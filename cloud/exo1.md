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


commandes pour aws
# Module BC04 — Exercice 1 : Provisionner une VM & Packager sa Golden Image

Ce document rassemble l'ensemble des commandes nécessaires pour valider les 4 étapes de l'**Exercice 1 (Page 13 du support)** sur le projet fil rouge *Smart City IoT*.

---

## Étape 1 : Sélectionner & Provisionner les Ressources Cloud

### Option A — AWS CLI / AWS Academy (Mode C : AWS Réel)

#### 1.1. Démarrer l'instance EC2 (Ubuntu 22.04)
```bash
# Lancement d'une instance t3.medium ou r6i.2xlarge selon le sujet IoT
aws ec2 run-instances \
    --image-id ami-0abc123456789def0 \
    --instance-type t3.medium \
    --count 1 \
    --key-name ma-cle-ssh \
    --subnet-id subnet-0abc1234 \
    --security-group-ids sg-0abc1234 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Group,Value=smart-city},{Key=Name,Value=sc-ingest-vm}]'
  1.2. (Optionnel) Créer et attacher un disque EBS gp3 pour le stockage IoT (Slide 10)
    # 1. Création d'un volume EBS gp3 de 100 Go avec 6000 IOPS
aws ec2 create-volume \
    --volume-type gp3 \
    --size 100 \
    --iops 6000 \
    --throughput 500 \
    --availability-zone eu-west-3a \
    --tag-specifications 'ResourceType=volume,Tags=[{Key=Group,Value=smart-city}]'

# 2. Attachement du volume à l'instance créée
aws ec2 attach-volume \
    --volume-id vol-0abc123456789def0 \
    --instance-id i-0abc123456789def0 \
    --device /dev/sdf

    Option B — VPS Local / Docker (Mode A : VPS mis à disposition)
    # Connexion au VPS de groupe
ssh ubuntu@bc04.vps.example

# Démarrage d'un conteneur Ubuntu 22.04 simulant la VM
docker run -d --name bc04 -p 80:80 -p 1883:1883 ubuntu:22.04

Étape 2 : Installer & Configurer l'Environnement Applicatif
Connexion à la VM créée pour préparer la stack applicative Python / IoT.
# Connexion SSH à la VM
ssh -i ~/.ssh/id_rsa ubuntu@<IP_PUBLIQUE_VM>

# 1. Mise à jour de l'OS Ubuntu 22.04
sudo apt-get update && sudo apt-get upgrade -y

# 2. Formater et monter le volume EBS additionnel (dans la VM - Slide 10)
sudo mkfs -t xfs /dev/nvme1n1
sudo mkdir -p /data/sensors
sudo mount /dev/nvme1n1 /data/sensors

# 3. Installation des outils de base, Python 3.11, Docker et dépendances IoT (Slide 9)
sudo apt-get install -y python3-pip python3-venv docker.io git
pip3 install boto3 paho-mqtt fastapi uvicorn psutil

# 4. Nettoyage et préparation avant la capture d'image (Slide 14)
# Désactivation du swap pour éviter un boot instable
sudo swapoff -a

# Suppression des clés SSH temporaires et des caches
rm -f ~/.ssh/authorized_keys
sudo rm -rf /tmp/* /var/log/*

Étape 3 : Créer l'Image de Référence (Golden Image AMI)
Méthode 1 — AWS CLI (AWS Réel / AWS Academy - Slide 14)
# Capture de l'instance EC2 sous forme d'AMI
aws ec2 create-image \
    --instance-id i-0abc123456789def0 \
    --name "sc-v1-$(date +%F)" \
    --description "Golden Image Smart City IoT - Ubuntu 22.04 Python FastApi" \
    --no-reboot
Méthode 2 — HashiCorp Packer (packer.pkr.hcl - Slide 9)
Si vous utilisez Packer pour industrialiser la création de l'AMI :

source "amazon-ebs" "ubuntu-smart-city" {
  ami_name      = "smart-city-${local.timestamp}"
  instance_type = "t3.medium"
  region        = "eu-west-3"
  source_ami_filter {
    name = "ubuntu/images/*ubuntu-jammy-22.04-amd64-server-*"
  }
  run_shell_commands = [
    "sudo apt-get update",
    "sudo apt-get install -y python3-pip docker.io",
    "pip3 install boto3 paho-mqtt fastapi psutil"
  ]
  tags = { Group = "smart-city" }
}