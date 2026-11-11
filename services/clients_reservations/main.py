import threading
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient

from services.commun.evenements import ecouter, publier

# Le classeur MongoDB de CE service, avec 4 tiroirs
db = MongoClient("mongodb://localhost:27017")["reservations_db"]
clients = db["clients"]
tarifs = db["tarifs"]
reservations = db["reservations"]
seances_reservables = db["seances_reservables"]   # le replica

NOM_SERVICE = "ClientsEtReservations"


# =====================================================================
# EVENEMENTS RECUS (depuis FilmsEtSeances, via Redis)
# =====================================================================

def traiter_evenement(evenement):
    print("Evenement recu :", evenement["evenement"], evenement["id_agregat"])
    nom = evenement["evenement"]

    if nom == "SeancePubliee":
        # Creation du replica SeanceReservable
        replica = evenement["nouvelle_valeur"]
        replica["type_donnee"] = "replica"
        replica["service_source"] = evenement["service_emetteur"]
        seances_reservables.replace_one({"id_seance": replica["id_seance"]},
                                        replica, upsert=True)

    elif nom == "SeanceModifiee":
        # Mise a jour du replica : la donnee modifiee (date ou heure_debut)
        seances_reservables.update_one(
            {"id_seance": evenement["id_agregat"]},
            {"$set": {evenement["donnee_modifiee"]: evenement["nouvelle_valeur"]}})

    elif nom == "SeanceAnnulee":
        # Mise a jour du replica + annulation des reservations de cette seance
        seances_reservables.update_one({"id_seance": evenement["id_agregat"]},
                                       {"$set": {"statut": "annulee"}})
        reservations.update_many(
            {"id_seance": evenement["id_agregat"], "statut": "confirmee",
             "presence_validee": False},
            {"$set": {"statut": "annulee", "motif_annulation": "Seance annulee par le cinema"}})

    elif nom == "FilmRenomme":
        # Le titre est copie dans toutes les seances de ce film
        seances_reservables.update_many(
            {"film.id_film": evenement["id_agregat"]},
            {"$set": {"film.titre": evenement["nouvelle_valeur"]}})


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=ecouter, args=(NOM_SERVICE, traiter_evenement),
                     daemon=True).start()
    yield


app = FastAPI(title="Service ClientsEtReservations", lifespan=lifespan)


# =====================================================================
# CLIENTS
# =====================================================================

# Commande CreerCompteClient
class CommandeCreerCompteClient(BaseModel):
    id_client: str
    prenom: str
    nom: str
    email: str
    date_naissance: str
    statut_etudiant: bool


# Commande ModifierProfilClient : on n'envoie QUE ce qui change
class CommandeModifierProfilClient(BaseModel):
    prenom: str | None = None
    nom: str | None = None
    email: str | None = None
    statut_etudiant: bool | None = None


def trouver_client(id_client):
    client = clients.find_one({"id_client": id_client}, {"_id": 0})
    if client is None:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return client


@app.post("/clients")
def creer_compte_client(commande: CommandeCreerCompteClient):
    if clients.find_one({"id_client": commande.id_client}):
        raise HTTPException(status_code=400, detail="Ce client existe deja")
    # Agregat Client = la commande + la date de creation ajoutee par le service
    client = commande.model_dump()
    client["date_creation"] = date.today().isoformat()
    clients.insert_one(client)
    client.pop("_id")
    return client


@app.post("/clients/{id_client}/modifier")
def modifier_profil_client(id_client: str, commande: CommandeModifierProfilClient):
    trouver_client(id_client)
    modifications = commande.model_dump(exclude_none=True)
    if not modifications:
        raise HTTPException(status_code=400, detail="Aucune modification envoyee")
    clients.update_one({"id_client": id_client}, {"$set": modifications})
    return trouver_client(id_client)


# Requete ConsulterMonProfil
@app.get("/clients/{id_client}")
def consulter_mon_profil(id_client: str):
    return trouver_client(id_client)


# =====================================================================
# TARIFS
# =====================================================================

# Commande DefinirTarifs
class CommandeDefinirTarifs(BaseModel):
    id_seance: str
    tarifs: dict[str, float]


@app.post("/tarifs")
def definir_tarifs(commande: CommandeDefinirTarifs):
    if seances_reservables.find_one({"id_seance": commande.id_seance}) is None:
        raise HTTPException(status_code=404, detail="Seance introuvable")
    # Agregat Tarification = la commande + la devise
    tarification = commande.model_dump()
    tarification["devise"] = "EUR"
    tarifs.replace_one({"id_seance": commande.id_seance}, tarification, upsert=True)
    return tarification


# =====================================================================
# SEANCES RESERVABLES (lecture du replica)
# =====================================================================

@app.get("/seances-reservables")
def consulter_seances_reservables():
    return list(seances_reservables.find({}, {"_id": 0}))


def places_deja_reservees(id_seance):
    prises = []
    for r in reservations.find({"id_seance": id_seance, "statut": "confirmee"}):
        prises.extend(r["places"])
    return prises


# Requete ConsulterPlacesDisponibles
@app.get("/seances/{id_seance}/places-disponibles")
def consulter_places_disponibles(id_seance: str):
    seance = seances_reservables.find_one({"id_seance": id_seance})
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance introuvable")
    places_prises = places_deja_reservees(id_seance)
    return {
        "id_seance": id_seance,
        "nombre_places": seance["salle"]["nombre_places"],
        "places_prises": places_prises,
        "places_disponibles": seance["salle"]["nombre_places"] - len(places_prises),
    }


# =====================================================================
# CALCUL DU PRIX (regles metier de CE service)
# =====================================================================

def age_du_client(client):
    naissance = date.fromisoformat(client["date_naissance"])
    aujourd_hui = date.today()
    age = aujourd_hui.year - naissance.year
    if (aujourd_hui.month, aujourd_hui.day) < (naissance.month, naissance.day):
        age -= 1
    return age


def categories_autorisees(client):
    """Les tarifs auxquels ce client a droit."""
    autorisees = ["normal"]
    age = age_du_client(client)
    if age < 26:
        autorisees.append("moins_26_ans")
    if age < 14:
        autorisees.append("moins_14_ans")
    if client["statut_etudiant"]:
        autorisees.append("etudiant")
    return autorisees


def calculer_prix(id_client, id_seance, places, categorie_tarif=None):
    """Verifie la demande et calcule le prix. Utilise par 2 routes."""
    client = trouver_client(id_client)

    # On lit NOTRE replica : pas besoin d'appeler le service FilmsEtSeances
    seance = seances_reservables.find_one({"id_seance": id_seance})
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance introuvable")
    if seance["statut"] != "programmee":
        raise HTTPException(status_code=400, detail="Cette seance n'est pas reservable")

    if not places:
        raise HTTPException(status_code=400, detail="Aucune place demandee")
    if len(set(places)) != len(places):
        raise HTTPException(status_code=400, detail="Une place est demandee deux fois")

    prises = places_deja_reservees(id_seance)
    deja_prises = set(prises) & set(places)
    if deja_prises:
        raise HTTPException(status_code=400,
                            detail=f"Places deja reservees : {sorted(deja_prises)}")
    if len(prises) + len(places) > seance["salle"]["nombre_places"]:
        raise HTTPException(status_code=400, detail="Pas assez de places disponibles")

    tarification = tarifs.find_one({"id_seance": id_seance})
    if tarification is None:
        raise HTTPException(status_code=400, detail="Aucun tarif pour cette seance")

    autorisees = [c for c in categories_autorisees(client) if c in tarification["tarifs"]]
    if categorie_tarif is None:
        # Pas de categorie demandee : on choisit la moins chere a laquelle il a droit
        if not autorisees:
            raise HTTPException(status_code=400, detail="Aucun tarif applicable")
        categorie_tarif = min(autorisees, key=lambda c: tarification["tarifs"][c])
    elif categorie_tarif not in tarification["tarifs"]:
        raise HTTPException(status_code=400, detail="Categorie de tarif inconnue")
    elif categorie_tarif not in autorisees:
        raise HTTPException(status_code=400,
                            detail=f"Ce client n'a pas droit au tarif {categorie_tarif}")

    prix_unitaire = tarification["tarifs"][categorie_tarif]
    return {
        "categorie_tarif": categorie_tarif,
        "prix_unitaire": prix_unitaire,
        "nombre_places": len(places),
        "prix_total": round(prix_unitaire * len(places), 2),
    }


# =====================================================================
# RESERVATIONS
# =====================================================================

# La COMMANDE CreerReservation : ce que le client envoie (pas de prix !)
class CommandeCreerReservation(BaseModel):
    id_reservation: str
    id_client: str
    id_seance: str
    places: list[str]
    categorie_tarif: str



# La COMMANDE AnnulerReservation
class CommandeAnnulerReservation(BaseModel):
    id_client: str
    motif: str


# Requete CalculerPrixReservation : GET, car on lit sans rien changer
@app.get("/reservations/calculer-prix")
def calculer_prix_reservation(id_client: str, id_seance: str,
                              places: list[str] = Query(...),
                              categorie_tarif: str | None = None):
    return calculer_prix(id_client, id_seance, places, categorie_tarif)


@app.post("/reservations")
def creer_reservation(commande: CommandeCreerReservation):
    if reservations.find_one({"id_reservation": commande.id_reservation}):
        raise HTTPException(status_code=400, detail="Cette reservation existe deja")

    # 1. Le service VERIFIE et CALCULE ce que le client n'a pas donne
    prix = calculer_prix(commande.id_client, commande.id_seance,
                         commande.places, commande.categorie_tarif)

    # 2. On fabrique l'AGREGAT Reservation : commande + champs calcules
    reservation = commande.model_dump()
    reservation["date_reservation"] = date.today().isoformat()
    reservation["prix_unitaire"] = prix["prix_unitaire"]
    reservation["nombre_places"] = prix["nombre_places"]
    reservation["prix_total"] = prix["prix_total"]
    reservation["recompense_utilisee"] = None
    reservation["statut"] = "confirmee"
    reservation["presence_validee"] = False

    reservations.insert_one(reservation)
    reservation.pop("_id")
    return reservation


def trouver_reservation(id_reservation):
    reservation = reservations.find_one({"id_reservation": id_reservation}, {"_id": 0})
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation introuvable")
    return reservation


# Commande AnnulerReservation
@app.post("/reservations/{id_reservation}/annuler")
def annuler_reservation(id_reservation: str, commande: CommandeAnnulerReservation):
    reservation = trouver_reservation(id_reservation)
    if reservation["id_client"] != commande.id_client:
        raise HTTPException(status_code=403, detail="Cette reservation n'est pas a vous")
    if reservation["statut"] != "confirmee":
        raise HTTPException(status_code=400, detail="Reservation deja annulee")
    if reservation["presence_validee"]:
        raise HTTPException(status_code=400, detail="Le film a deja ete vu")

    # Seul le statut change : les places redeviennent libres
    reservations.update_one({"id_reservation": id_reservation},
                            {"$set": {"statut": "annulee",
                                      "motif_annulation": commande.motif}})
    return trouver_reservation(id_reservation)


# Commande ValiderPresence
@app.post("/reservations/{id_reservation}/valider-presence")
def valider_presence(id_reservation: str):
    reservation = trouver_reservation(id_reservation)
    if reservation["statut"] != "confirmee":
        raise HTTPException(status_code=400, detail="Reservation non confirmee")
    if reservation["presence_validee"]:
        raise HTTPException(status_code=400, detail="Presence deja validee")

    # On cherche le film dans NOTRE replica de la seance
    seance = seances_reservables.find_one({"id_seance": reservation["id_seance"]})

    # 1. On modifie NOTRE agregat Reservation
    reservations.update_one({"id_reservation": id_reservation},
                            {"$set": {"presence_validee": True}})

    # 2. On annonce le fait a AvisEtFidelite (sans parler de points !)
    publier(
        evenement="PresenceValidee",
        service_emetteur=NOM_SERVICE,
        service_recepteur="AvisEtFidelite",
        agregat_modifie="Reservation",
        id_agregat=id_reservation,
        operation="mise_a_jour",
        donnee_modifiee="presence_validee",
        nouvelle_valeur=True,
        contexte={
            "id_client": reservation["id_client"],
            "id_film": seance["film"]["id_film"],
        },
    )
    return {"id_reservation": id_reservation, "presence_validee": True}


# Requete ConsulterMesReservations
@app.get("/reservations")
def consulter_mes_reservations(id_client: str):
    return list(reservations.find({"id_client": id_client}, {"_id": 0}))