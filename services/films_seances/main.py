from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

from services.commun.evenements import publier

# Le guichet du service
app = FastAPI(title="Service FilmsEtSeances")

# Le classeur MongoDB de CE service, avec 3 tiroirs (collections)
client = MongoClient("mongodb://localhost:27017")
db = client["films_db"]
films = db["films"]
salles = db["salles"]
seances = db["seances"]

NOM_SERVICE = "FilmsEtSeances"


# =====================================================================
# FILMS
# =====================================================================

# Commande AjouterFilm (ici, commande et agregat ont presque les memes champs)
class Film(BaseModel):
    id_film: str
    titre: str
    description: str
    realisateur: str
    pays: list[str]
    annee_sortie: int
    genres: list[str]
    duree_minutes: int
    langue_originale: str
    versions_disponibles: list[str]
    acteurs: list[str]
    age_minimum: int
    affiche_url: str
    statut: str = "a_l_affiche"


# Commande ModifierFilm : on n'envoie QUE les champs a changer
class CommandeModifierFilm(BaseModel):
    titre: str | None = None
    description: str | None = None
    realisateur: str | None = None
    pays: list[str] | None = None
    annee_sortie: int | None = None
    genres: list[str] | None = None
    duree_minutes: int | None = None
    langue_originale: str | None = None
    versions_disponibles: list[str] | None = None
    acteurs: list[str] | None = None
    age_minimum: int | None = None
    affiche_url: str | None = None


def trouver_film(id_film):
    film = films.find_one({"id_film": id_film}, {"_id": 0})
    if film is None:
        raise HTTPException(status_code=404, detail="Film introuvable")
    return film


# Commande AjouterFilm
@app.post("/films")
def ajouter_film(film: Film):
    if films.find_one({"id_film": film.id_film}):
        raise HTTPException(status_code=400, detail="Ce film existe deja")

    # 1. On range la fiche dans NOTRE MongoDB
    films.insert_one(film.model_dump())

    # 2. On previent AvisEtFidelite : creation du replica FilmAvisable
    publier(
        evenement="FilmPublie",
        service_emetteur=NOM_SERVICE,
        service_recepteur="AvisEtFidelite",
        agregat_modifie="FilmAvisable",
        id_agregat=film.id_film,
        operation="creation",
        donnee_modifiee="FilmAvisable",
        nouvelle_valeur={
            "id_film": film.id_film,
            "titre": film.titre,
            "statut": film.statut,
        },
    )
    return film


# Commande ModifierFilm
@app.post("/films/{id_film}/modifier")
def modifier_film(id_film: str, commande: CommandeModifierFilm):
    ancien_film = trouver_film(id_film)

    # On garde seulement les champs envoyes
    modifications = commande.model_dump(exclude_none=True)
    if not modifications:
        raise HTTPException(status_code=400, detail="Aucune modification envoyee")

    # 1. On modifie NOTRE agregat Film
    films.update_one({"id_film": id_film}, {"$set": modifications})

    # 2. Si le TITRE a change, les replicas doivent etre mis a jour
    nouveau_titre = modifications.get("titre")
    if nouveau_titre and nouveau_titre != ancien_film["titre"]:
        # Le titre est copie dans 2 services : on previent les deux
        publier(
            evenement="FilmRenomme",
            service_emetteur=NOM_SERVICE,
            service_recepteur="AvisEtFidelite",
            agregat_modifie="FilmAvisable",
            id_agregat=id_film,
            operation="mise_a_jour",
            donnee_modifiee="titre",
            nouvelle_valeur=nouveau_titre,
        )
        publier(
            evenement="FilmRenomme",
            service_emetteur=NOM_SERVICE,
            service_recepteur="ClientsEtReservations",
            agregat_modifie="SeanceReservable",
            id_agregat=id_film,
            operation="mise_a_jour",
            donnee_modifiee="film.titre",
            nouvelle_valeur=nouveau_titre,
        )

    return trouver_film(id_film)


# Commande RetirerFilm
@app.post("/films/{id_film}/retirer")
def retirer_film(id_film: str):
    film = trouver_film(id_film)
    if film["statut"] == "retire":
        raise HTTPException(status_code=400, detail="Ce film est deja retire")

    # 1. On modifie NOTRE agregat : seul le statut change
    films.update_one({"id_film": id_film}, {"$set": {"statut": "retire"}})

    # 2. On previent AvisEtFidelite : mise a jour du replica FilmAvisable
    publier(
        evenement="FilmRetire",
        service_emetteur=NOM_SERVICE,
        service_recepteur="AvisEtFidelite",
        agregat_modifie="FilmAvisable",
        id_agregat=id_film,
        operation="mise_a_jour",
        donnee_modifiee="statut",
        nouvelle_valeur="retire",
    )
    return {"id_film": id_film, "statut": "retire"}


# Requete ConsulterFilms
@app.get("/films")
def consulter_films(statut: str = "a_l_affiche"):
    return list(films.find({"statut": statut}, {"_id": 0}))


# Requete ConsulterDetailsFilm
@app.get("/films/{id_film}")
def consulter_details_film(id_film: str):
    return trouver_film(id_film)


# =====================================================================
# SALLES
# =====================================================================

# Commande CreerSalle (ici, commande et agregat ont les memes champs)
class Salle(BaseModel):
    id_salle: str
    nom: str
    nombre_rangees: int
    places_par_rangee: int
    nombre_places: int
    equipements: list[str]


@app.post("/salles")
def creer_salle(salle: Salle):
    if salles.find_one({"id_salle": salle.id_salle}):
        raise HTTPException(status_code=400, detail="Cette salle existe deja")
    if salle.nombre_places != salle.nombre_rangees * salle.places_par_rangee:
        raise HTTPException(status_code=400,
                            detail="nombre_places doit valoir nombre_rangees x places_par_rangee")
    salles.insert_one(salle.model_dump())
    return salle


@app.get("/salles")
def consulter_salles():
    return list(salles.find({}, {"_id": 0}))


# =====================================================================
# SEANCES
# =====================================================================

# La COMMANDE CreerSeance : ce que l'utilisateur envoie (pas de statut)
class CommandeCreerSeance(BaseModel):
    id_seance: str
    id_film: str
    id_salle: str
    date: str
    heure_debut: str
    version: str
    format: str


# La COMMANDE ModifierSeance : on n'envoie QUE ce qui change
class CommandeModifierSeance(BaseModel):
    date: str | None = None
    heure_debut: str | None = None


# La COMMANDE AnnulerSeance : juste un motif
class CommandeAnnulerSeance(BaseModel):
    motif: str


def trouver_seance(id_seance):
    seance = seances.find_one({"id_seance": id_seance}, {"_id": 0})
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance introuvable")
    return seance


@app.post("/seances")
def creer_seance(commande: CommandeCreerSeance):
    # 1. Verifications : la seance n'existe pas, le film et la salle existent
    if seances.find_one({"id_seance": commande.id_seance}):
        raise HTTPException(status_code=400, detail="Cette seance existe deja")
    film = trouver_film(commande.id_film)
    if film["statut"] == "retire":
        raise HTTPException(status_code=400, detail="Ce film est retire")
    if commande.version not in film["versions_disponibles"]:
        raise HTTPException(status_code=400, detail="Version non disponible pour ce film")
    salle = salles.find_one({"id_salle": commande.id_salle})
    if salle is None:
        raise HTTPException(status_code=404, detail="Salle introuvable")

    # 2. On fabrique l'AGREGAT Seance : la commande + le statut ajoute par le service
    seance = commande.model_dump()
    seance["statut"] = "programmee"
    seances.insert_one(seance)
    seance.pop("_id")

    # 3. On previent ClientsEtReservations : creation du replica SeanceReservable
    publier(
        evenement="SeancePubliee",
        service_emetteur=NOM_SERVICE,
        service_recepteur="ClientsEtReservations",
        agregat_modifie="SeanceReservable",
        id_agregat=commande.id_seance,
        operation="creation",
        donnee_modifiee="SeanceReservable",
        nouvelle_valeur={
            "id_seance": commande.id_seance,
            "film": {"id_film": film["id_film"], "titre": film["titre"]},
            "salle": {
                "id_salle": salle["id_salle"],
                "nom": salle["nom"],
                "nombre_places": salle["nombre_places"],
            },
            "date": commande.date,
            "heure_debut": commande.heure_debut,
            "version": commande.version,
            "format": commande.format,
            "statut": "programmee",
        },
    )
    return seance


# Commande ModifierSeance
@app.post("/seances/{id_seance}/modifier")
def modifier_seance(id_seance: str, commande: CommandeModifierSeance):
    seance = trouver_seance(id_seance)
    if seance["statut"] == "annulee":
        raise HTTPException(status_code=400, detail="Une seance annulee ne peut pas etre modifiee")

    modifications = commande.model_dump(exclude_none=True)
    if not modifications:
        raise HTTPException(status_code=400, detail="Aucune modification envoyee")

    # 1. On modifie NOTRE agregat Seance
    seances.update_one({"id_seance": id_seance}, {"$set": modifications})

    # 2. Un evenement SeanceModifiee par donnee modifiee
    for champ, valeur in modifications.items():
        publier(
            evenement="SeanceModifiee",
            service_emetteur=NOM_SERVICE,
            service_recepteur="ClientsEtReservations",
            agregat_modifie="SeanceReservable",
            id_agregat=id_seance,
            operation="mise_a_jour",
            donnee_modifiee=champ,
            nouvelle_valeur=valeur,
        )
    return trouver_seance(id_seance)


# Commande AnnulerSeance
@app.post("/seances/{id_seance}/annuler")
def annuler_seance(id_seance: str, commande: CommandeAnnulerSeance):
    seance = trouver_seance(id_seance)
    if seance["statut"] == "annulee":
        raise HTTPException(status_code=400, detail="Cette seance est deja annulee")

    # 1. On modifie NOTRE agregat : seul le statut change
    seances.update_one({"id_seance": id_seance}, {"$set": {"statut": "annulee"}})

    # 2. On previent ClientsEtReservations : mise a jour du replica
    publier(
        evenement="SeanceAnnulee",
        service_emetteur=NOM_SERVICE,
        service_recepteur="ClientsEtReservations",
        agregat_modifie="SeanceReservable",
        id_agregat=id_seance,
        operation="mise_a_jour",
        donnee_modifiee="statut",
        nouvelle_valeur="annulee",
        contexte={"motif": commande.motif},
    )
    return {"id_seance": id_seance, "statut": "annulee", "motif": commande.motif}


# Requete ConsulterSeances (filtres facultatifs)
@app.get("/seances")
def consulter_seances(id_film: str | None = None, date: str | None = None,
                      version: str | None = None):
    filtre = {}
    if id_film:
        filtre["id_film"] = id_film
    if date:
        filtre["date"] = date
    if version:
        filtre["version"] = version
    return list(seances.find(filtre, {"_id": 0}))