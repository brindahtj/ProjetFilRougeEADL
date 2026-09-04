# Exercice 2 — Sécuriser et optimiser le stockage des données IoT

**Projet fil rouge : UrbanHub — Groupe [X]**
**Module BC04 · Jour 2 PM · Exercice 2 (noté 40 pts)**
**Mode utilisé : Mode A (MinIO Docker local — sans compte AWS facturé)**

---

## Contexte et environnement

Sujet IoT : [pollution eau / air / trafic / bruit / énergie — à préciser]
Environnement : simulation locale via **MinIO** (compatible API S3), aucun
compte AWS requis, cohérent avec l'approche retenue pour l'ensemble du
projet UrbanHub (Packer/Docker pour les golden images, LocalStack pour le
réseau).

MinIO a été retenu plutôt que LocalStack S3 pour cette partie, car
directement compatible boto3/mc sans compte ni token, et disposant d'une
console web native facilitant la prise de capture pour ce rendu.

---

## Étape 1 — Choix du service & upload

### Service retenu : MinIO (équivalent fonctionnel S3)

```bash
docker run -d \
  --name minio \
  --network my-network \
  -p 9005:9000 \
  -p 9006:9006 \
  -e "MINIO_ROOT_USER=admin_iot" \
  -e "MINIO_ROOT_PASSWORD=********" \
  -v "$HOME/amis/minio-data:/data" \
  minio/minio server /data --console-address ":9006"
```

- Port `9005` → API S3 (port interne 9000)
- Port `9006` → Console web d'administration

### Buckets créés

```bash
mc mb local/sc-raw-data
mc mb local/sc-processed-data
```

| Bucket | Rôle |
|---|---|
| `sc-raw-data` | Données brutes capteurs (préfixe `raw/`) |
| `sc-processed-data` | Données agrégées, destinées au dashboard |

### Génération et upload des données de test

Un script Python (`generate_data.py`) génère des mesures capteurs simulées
au format JSON et les upload directement via boto3 (endpoint MinIO) :

```python
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9005',
    aws_access_key_id='admin_iot',
    aws_secret_access_key='********',
    region_name='us-east-1'
)
# Génération de mesures capteurs horodatées, upload quotidien sous raw/YYYY-MM-DD.json
```

### Preuve — volumétrie chargée

```bash
mc du local/sc-raw-data
```
```
4.7MiB  30 objects      sc-raw-data
```

30 fichiers (un par jour sur la période de test), un objet par jour, cohérent
avec la fenêtre de rétention de 30 jours définie pour les données brutes.

> **Note méthodologique** : la cible initiale de ~5 Go pour la démonstration
> FinOps (visible dans le dimensionnement du script de génération) n'a pas
> été atteinte sur ce jeu de données final — le volume réel chargé est de
> 4,7 Mio pour 30 objets. Le mécanisme de lifecycle et la logique
> d'architecture restent identiques et valides indépendamment du volume ;
> seule l'ampleur de la démonstration chiffrée est réduite en conséquence
> (voir étape 3).

---

## Étape 2 — Lifecycle & chiffrement

### Stratégie de cycle de vie retenue

| Zone | Durée de rétention | Action | Justification |
|---|---|---|---|
| `raw/` (brut) | 30 jours | Suppression automatique (expiration) | Le brut n'a de valeur que pour alimenter l'agrégation ; au-delà de 30j, il n'est plus consulté |
| `processed/` (agrégé) | Illimitée | Conservation permanente | Volume réduit, toujours consulté (dashboards, historique) |

**Écart assumé par rapport à l'architecture AWS de référence** : le cours
(slide 17) illustre une chaîne Standard → Standard-IA → Glacier → Deep
Archive. Notre choix diffère volontairement : les données brutes IoT de ce
projet ne sont **jamais relues** au-delà de 30 jours (seuls les agrégats
comptent), donc les transiter vers des classes froides n'apporterait aucune
valeur — seule la **suppression** après la fenêtre d'utilité est pertinente.
Une classe froide n'a de sens que pour des données qu'on veut garder
accessibles à long terme sans les consulter souvent ; ici, on ne veut
justement plus les garder du tout.

### Implémentation — règle de lifecycle appliquée

```bash
mc ilm add local/sc-raw-data --expiry-days 30 --prefix "raw/"
```

### Preuve — règle active

```bash
mc ilm ls local/sc-raw-data
```

```
┌───────────────────────────────────────────────────────────────────────┐
│ Expiration for latest version (Expiration)                            │
├──────────────────────┬─────────┬────────┬──────┬────────────────┬─────┤
│ ID                   │ STATUS  │ PREFIX │ TAGS │ DAYS TO EXPIRE │ ... │
├──────────────────────┼─────────┼────────┼──────┼────────────────┼─────┤
│ dacogdohu42kd3jlc5s0 │ Enabled │ raw/   │ -    │             30 │false│
└──────────────────────┴─────────┴────────┴──────┴────────────────┴─────┘
```

Règle confirmée active (`Enabled`), s'applique au préfixe `raw/`, expiration
à 30 jours.

### Chiffrement

MinIO chiffre les échanges API en HTTPS lorsqu'un certificat TLS est
configuré (non activé dans cet environnement de test local — accès limité au
réseau interne du VPS, pas d'exposition publique). Pour la donnée at-rest,
MinIO supporte le chiffrement côté serveur (SSE-S3/SSE-KMS) via un serveur
KMS externe (Vault, par exemple) — non mis en œuvre dans ce test faute de
service KMS local disponible sans dépendance supplémentaire.

**Limite assumée et documentée** : contrairement à l'exemple SSE-KMS
présenté dans le cours (chapitre 2.4, chiffrement S3 natif AWS), l'absence de
service KMS local dans notre environnement Docker ne permet pas de
reproduire un chiffrement at-rest équivalent sans complexité disproportionnée
pour ce TP. En production réelle (AWS), la bucket policy imposerait
`aws:SecureTransport: false → Deny` et un chiffrement SSE-KMS par défaut,
comme vu en cours.

---

## Étape 3 — Optimisation coûts/performance

### Volumétrie observée

```bash
mc admin info local
```
```
4.7 MiB Used, 2 Buckets, 30 Objects
```

```bash
mc du local/sc-raw-data
mc du local/sc-processed-data
```
```
4.7MiB  30 objects      sc-raw-data
0B      0 objects       sc-processed-data
```

### Optimisations prévues (architecture cible)

| Levier | Implémentation prévue | Gain estimé |
|---|---|---|
| Compression gzip | Compression du payload JSON avant upload | ~-40% volume |
| Déduplication | Hash SHA-256 du payload, `head_object` avant upload pour éviter les doublons | ~-25% sur les doublons |
| Expiration automatique | Suppression du brut après 30j (voir étape 2) | -100% sur le brut au-delà de la fenêtre d'usage |

### État d'implémentation à date

La suppression automatique (`mc ilm add`) est **implémentée et vérifiée**
(étape 2). La compression et la déduplication sont **documentées et
scriptées** (voir extraits ci-dessous) mais n'ont pas encore été appliquées
au jeu de données actuellement chargé dans `sc-raw-data` — action à finaliser
avant le rendu définitif.

```python
# Compression avant upload
import gzip, io
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
    gz.write(json.dumps(payload).encode())
buf.seek(0)
s3.upload_fileobj(buf, 'sc-raw-data', 'raw/2026-08-31.json.gz')
```

```python
# Déduplication par hash
import hashlib
def hash_payload(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def upload_si_nouveau(payload, bucket, key_prefix):
    h = hash_payload(payload)
    key = f"{key_prefix}/{h}.json"
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except s3.exceptions.ClientError:
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload))
```

### `sc-processed-data` — non alimenté à date

Le bucket destiné aux agrégats est créé mais vide (`0B, 0 objects`) : le
pipeline d'agrégation (`sc-worker`/batchml) n'a pas encore écrit de résultat
dans MinIO à ce stade — l'intégration entre `batchMLScript.py` (consommateur
RabbitMQ, exercice 1) et l'écriture vers `sc-processed-data` reste à câbler
pour compléter le pipeline de bout en bout.

---

## Étape 4 — Rapport sécurité & coûts

### Matrice d'accès (IAM simulé / permissions applicatives)

| Composant | Droit | Justification |
|---|---|---|
| sc-ingest | Écriture seule sur `raw/` | Ne doit jamais lire ni modifier les données existantes |
| sc-worker | Lecture `raw/` + écriture `processed/` | Seul composant à traiter le brut |
| sc-api | Lecture seule `processed/` | Sert uniquement les données déjà agrégées |
| Anonyme | Aucun accès | Refus explicite par défaut |

> Cette matrice reprend le principe de moindre privilège étudié en cours
> (chapitre 2.4, slide 19), transposé aux rôles applicatifs du projet
> UrbanHub. Non encore implémentée sous forme de policy MinIO IAM à ce
> stade — à formaliser via `mc admin policy` si le temps le permet.

### Schéma du pipeline

```
[Capteurs IoT] --RabbitMQ (AMQP)--> [sc-ingest] --raw/--> [MinIO, 30j]
                                                                |
                                                       [sc-worker batch ML]
                                                       agrégation + nettoyage
                                                                |
                                                                v
                                                  [MinIO processed/, permanent]
                                                                |
                                                       [sc-api] --GetObject--> Dashboard
```

### Limites de l'environnement de simulation (résumé)

| Fonctionnalité AWS | Statut en environnement MinIO local |
|---|---|
| S3 Storage Lens | Non disponible (service propriétaire AWS, aucun équivalent conteneurisable) — remplacé par `mc admin info` / `mc du` |
| Transition Glacier / Deep Archive | Non applicable — MinIO n'a qu'un seul niveau de stockage ; remplacé par une politique d'expiration simple |
| Chiffrement SSE-KMS | Non implémenté — nécessiterait un service KMS externe (Vault), disproportionné pour ce TP |
| IAM avancé (policies par rôle) | Décrit en matrice d'accès théorique, non encore formalisé en policies MinIO réelles |

### Estimation FinOps (à titre indicatif, volumétrie de test réduite)

Sur la base du volume réellement chargé (4,7 Mio / 30 jours), l'application
de la règle d'expiration à 30 jours permet une économie de stockage de
**100% sur les données brutes au-delà de leur fenêtre d'utilité**, l'espace
étant automatiquement libéré sans intervention manuelle. À l'échelle de
production visée (~5 Go/30 jours par capteur), ce mécanisme reste identique
et le gain proportionnel équivalent.

---

## Synthèse — État d'avancement par rapport aux critères de notation

| Critère (40 pts) | Statut |
|---|---|
| VM lancée / service provisionné avec sizing adapté | ✅ MinIO déployé, buckets créés |
| Lifecycle chiffré appliqué | ✅ Expiration 30j vérifiée · ⚠️ Chiffrement at-rest documenté mais non implémenté (limite environnement) |
| Optimisation coûts/perf | ⚠️ Scripts prêts (compression, dédup) — application au jeu de données à finaliser |
| Documentation | ✅ Ce document |

### Actions restantes avant rendu final

1. Réappliquer le script de génération avec compression gzip activée sur les
   nouveaux uploads
2. Câbler l'écriture des résultats `batchMLScript.py` vers `sc-processed-data`
3. Capture d'écran de la console MinIO (`http://<IP_VPS>:9006`) pour
   illustration visuelle du rapport
4. (Optionnel, bonus) Formaliser la matrice d'accès en policies MinIO réelles
   via `mc admin policy create`
