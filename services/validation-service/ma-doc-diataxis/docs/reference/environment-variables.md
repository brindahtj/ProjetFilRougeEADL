# Variables d'environnement

Cette page récapitule les variables utilisées par UrbanHub.

## RabbitMQ

- `RABBITMQ_HOST` : hôte RabbitMQ, par défaut `rabbitmq`
- `RABBITMQ_PORT` : port AMQP, par défaut `5672`
- `RABBITMQ_USER` : utilisateur RabbitMQ, par défaut `guest`
- `RABBITMQ_PASS` : mot de passe RabbitMQ, par défaut `guest`
- `EXCHANGE` : exchange RabbitMQ partagé, par défaut `urbanhub`

## PostgreSQL

- `POSTGRES_HOST` : hôte PostgreSQL, par défaut `postgres`
- `POSTGRES_PORT` : port PostgreSQL, par défaut `5432`
- `POSTGRES_USER` : utilisateur PostgreSQL, par défaut `urbanhub_user`
- `POSTGRES_PASSWORD` : mot de passe PostgreSQL, par défaut `urbanhub_password`
- `POSTGRES_DB` : base de données, par défaut `urbanhub`

## Services HTTP

- `VALIDATION_SERVICE_URL` : URL du service de validation
- `REFERENTIAL_URL` : URL du service référentiel

## Paramètres métier

- `THRESHOLD_REFRESH_SECONDS` : intervalle de rafraîchissement des seuils
- `POLL_PREFETCH` : nombre de messages RabbitMQ consommés en avance