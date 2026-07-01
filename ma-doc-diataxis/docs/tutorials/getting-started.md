# Getting Started

Ce guide t’aide à démarrer rapidement avec UrbanHub.

## Objectif

À la fin de ce tutoriel, tu sauras :
- configurer le projet
- lancer les services
- envoyer une première donnée
- comprendre le cheminement d’une mesure

## Étape 1 — Préparer l’environnement

Vérifie que les prérequis sont installés :
- Python
- Docker
- Docker Compose

## Étape 2 — Configurer le fichier `.env`

Complète les variables d’environnement nécessaires au projet.

Voir la référence : [Variables d’environnement](../reference/environment-variables.md)

## Étape 3 — Démarrer les dépendances

Lance RabbitMQ et PostgreSQL si le projet les utilise via Docker.

## Étape 4 — Lancer les services

Démarre les services applicatifs selon la méthode choisie :
- Docker
- exécution locale
- lancement par module Python

## Étape 5 — Tester une mesure

Envoie une mesure brute vers le système, puis observe :
- sa validation
- sa publication
- sa détection éventuelle
- la notification si seuil dépassé

## Étape 6 — Consulter les résultats

Vérifie :
- les logs
- la base de données
- les réponses API
- les messages RabbitMQ

## Suite

Une fois ce guide terminé, consulte :
- [Architecture](../explanation/architecture.md)
- [Référence API](../reference/api.md)
- [Troubleshooting](../how-to/troubleshooting.md)