# CinéBooking — Projet NoSQL

## 1. Présentation du projet

CinéBooking est une application de cinéma qui permet aux utilisateurs de consulter les films disponibles, de réserver des places et de donner leur avis sur les films.

L’application propose également un programme de fidélité permettant de gagner des points et de les échanger contre des récompenses utilisables lors des réservations.

Le projet est composé de trois services indépendants, chacun ayant ses propres fonctionnalités et ses propres données.

## 2. Objectifs du projet

- Consulter les films et les horaires des séances.
- Créer un compte client.
- Réserver et annuler des places de cinéma.
- Donner une note et un commentaire sur un film.
- Consulter les avis des spectateurs.
- Cumuler des points de fidélité.
- Échanger des points contre des récompenses.
- Faire communiquer les services grâce à des événements.
- Utiliser des données au format JSON.

## 3. Les trois services

### Service 1 — Films et séances

Ce service est responsable de la gestion du catalogue des films, des salles et de la programmation des séances.

**Fonctionnalités :**

- Ajouter, modifier ou retirer un film.
- Consulter les films disponibles.
- Créer et modifier les séances.
- Annuler une séance.
- Gérer les salles et les horaires.

**Exemple :**

Le film Avatar est programmé dans la salle 2 à 20 h.

### Service 2 — Clients et réservations

Ce service est responsable de la gestion des comptes clients, des tarifs, des places et des réservations.

**Fonctionnalités :**

- Créer et modifier un compte client.
- Définir les tarifs d’une séance.
- Consulter les places disponibles.
- Réserver une ou plusieurs places.
- Annuler une réservation.
- Consulter les réservations effectuées.
- Calculer le prix d’une réservation.
- Appliquer une récompense à une réservation.
- Valider la présence d’un client à une séance.

**Exemple :**

Un client réserve les places B5 et B6 pour une séance du film Avatar en utilisant le tarif étudiant.

### Service 3 — Avis et fidélité

Ce service est responsable de la gestion des avis des spectateurs, des points de fidélité et des récompenses.

**Fonctionnalités :**

- Ajouter, modifier ou supprimer un avis.
- Donner une note et un commentaire sur un film.
- Consulter les avis des spectateurs.
- Calculer la note moyenne d’un film.
- Cumuler des points après avoir visionné un film ou publié un avis.
- Échanger des points contre une récompense.
- Consulter ses points et ses récompenses.
- Désactiver une récompense si nécessaire.

**Exemple :**

Un spectateur donne une note de 4 sur 5 au film Avatar et ajoute un commentaire. Après plusieurs séances et avis publiés, il échange 100 points contre une récompense de 5 euros.

## 4. Architecture du projet

L’application est composée de trois services indépendants.

Chaque service possède ses propres données et gère ses propres fonctionnalités.

Les services communiquent grâce à des événements JSON afin de transmettre les informations nécessaires tout en restant découplés.

Cette organisation permet de limiter les dépendances entre les services, d’améliorer leur autonomie et de faciliter leur évolution.

## 5. Technologies envisagées

- JSON : représentation des commandes, agrégats et événements.
- NoSQL : stockage des données.
- GitHub : gestion et partage du projet.
- Architecture événementielle : communication entre les services.
