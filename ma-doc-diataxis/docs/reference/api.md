# Référence API

## validation-service

### POST `/validate`
Valide une mesure brute.

#### Exemple
```json
{
  "type": "pollution",
  "city": "Paris",
  "zone": "nord",
  "pollutant": "no2",
  "value": 220
}
```
valid: true si la mesure est acceptable
valid: false sinon
 
## detection-service
### Rôle
- consommer les mesures validées
- comparer aux seuils
- publier des alertes

### Événements publiés
- `alerts`

 
## referential-service
### Rôle
fournir les règles et seuils aux autres services
### Endpoints
- `GET /thresholds`
  Retourne tous les seuils actifs.
- `GET /thresholds/{key}`
  Retourne un seuil précis.
- `POST /thresholds`
  Crée un seuil.
- `PUT /thresholds/{key}`
  Met à jour un seuil.
- `DELETE /thresholds/{key}`
  Désactive un seuil.
 
## analyse-service
### Rôle
exposer les corrélations aux clients UrbanHub
### Endpoints
- `GET /correlations`
  Retourne les corrélations calculées.
- `GET /correlations/{city}`
  Retourne les corrélations pour une ville spécifique.
- `GET /correlations/{city}/{zone}`
  Retourne les corrélations d’une zone.

## notification-service
### Rôle
Notifier le CSU externe à partir des alertes reçues.
### Comportement
- consommer les alertes publiées par le `detection-service`
- envoyer une notification HTTP POST vers l’URL du CSU
- journaliser les notifications envoyées si nécessaire