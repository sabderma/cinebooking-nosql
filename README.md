# CinéBooking — Projet NoSQL

## 1. Présentation du projet

CinéBooking est une application de cinéma qui permet aux utilisateurs de consulter les films disponibles, de réserver des places et de donner leur avis sur les films.

L'application propose également des promotions pour bénéficier de réductions sur les réservations.

Le projet est composé de trois services indépendants, chacun ayant ses propres fonctionnalités et ses propres données.

## 2. Objectifs du projet

- Consulter les films et les horaires des séances.
- Réserver et annuler des places de cinéma.
- Donner une note et un commentaire sur un film.
- Consulter les avis des spectateurs.
- Créer et utiliser des codes promotionnels.
- Faire communiquer les services grâce à des événements.
- Utiliser des données au format JSON.

## 3. Les trois services hh

### Service 1 — Films et séances

Ce service est responsable de la gestion du catalogue des films et de la programmation du cinéma.

**Fonctionnalités :**
- Ajouter, modifier ou supprimer un film.
- Consulter les films disponibles.
- Créer et modifier les séances.
- Gérer les salles et les horaires.

**Exemple :**

Le film Avatar est programmé dans la salle 2 à 20h.

### Service 2 — Réservations

Ce service est responsable de la gestion des places et des réservations des clients.

**Fonctionnalités :**
- Consulter les places disponibles.
- Réserver une ou plusieurs places.
- Annuler une réservation.
- Consulter les réservations effectuées.
- Gérer les places occupées et disponibles.

**Exemple :**

Un client réserve la place B5 pour une séance du film Avatar.

### Service 3 — Avis, évaluations et promotions

Ce service est responsable de la gestion des avis des spectateurs et des offres promotionnelles.

**Fonctionnalités :**
- Donner une note à un film.
- Ajouter un commentaire sur un film.
- Consulter les avis des spectateurs.
- Calculer la note moyenne d'un film.
- Créer des codes promotionnels.
- Définir le pourcentage de réduction.
- Activer ou désactiver une promotion.

**Exemple :**

Un spectateur donne une note de 4/5 au film Avatar et ajoute un commentaire.

Le cinéma propose également un code promotionnel CINEMA10 donnant une réduction de 10 %.

## 4. Architecture du projet

L'application est composée de trois services indépendants.

Chaque service possède ses propres données et gère ses propres fonctionnalités.

Les services peuvent communiquer grâce à des événements JSON pour transmettre les informations nécessaires.

Cette organisation permet de limiter les dépendances entre les services et de faciliter leur évolution.

## 5. Technologies envisagées

- JSON : représentation des données.
- NoSQL : stockage des données.
- GitHub : gestion et partage du projet.
- Architecture événementielle : communication entre les services.
