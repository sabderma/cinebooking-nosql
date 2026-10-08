# CinéBooking — Projet NoSQL

## 1. Présentation du projet

CinéBooking est une application de réservation de places de cinéma en ligne.

Elle permet aux utilisateurs de consulter les films disponibles, de choisir une séance et de réserver des places.

L'application est composée de trois services indépendants qui communiquent entre eux.

## 2. Objectifs du projet

- Consulter les films et les séances disponibles.
- Réserver et annuler des places de cinéma.
- Consulter les prix et utiliser des codes promotionnels.
- Faire communiquer les services grâce à des événements.
- Utiliser le format JSON pour représenter les données.

## 3. Les services de l'application

### Service 1 : Films et séances

Ce service gère les films, les salles et les horaires des séances.

### Service 2 : Réservations

Ce service permet de réserver des places, de consulter les réservations et de les annuler.

### Service 3 : Tarification et promotions

Ce service gère les prix des billets, les tarifs réduits et les codes promotionnels.

## 4. Architecture du projet

L'application utilise une architecture composée de trois services indépendants.

Chaque service possède ses propres données et peut communiquer avec les autres grâce à des événements.

Les données seront représentées au format JSON dans le cadre du projet NoSQL.
