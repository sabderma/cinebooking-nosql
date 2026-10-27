# CinéBooking — Projet NoSQL

## 1. Présentation

CinéBooking est une application de cinéma permettant de consulter les films et les séances, de réserver des places, de publier des avis et de bénéficier d'un programme de fidélité.

L'architecture repose sur trois services métier principaux. Chaque service possède ses propres agrégats et communique avec les autres au moyen d'événements JSON afin de limiter les dépendances directes. À l'étape 6, un service spécialisé de lecture, `StatistiquesFilms`, est ajouté pour construire une projection destinée au classement des films.

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
- `SeanceReservable` : réplica des informations de séance nécessaires à une réservation.

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

Deux réplicas permettent aux services consommateurs de travailler sans interroger directement `FilmsEtSeances` :

- `SeanceReservable`, stocké dans `ClientsEtReservations`, reprend l'identifiant de la séance, le film, la salle, la capacité, la date, l'heure, la version, le format et le statut ;
- `FilmAvisable`, stocké dans `AvisEtFidelite`, reprend l'identifiant, le titre et le statut du film.

Chaque réplica indique explicitement `type_donnee: "replica"` et son `service_source`.

## 4. Communication par événements

Les services sont découplés grâce à six événements JSON :

| Événement | Émetteur | Récepteur | Rôle |
|---|---|---|---|
| `SeancePubliee` | `FilmsEtSeances` | `ClientsEtReservations` | Crée le réplica `SeanceReservable`. |
| `SeanceModifiee` | `FilmsEtSeances` | `ClientsEtReservations` | Met à jour l'heure du réplica. |
| `SeanceAnnulee` | `FilmsEtSeances` | `ClientsEtReservations` | Passe le statut du réplica à `annulee`. |
| `FilmPublie` | `FilmsEtSeances` | `AvisEtFidelite` | Crée le réplica `FilmAvisable`. |
| `FilmModifie` | `FilmsEtSeances` | `AvisEtFidelite` | Met à jour le statut du réplica. |
| `PresenceValidee` | `ClientsEtReservations` | `AvisEtFidelite` | Ajoute les points du film visionné au `CompteFidelite`, incrémente le compteur et complète l'historique. |

Chaque événement précise le service émetteur, le service récepteur, l'agrégat et la donnée modifiés ainsi que la nouvelle valeur. Les événements `SeancePubliee`/`SeanceModifiee` et `FilmPublie`/`FilmModifie` montrent respectivement la création puis la mise à jour d'un réplica.

## 5. Projection `StatistiquesFilms`

Le service spécialisé `StatistiquesFilms` construit l'agrégat de lecture `EvaluationFilm` à partir de `FilmAvisable` et des avis publiés par `AvisEtFidelite`.

Pour chaque film, la projection calcule :

- le nombre total d'avis publiés ;
- la note moyenne, selon la formule `somme des notes / nombre d'avis`.

L'exemple fourni contient un avis noté 5 : la projection reproductible possède donc `note_moyenne: 5.0` et `nombre_avis: 1`.

La requête `ConsulterFilmsLesMieuxNotes` sélectionne les films dont la note moyenne est au moins égale à 4, les trie par note décroissante et limite le résultat aux dix premiers.

## 6. Structure du dépôt

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
│   └── fidelite.json
└── projections/
    └── service_statistiques_films.json
```

## 7. Technologies et principes

- JSON pour représenter les commandes, agrégats, réplicas, événements et projections ;
- stockage NoSQL orienté agrégats ;
- architecture événementielle pour la communication asynchrone entre services ;
- réplication contrôlée des seules données nécessaires à chaque service ;
- projection en modèle de lecture pour répondre efficacement à une requête spécialisée ;
- Git et GitHub pour le travail collaboratif et le suivi des versions.
