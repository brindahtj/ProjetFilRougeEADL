# Architecture UrbanHub

## Vue d’ensemble

UrbanHub suit une architecture microservices événementielle.

Chaque service a une responsabilité claire afin de limiter le couplage et faciliter le déploiement indépendant, les tests et la maintenance.

## Services principaux

### `ingestion-service`
- reçoit les données brutes des capteurs
- prépare les messages à envoyer au pipeline
- publie les mesures vers le service de validation

### `validation-service`
- contrôle la structure des messages
- vérifie les champs obligatoires
- valide les types et les valeurs
- rejette les données invalides

### `detection-service`
- consomme les mesures validées
- compare les valeurs aux seuils
- publie une alerte si un seuil est dépassé

### `association-service`
- regroupe ou associe des données selon des règles métier
- produit des événements corrélés

### `analyse-service`
- expose les corrélations et analyses via une API
- interroge la base de données pour restituer l’historique

### `notification-service`
- consomme les alertes
- notifie un système externe, par exemple un CSU
- journalise les notifications envoyées

### `referential-service`
- fournit les seuils et règles métier
- centralise les données de référence utilisées par les autres services

## Bus d’événements

RabbitMQ joue le rôle de bus de messages entre les services.

Il permet :
- le découplage entre producteurs et consommateurs
- le traitement asynchrone
- la scalabilité horizontale
- la résilience face aux pics de charge

## Stockage

Le projet s’appuie sur PostgreSQL, et selon le contexte du projet, éventuellement TimescaleDB pour les données temporelles.

Le stockage sert à :
- conserver les mesures
- historiser les alertes
- conserver les corrélations
- permettre l’analyse et la consultation

## Flux de traitement

1. un capteur envoie une mesure brute
2. la mesure est reçue par le service d’ingestion
3. le service de validation contrôle le message
4. si la mesure est valide, elle est publiée dans RabbitMQ
5. le service de détection consomme la mesure
6. si un seuil est dépassé, une alerte est publiée
7. le service de notification transmet l’alerte au CSU
8. les services d’analyse et d’association traitent les données corrélées

## Pourquoi cette architecture ?

Cette architecture a été choisie pour :

- séparer les responsabilités
- faciliter le développement en équipe
- rendre les services testables indépendamment
- permettre l’évolution d’un service sans casser les autres
- supporter une charge croissante

## Conclusion

UrbanHub est conçu comme un système modulaire, extensible et orienté événements.