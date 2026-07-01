# Dépendances des services

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