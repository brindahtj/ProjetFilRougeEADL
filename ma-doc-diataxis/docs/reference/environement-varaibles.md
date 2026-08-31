# Variables d’environnement

Ce document liste les variables d’environnement utilisées par UrbanHub.

## Variables communes

### `ENVIRONMENT`
- Description : environnement d’exécution
- Valeurs possibles : `development`, `test`, `production`

### `LOG_LEVEL`
- Description : niveau de journalisation
- Valeurs possibles : `DEBUG`, `INFO`, `WARNING`, `ERROR`

## RabbitMQ

### `RABBITMQ_HOST`
- Description : nom d’hôte du broker RabbitMQ

### `RABBITMQ_PORT`
- Description : port de connexion RabbitMQ

### `RABBITMQ_USER`
- Description : utilisateur RabbitMQ

### `RABBITMQ_PASSWORD`
- Description : mot de passe RabbitMQ

## PostgreSQL

### `POSTGRES_HOST`
- Description : nom d’hôte de PostgreSQL

### `POSTGRES_PORT`
- Description : port PostgreSQL

### `POSTGRES_DB`
- Description : nom de la base de données

### `POSTGRES_USER`
- Description : utilisateur PostgreSQL

### `POSTGRES_PASSWORD`
- Description : mot de passe PostgreSQL

## API / services

### `API_HOST`
- Description : adresse d’écoute de l’API

### `API_PORT`
- Description : port HTTP de l’API

### `CSU_WEBHOOK_URL`
- Description : URL de notification du CSU externe

## Remarques

Les variables exactes peuvent varier selon le service.  
Il est recommandé d’indiquer ici :
- si la variable est obligatoire
- sa valeur par défaut
- le service qui l’utilise