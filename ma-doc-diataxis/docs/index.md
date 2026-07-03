# UrbanHub

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571.svg?logo=fastapi)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600.svg?logo=rabbitmq)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791.svg?logo=postgresql)

UrbanHub est une plateforme microservices orientée événements pour traiter des mesures de capteurs, les valider, détecter les alertes, puis les transmettre à des services spécialisés.

## Vue d’ensemble

Le projet est structuré autour d’un bus d’événements RabbitMQ et de services spécialisés:

- `ingestion-service` reçoit les données brutes
- `validation-service` valide les données à partir du flux d’ingestion
- `detection-service` consomme les mesures validées et produit des alertes
- `association-service` consomme aussi les mesures validées pour produire des corrélations
- `notification-service` consomme les alertes issues de la détection
- `referential-service` fournit les seuils et règles métier
- `analyse-service` expose les analyses et corrélations

## Flux événementiel

```mermaid
flowchart LR
	sensors[API Capteurs] --> ingestion[ingestion-service]
	ingestion --> bus1[(RabbitMQ\nBus d'événements)]
	bus1 --> validation[validation-service]
	validation --> bus2[(RabbitMQ\nBus d'événements)]
	bus2 --> detection[detection-service]
	bus2 --> association[association-service]
	detection --> bus3[(RabbitMQ\nBus d'événements)]
	bus3 --> notification[notification-service]
	notification --> csu[CSU / Système externe]
	referential[referential-service] --> detection
	analyse[analyse-service] <--> db[(PostgreSQL)]
```

## Démarrage rapide

1. Lancer le projet complet: `docker compose up -d --build`
2. Ouvrir Swagger du service de validation: `http://localhost:8002/docs`
3. Ouvrir la documentation MkDocs: `mkdocs serve`

## Accès rapides

- [Architecture](explanation/architecture.md)
- [Tutoriel de démarrage](tutorials/getting-started.md)
- [Référence API](reference/api.md)
- [Variables d’environnement](reference/environment-variables.md)
- [Services](reference/services.md)

## Points clés

- validation des mesures par contrat Pydantic et Swagger
- publication d’événements via RabbitMQ
- consommation asynchrone par les services métiers
- stockage PostgreSQL pour l’analyse et l’historisation

## Diagramme du projet

![diagramme de sequence UC3 V2.png](diagramme%20de%20sequence%20UC3%20V2.png)