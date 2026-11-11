import json
import time
import uuid
from datetime import datetime, timezone

import redis

# Connexion a Redis (la boite aux lettres)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def publier(evenement, service_emetteur, service_recepteur, agregat_modifie,
            id_agregat, operation, donnee_modifiee, nouvelle_valeur, contexte=None):
    """Depose un evenement dans la boite aux lettres du service recepteur."""
    message = {
        "evenement": evenement,
        "id_evenement": "EVT-" + uuid.uuid4().hex[:8].upper(),
        "date_emission": datetime.now(timezone.utc).isoformat(),
        "service_emetteur": service_emetteur,
        "service_recepteur": service_recepteur,
        "agregat_modifie": agregat_modifie,
        "id_agregat": id_agregat,
        "operation": operation,
        "donnee_modifiee": donnee_modifiee,
        "nouvelle_valeur": nouvelle_valeur,
    }
    if contexte is not None:
        message["contexte"] = contexte
    r.xadd("evenements:" + service_recepteur,
           {"data": json.dumps(message, ensure_ascii=False)})
    return message


def ecouter(service_recepteur, traiter):
    """Lit en boucle la boite aux lettres d'un service et traite chaque evenement."""
    flux = "evenements:" + service_recepteur
    # Cle-valeur dans Redis : le dernier message deja lu par ce service
    cle_position = "position:" + service_recepteur
    dernier_id = r.get(cle_position) or "0"

    while True:
        try:
            reponse = r.xread({flux: dernier_id}, block=5000)
        except redis.exceptions.ConnectionError:
            print("Redis injoignable, nouvel essai dans 2 secondes...")
            time.sleep(2)
            continue

        for _nom_flux, messages in reponse:
            for id_message, champs in messages:
                try:
                    traiter(json.loads(champs["data"]))
                except Exception as erreur:
                    print("Erreur pendant le traitement de", id_message, ":", erreur)
                dernier_id = id_message
                r.set(cle_position, dernier_id)