# UrbanHub — Documentation

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571.svg?logo=fastapi)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600.svg?logo=rabbitmq)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791.svg?logo=postgresql)

Bienvenue dans la documentation du projet **UrbanHub**, une plateforme microservices pour l’ingestion, la validation, la détection, l’association et l’analyse de données IoT.

## Présentation

UrbanHub permet de traiter des données de capteurs IoT à travers une chaîne de services découplés :

- ingestion des mesures brutes
- validation des données
- détection des anomalies et dépassements de seuil
- association et corrélation des mesures
- notification d’un système tiers
- exposition des résultats via une API

## Fonctionnalités principales

- réception de mesures IoT
- validation des données entrantes
- publication d’événements via RabbitMQ
- détection de seuils et d’alertes
- stockage et analyse des données
- corrélation des événements
- notification d’un CSU externe
- exposition d’une API de consultation

## Architecture globale

Voir la page dédiée : [Architecture](explanation/architecture.md)

## Démarrage rapide

Voir le guide pas à pas : [Getting Started](tutorials/getting-started.md)

## Référence

- [API](reference/api.md)
- [Variables d’environnement](reference/environment-variables.md)
- [Dépendances des services](reference/services.md)

## Guides pratiques

- [Configuration et lancement](how-to/configure-x.md)
- [Troubleshooting](how-to/troubleshooting.md)

## Diagramme de séquence

![diagramme de sequence UC3 V2.png](diagramme%20de%20sequence%20UC3%20V2.png)