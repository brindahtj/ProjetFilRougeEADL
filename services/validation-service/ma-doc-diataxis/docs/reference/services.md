# Services UrbanHub

## Ingestion Service

- reçoit les mesures brutes
- appelle le service de validation
- renvoie les résultats de traitement

## Validation Service

- valide les mesures IoT
- publie les mesures acceptées dans RabbitMQ
- expose `GET /health`, `POST /validate` et `POST /validate-batch`

## Referential Service

- expose les seuils et règles métier
- sert de source de vérité pour les autres services
- fournit notamment `GET /thresholds`

## Detection Service

- consomme les mesures validées
- compare les valeurs aux seuils du référentiel
- publie des alertes dans RabbitMQ

## Association Service

- associe les mesures pollution et trafic
- produit des événements corrélés

## Analyse Service

- expose les analyses et corrélations via une API
- s’appuie sur PostgreSQL

## Notification Service

- consomme les alertes
- transmet les notifications à un système externe

## Bus de messages

RabbitMQ sert de bus événementiel entre les services producteurs et consommateurs.# Dépendances des services

## `ingestion-service`
### Rôle
Recevoir et transmettre les mesures IoT.

### Dépendances
- peut dépendre d’un endpoint de validation
- peut publier vers RabbitMQ

## `validation-service`
### Rôle
Valider les données entrantes.

### Dépendances
- RabbitMQ
- schéma des messages
- règles de validation métier

## `detection-service`
### Rôle
Détecter les dépassements de seuil.

### Dépendances
- RabbitMQ
- `referential-service`
- base de données de référence éventuelle

## `association-service`
### Rôle
Associer des données selon la logique métier.

### Dépendances
- RabbitMQ
- règles d’association
- base de stockage si nécessaire

## `analyse-service`
### Rôle
Exposer les analyses et corrélations.

### Dépendances
- base PostgreSQL / TimescaleDB
- données produites par les autres services

## `notification-service`
### Rôle
Notifier le CSU externe.

### Dépendances
- RabbitMQ
- URL du CSU
- base de journalisation éventuelle

## `referential-service`
### Rôle
Fournir les seuils et règles métier.

### Dépendances
- base de données
- API HTTP

## Matrice simplifiée

| Service | RabbitMQ | Base de données | API externe |
|--------|----------|-----------------|-------------|
| ingestion-service | oui | non | éventuellement |
| validation-service | oui | non | non |
| detection-service | oui | oui / non | oui |
| association-service | oui | oui / non | non |
| analyse-service | non | oui | non |
| notification-service | oui | oui / non | oui |
| referential-service | non | oui | non |