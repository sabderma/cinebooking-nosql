import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pymongo import MongoClient

from services.commun.evenements import ecouter

# Le classeur MongoDB de CE service uniquement
db = MongoClient("mongodb://localhost:27017")["avis_db"]
films_avisables = db["films_avisables"]
comptes_fidelite = db["comptes_fidelite"]

# Les regles de fidelite (les memes que dans commandes/service_avis_fidelite.json)
POINTS_FILM_VISIONNE = 20
BONUS_TOUS_LES_N_FILMS = 5
BONUS_POINTS = 30


# =====================================================================
# EVENEMENTS RECUS
# =====================================================================

def traiter_evenement(evenement):
    """Ce que fait le service quand il recoit un message."""
    print("Evenement recu :", evenement["evenement"], evenement["id_agregat"])

    if evenement["evenement"] == "FilmPublie":
        replica = evenement["nouvelle_valeur"]
        replica["type_donnee"] = "replica"
        replica["service_source"] = evenement["service_emetteur"]
        films_avisables.replace_one({"id_film": replica["id_film"]}, replica, upsert=True)

    elif evenement["evenement"] == "FilmRenomme":
        films_avisables.update_one({"id_film": evenement["id_agregat"]},
                                   {"$set": {"titre": evenement["nouvelle_valeur"]}})

    elif evenement["evenement"] == "FilmRetire":
        films_avisables.update_one({"id_film": evenement["id_agregat"]},
                                   {"$set": {"statut": evenement["nouvelle_valeur"]}})

    elif evenement["evenement"] == "PresenceValidee":
        ajouter_points_film(evenement)


def ajouter_points_film(evenement):
    id_client = evenement["contexte"]["id_client"]
    id_reservation = evenement["id_agregat"]

    # 1. On lit le compte du client (ou on en cree un vide)
    compte = comptes_fidelite.find_one({"id_client": id_client}, {"_id": 0})
    if compte is None:
        compte = {
            "id_client": id_client,
            "solde_points": 0,
            "nombre_films_visionnes": 0,
            "nombre_avis_publies": 0,
            "historique_points": [],
        }

    # 2. Securite : si cette reservation a deja rapporte des points, on ne fait rien
    for ligne in compte["historique_points"]:
        if ligne.get("id_reservation") == id_reservation:
            return

    # 3. On applique NOS regles de fidelite
    compte["solde_points"] += POINTS_FILM_VISIONNE
    compte["nombre_films_visionnes"] += 1
    compte["historique_points"].append({
        "type": "film_visionne",
        "points": POINTS_FILM_VISIONNE,
        "id_reservation": id_reservation,
    })
    if compte["nombre_films_visionnes"] % BONUS_TOUS_LES_N_FILMS == 0:
        compte["solde_points"] += BONUS_POINTS
        compte["historique_points"].append({
            "type": "bonus_5_films",
            "points": BONUS_POINTS,
        })

    # 4. On range l'agregat CompteFidelite dans NOTRE MongoDB
    comptes_fidelite.replace_one({"id_client": id_client}, compte, upsert=True)


@asynccontextmanager
async def lifespan(app):
    # Au demarrage : on lance l'ecoute de la boite aux lettres en arriere-plan
    threading.Thread(target=ecouter, args=("AvisEtFidelite", traiter_evenement),
                     daemon=True).start()
    yield


app = FastAPI(title="Service AvisEtFidelite", lifespan=lifespan)


# =====================================================================
# REQUETES
# =====================================================================

@app.get("/films-avisables")
def consulter_films_avisables():
    return list(films_avisables.find({}, {"_id": 0}))


# Requete ConsulterMesPoints
@app.get("/fidelite/{id_client}")
def consulter_mes_points(id_client: str):
    compte = comptes_fidelite.find_one({"id_client": id_client}, {"_id": 0})
    if compte is None:
        raise HTTPException(status_code=404, detail="Aucun compte fidelite pour ce client")
    return compte