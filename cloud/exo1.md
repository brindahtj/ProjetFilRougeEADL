
   
   # Les 3 golden images UrbanHub — prêtes

## ✅ Déjà construites et testées
| Image | Taille | Vérifié |
|---|---|---|
| `urbanhub-fastapi-golden:v1` | 249 Mo | `/health` répond `{"status":"ok"}` |
| `urbanhub-rabbitmq-golden:v1` | 284 Mo | `rabbitmq-server` + plugin management actif |
| `urbanhub-batchml-golden:v1` | 1,29 Go | numpy 2.5.2 · pandas 3.0.5 · scikit-learn 1.9.0 |

```bash
docker images --filter reference='urbanhub-*'
```

## Reconstruire
   ```bash
cd ~/amis
packer init .                         # une fois
packer build .                        # les 3
packer build -only=fastapi.docker.fastapi .    # une seule
packer build -var version_tag=v2 .    # autre tag
```

## Les lancer
```bash
# FastAPI  (choisissez un port LIBRE : 8083-8089)
docker run -d --name api -p 8085:8000 -w /app urbanhub-fastapi-golden:v1 \
  uvicorn main:app --host 0.0.0.0 --port 8000

curl http://127.0.0.1:8085/health

# RabbitMQ (5672 = AMQP, 15672 = console web)

docker run -d --name mq -p 8086:15672 -p 8087:5672 urbanhub-rabbitmq-golden:v1 \
  bash -c "rabbitmq-server"

# Batch ML (conteneur jetable)
docker run --rm -v "$PWD:/work" urbanhub-batchml-golden:v1 python3 mon_script.py
```
Arrêter : `docker rm -f api mq`

## ⚠️ Ce sont des images Docker, pas des AMI Amazon
Une **AMI** ne peut être créée que dans AWS : `packer build` lance une vraie instance EC2.
Sans identifiants AWS, Packer répond `No valid credential sources found`.
   
   
   
   Les mêmes 3 images en **vraies AMI** sont prêtes dans **`~/amis/aws/`**
(`packer validate` OK). Dès que l'enseignant fournit les identifiants :
```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=eu-west-3
cd ~/amis/aws && packer init . && packer build .
```
La logique est identique — seul le `source` change (`docker` → `amazon-ebs`).
> Ne mettez jamais ces clés dans un `.hcl` ni sur GitHub.

## 💡 Rappel qui coûte cher
Packer ne lit que les fichiers en **`.pkr.hcl`**. Un fichier `packer.hcl` est **ignoré**
(« Could not find any config file »). Renommez : `mv packer.hcl main.pkr.hcl`.