# Configuration et lancement d’UrbanHub

## Prérequis

Avant de commencer, assure-toi d’avoir :

- Python 3.11 ou plus
- Docker et Docker Compose
- Git
- un fichier `.env` correctement configuré

## Étape 1 — Récupérer le projet

Clone le dépôt puis place-toi à la racine du projet.

## Étape 2 — Configurer les variables d’environnement

Crée ou complète le fichier `.env` avec les valeurs nécessaires pour :
- RabbitMQ
- PostgreSQL
- les services HTTP
- les paramètres métier

Voir aussi : [Variables d’environnement](../reference/environment-variables.md)

## Étape 3 — Lancer les dépendances

Si le projet utilise Docker Compose, démarre les services techniques :

```powershell
docker compose up -d

```

## Étape 4 — Lancer les services applicatifs
Selon l’organisation du dépôt, tu peux lancer chaque service séparément ou via Docker.
Exemples: 

```powershell
python -m app.main
```
ou 
```powershell
uvicorn app.main:app --reload
```
## Étape 5 — Vérifier le bon fonctionnement
Vérifie :
- que RabbitMQ est joignable
- que PostgreSQL est démarré
- que les APIs répondent
- que les consommateurs RabbitMQ sont actifs
## Commandes utiles
- Voir les conteneurs
```powershell
docker ps
```
- Voir les logs 
```powershell
docker compose logs -f
```
- Arrêter les services
```powershell
docker compose down
```
### Notes
Les commandes exactes peuvent varier selon le service concerné et la façon dont le projet est lancé.
