## 4. `docs/how-to/troubleshooting.md`
```md
# Troubleshooting

## RabbitMQ ne démarre pas

### Symptômes
- le service ne répond pas
- les consommateurs ne se connectent pas

### Vérifications
- le conteneur est bien lancé
- le port configuré n’est pas déjà utilisé
- les identifiants du `.env` sont corrects

## PostgreSQL est inaccessible

### Symptômes
- erreurs de connexion à la base
- les services d’analyse ou de notification échouent

### Vérifications
- la base est démarrée
- l’URL de connexion est correcte
- le mot de passe et le nom de base sont valides

## Variable d’environnement manquante

### Symptômes
- erreur au démarrage
- `KeyError` ou variable vide

### Vérifications
- le fichier `.env` existe
- la variable est bien déclarée
- le nom de la variable correspond exactement à celui attendu

## Port déjà utilisé

### Symptômes
- l’application ne démarre pas
- erreur du type “address already in use”

### Solution
- arrêter le processus qui utilise le port
- ou modifier le port dans la configuration

## Service qui redémarre en boucle

### Causes possibles
- dépendance indisponible
- erreur dans le code
- variable de configuration incorrecte
- migration ou schéma de base incomplet

## Conseils généraux

- consulter les logs du service concerné
- vérifier le `.env`
- tester les dépendances une par une
- démarrer d’abord RabbitMQ et PostgreSQL