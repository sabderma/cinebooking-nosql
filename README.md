# CinéBooking — Projet NoSQL

## 1. Présentation

CinéBooking est une application de cinéma qui permet de consulter les films et les séances, de réserver des places, de publier des avis et de profiter d'un programme de fidélité.

L'architecture repose sur trois services métier principaux. Chaque service possède ses propres agrégats et communique avec les autres au moyen d'événements JSON, afin de limiter les dépendances directes. À l'étape 6, un service spécialisé de lecture, `StatistiquesFilms`, est ajouté pour construire une projection destinée au classement des films.

## 2. Services métier principaux

### `FilmsEtSeances`

Ce service est propriétaire du catalogue et de la programmation.

Agrégats :

- `Film` : description, réalisation, genres, durée, versions et statut du film ;
- `Salle` : capacité et équipements d'une salle ;
- `Seance` : film, salle, date, heure, version, format et statut d'une séance.

Principales commandes : ajouter, modifier ou retirer un film ; créer une salle ; créer, modifier ou annuler une séance.

### `ClientsEtReservations`

Ce service est propriétaire des comptes clients, des tarifs et des réservations.

Agrégats :

- `Client` : profil du client ;
- `Tarification` : tarifs applicables à une séance ;
- `Reservation` : places réservées, prix appliqués et statut de la réservation ;
- `SeanceReservable` : réplica des informations de séance nécessaires à une réservation ;
- `RecompenseUtilisable` : réplica des récompenses qu'un client peut appliquer à une réservation.

Principales commandes : créer ou modifier un compte, définir les tarifs, créer ou annuler une réservation, valider une présence et appliquer une récompense.

### `AvisEtFidelite`

Ce service est propriétaire des avis, des comptes de fidélité et des récompenses.

Agrégats :

- `Avis` : note et commentaire publiés par un client ;
- `CompteFidelite` : solde, compteurs et historique des points ;
- `Recompense` : réduction obtenue en échange de points ;
- `FilmAvisable` : réplica minimal d'un film pouvant recevoir des avis.

Principales commandes : ajouter, modifier ou supprimer un avis, échanger des points et désactiver une récompense.

## 3. Données répliquées

Trois réplicas permettent aux services consommateurs de travailler sans interroger directement le service propriétaire de la donnée :

- `SeanceReservable`, stocké dans `ClientsEtReservations` et issu de `FilmsEtSeances`, reprend l'identifiant de la séance, le film, la salle, la capacité, la date, l'heure, la version, le format et le statut ;
- `FilmAvisable`, stocké dans `AvisEtFidelite` et issu de `FilmsEtSeances`, reprend l'identifiant, le titre et le statut du film ;
- `RecompenseUtilisable`, stocké dans `ClientsEtReservations` et issu de `AvisEtFidelite`, reprend l'identifiant, le client, le montant, la date d'expiration et le statut de la récompense.

Chaque réplica indique explicitement `type_donnee: "replica"` et son `service_source`.

Données répliquées repérées : `id_film` et `titre` (dans `SeanceReservable` et `FilmAvisable`), les informations de séance et de salle (dans `SeanceReservable`), et les informations de récompense (dans `RecompenseUtilisable`).

## 4. Communication par événements

Les services sont découplés grâce aux événements JSON suivants :

| Événement | Émetteur | Récepteur | Rôle |
|---|---|---|---|
| `SeancePubliee` | `FilmsEtSeances` | `ClientsEtReservations` | Crée le réplica `SeanceReservable`. |
| `SeanceModifiee` | `FilmsEtSeances` | `ClientsEtReservations` | Met à jour l'heure du réplica. |
| `SeanceAnnulee` | `FilmsEtSeances` | `ClientsEtReservations` | Passe le statut du réplica à `annulee`. |
| `FilmPublie` | `FilmsEtSeances` | `AvisEtFidelite` | Crée le réplica `FilmAvisable`. |
| `FilmRenomme` | `FilmsEtSeances` | `ClientsEtReservations` et `AvisEtFidelite` | Met à jour le titre copié dans `SeanceReservable` et `FilmAvisable`. |
| `FilmRetire` | `FilmsEtSeances` | `AvisEtFidelite` | Passe le statut du réplica à `retire`. |
| `PresenceValidee` | `ClientsEtReservations` | `AvisEtFidelite` | Annonce qu'un client a vu un film ; `AvisEtFidelite` calcule lui-même les points. |
| `RecompenseCreee` | `AvisEtFidelite` | `ClientsEtReservations` | Crée le réplica `RecompenseUtilisable`. |
| `RecompenseDesactivee` | `AvisEtFidelite` | `ClientsEtReservations` | Passe le statut du réplica à `desactivee`. |
| `RecompenseUtilisee` | `ClientsEtReservations` | `AvisEtFidelite` | Marque la récompense comme utilisée. |
| `AvisPublie` / `AvisModifie` / `AvisSupprime` | `AvisEtFidelite` | `StatistiquesFilms` | Mettent à jour la projection `EvaluationFilm`. |

Chaque événement précise :

- un identifiant unique (`id_evenement`) et une date d'émission (`date_emission`) ;
- le service émetteur et le service récepteur ;
- l'agrégat et la donnée modifiés ;
- la nouvelle valeur (et l'ancienne valeur lorsqu'elle est nécessaire au calcul).

Les couples `SeancePubliee` / `SeanceModifiee`, `FilmPublie` / `FilmRenomme` et `RecompenseCreee` / `RecompenseDesactivee` montrent chacun la création puis la mise à jour d'un réplica.

L'événement `PresenceValidee` ne transporte que le fait métier (le client a vu le film). Le service émetteur ne connaît pas le solde de points : c'est `AvisEtFidelite` qui applique ses propres règles de fidélité.

## 5. Projection `StatistiquesFilms`

Le service spécialisé `StatistiquesFilms` construit l'agrégat de lecture `EvaluationFilm` à partir des événements `AvisPublie`, `AvisModifie` et `AvisSupprime` émis par `AvisEtFidelite`.

Pour chaque film, la projection conserve :

- la somme des notes (`somme_notes`) ;
- le nombre total d'avis publiés (`nombre_avis`) ;
- la note moyenne, selon la formule `somme_notes / nombre_avis`.

Conserver la somme permet de recalculer la moyenne à chaque événement sans relire tous les avis :

- `AvisPublie` : `somme_notes += note` et `nombre_avis += 1` ;
- `AvisModifie` : `somme_notes += nouvelle note - ancienne note` ;
- `AvisSupprime` : `somme_notes -= note` et `nombre_avis -= 1`.

L'exemple fourni contient un avis noté 5 : la projection possède donc `somme_notes: 5`, `nombre_avis: 1` et `note_moyenne: 5.0`.

La requête `ConsulterFilmsLesMieuxNotes` sélectionne les films dont la note moyenne est au moins égale à 4, les trie par note décroissante et limite le résultat aux dix premiers.

## 6. Stockage NoSQL

Le projet utilise deux bases NoSQL complémentaires :

- **Redis** (étape 7) : stockage des agrégats de chaque service sous forme de clés préfixées par le nom du service, et transport des événements entre services avec Redis Streams. La projection `EvaluationFilm` utilise un ensemble trié (sorted set) pour obtenir directement le classement des films.
- **MongoDB** : stockage durable des agrégats sous forme de documents JSON, avec une base par service, ce qui permet de faire des requêtes riches (par exemple filtrer les séances par film, date et version).

## 7. Structure du dépôt

```text
.
├── README.md
├── commandes/
│   ├── service_films_seances.json
│   ├── service_clients_reservations.json
│   └── service_avis_fidelite.json
├── agregats/
│   ├── service_films_seances.json
│   ├── service_clients_reservations.json
│   └── service_avis_fidelite.json
├── evenements/
│   ├── seance_reservable.json
│   ├── film_avisable.json
│   ├── fidelite.json
│   ├── recompense.json
│   └── statistiques_films.json
└── projections/
    └── service_statistiques_films.json
```

## 8. Technologies et principes

- JSON pour représenter les commandes, agrégats, réplicas, événements et projections ;
- Python et FastAPI pour implémenter chaque service ;
- Redis pour les agrégats, les événements (Redis Streams) et le classement des films ;
- MongoDB pour le stockage documentaire durable des agrégats ;
- architecture événementielle pour la communication asynchrone entre services ;
- réplication contrôlée des seules données nécessaires à chaque service ;
- projection en modèle de lecture pour répondre efficacement à une requête spécialisée ;
- Git et GitHub pour le travail collaboratif et le suivi des versions.
