# API Specification - Smart City IoT

Base URL : `/api/v1`

## 1. Zones

### GET /api/v1/zones
Liste toutes les zones.

**Réponse 200**
```json
{
  "status": 200,
  "data": [
    {
      "id": "zone-paris",
      "name": "Paris",
      "latitude": 48.8566,
      "longitude": 2.3522,
      "type": "urban",
      "createdAt": "2026-07-01T10:00:00Z"
    }
  ],
  "message": "1 zones trouvées"
}
```

### GET /api/v1/zones/{zoneId}
Retourne une zone précise.

### POST /api/v1/zones
Crée une zone.

**Body**
```json
{
  "name": "Paris",
  "latitude": 48.8566,
  "longitude": 2.3522,
  "type": "urban"
}
```

### PUT /api/v1/zones/{zoneId}
Met à jour une zone.

### DELETE /api/v1/zones/{zoneId}
Supprime une zone.

---

## 2. Sensors

### GET /api/v1/sensors
Retourne la liste des capteurs.

### GET /api/v1/sensors/{sensorId}
Retourne un capteur précis.

### GET /api/v1/sensors?zoneId={zoneId}
Filtre les capteurs par zone.

### GET /api/v1/sensors?status={status}
Filtre les capteurs par statut : `NORMAL`, `WARNING`, `CRITICAL`.

### POST /api/v1/sensors
Crée un capteur.

**Body**
```json
{
  "id": "sensor-pollution-001",
  "name": "Capteur pollution Paris 1",
  "type": "pollution",
  "zoneId": "zone-paris",
  "latitude": 48.8566,
  "longitude": 2.3522
}
```

### PUT /api/v1/sensors/{sensorId}
Met à jour un capteur.

### DELETE /api/v1/sensors/{sensorId}
Supprime un capteur.

---

## 3. Metrics

### GET /api/v1/metrics
Retourne la liste des métriques.

### GET /api/v1/metrics/{metricId}
Retourne une métrique précise.

### GET /api/v1/metrics?sensorId={sensorId}
Retourne les métriques d’un capteur.

### GET /api/v1/metrics?zoneId={zoneId}
Retourne les métriques d’une zone.

### POST /api/v1/metrics
Crée une métrique.

**Body**
```json
{
  "sensorId": "sensor-pollution-001",
  "type": "pollution",
  "value": 65.2,
  "unit": "µg/m³",
  "timestamp": "2026-07-01T10:00:00Z",
  "isAnomaly": true
}
```

### PUT /api/v1/metrics/{metricId}
Met à jour une métrique.

### DELETE /api/v1/metrics/{metricId}
Supprime une métrique.

---

## 4. Format des erreurs

### Cas : capteur hors ligne
**Status HTTP :** `503 Service Unavailable`

**Body**
```json
{
  "status": 503,
  "error": {
    "code": "SENSOR_OFFLINE",
    "message": "Le capteur est actuellement hors ligne",
    "resource": "/api/v1/sensors/sensor-pollution-001",
    "timestamp": "2026-07-01T10:00:00Z",
    "details": {
      "sensorId": "sensor-pollution-001",
      "sensorType": "pollution",
      "lastSeen": "2026-06-30T09:55:00Z",
      "offlineSince": "2026-06-30T09:55:00Z"
    },
    "retryable": true,
    "retryAfterSeconds": 60,
    "correlationId": "req-123456"
  }
}
```

### Cas : ressource introuvable
**Status HTTP :** `404 Not Found`

**Body**
```json
{
  "status": 404,
  "error": {
    "code": "NOT_FOUND",
    "message": "Ressource introuvable",
    "resource": "/api/v1/sensors/sensor-inconnu"
  }
}
```

### Cas : champ manquant
**Status HTTP :** `400 Bad Request`

**Body**
```json
{
  "status": 400,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Champ manquant",
    "details": {
      "missingField": "value"
    }
  }
}
```