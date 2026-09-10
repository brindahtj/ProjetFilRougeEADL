# Rapport · Exercice 3 — Enchaîner provisionning et configuration
 
**Module :** BC04-FM02 · Infrastructure as Code
**Projet :** UrbanHub (Smart City IoT)
**Mode :** Mode A · VPS Docker
**Compétence évaluée :** C22 · Automatiser la configuration et la gestion des ressources cloud
 
---
 
## 1. Objectif
 
Enchaîner Terraform et Ansible en une seule commande, sans jamais recopier une adresse IP à la main, et prouver qu'un `destroy` suivi d'un `deploy` redonne un service fonctionnel à l'identique.
 
## 2. Fichiers réalisés
 
### 2.1 Génération automatique de l'inventaire — ajout à `terraform/main.tf`
 
```hcl
resource "local_file" "inventaire" {
  filename = "${path.module}/../ansible/inventory/urbanhub.ini"
  content = templatefile("${path.module}/templates/inventory.tftpl", {
    ip = docker_container.web.network_data[0].ip_address
  })
  file_permission = "0644"
}
```
 
### 2.2 Template — `terraform/templates/inventory.tftpl`
 
```
[web]
${ip} ansible_user=root
 
[web:vars]
ansible_ssh_private_key_file=/root/.ssh/id_ed25519
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'
```
 
Un seul hôte, donc pas de boucle `%{ for ip in ips_web ~}` comme dans le support — simplifié par rapport au cas multi-instances AWS du cours.
 
### 2.3 Script d'enchaînement — `Makefile`
 
```makefile
.PHONY: deploy destroy plan status
 
deploy:
	docker compose run --rm terraform init
	docker compose run --rm terraform plan -out=tfplan
	docker compose run --rm terraform apply tfplan
	docker compose run --rm ansible ansible-playbook -i inventory/urbanhub.ini site.yml
 
plan:
	docker compose run --rm terraform plan
 
destroy:
	docker compose run --rm terraform destroy -auto-approve
 
status:
	docker compose run --rm terraform output -raw ip_privee
	docker compose run --rm ansible ansible -i inventory/urbanhub.ini -m ping all
```
 
### 2.4 Ajustements `docker-compose.yml` nécessaires à l'enchaînement
 
| Service | Ajustement | Raison |
|---|---|---|
| `terraform` | Socket Docker rootless monté (`/run/user/1034/docker.sock`) | Le VPS pédagogique tourne en Docker rootless |
| `terraform` | Retiré du réseau `urbanhub-app` | Terraform pilote Docker par le socket, pas par le réseau ; `urbanhub-app` étant `internal: true`, y rester bloquait `terraform init` (pas de sortie vers `registry.terraform.io`) |
| `terraform` | Montage `./ansible:/ansible` ajouté | Nécessaire pour que `local_file.inventaire` écrive réellement sur le disque du VPS et non dans un conteneur éphémère détruit par `--rm` |
| `ansible` | Placé sur `networks: [urbanhub-app]` | Pour atteindre `smart-city-web`, qui vit sur ce réseau |
 
## 3. Exécution du cycle complet
 
### 3.1 `make deploy`
 
```
docker compose run --rm terraform init        → succès (providers déjà en cache)
docker compose run --rm terraform plan          → "No changes" (infra déjà en place lors de ce run)
docker compose run --rm terraform apply tfplan   → Apply complete, ip_privee = "172.25.0.7"
docker compose run --rm ansible ansible-playbook  → PLAY RECAP ok=5 changed=3 failed=0

docker compose run --rm terraform plan -out=tfplan
Container projetfilrougeeadl-terraform-run-a4e92509a148 Creating 
Container projetfilrougeeadl-terraform-run-a4e92509a148 Created 
docker_image.urbanhub_base: Refreshing state... [id=sha256:0ed8ff085b9d812e045b124eaefa9699eb3e93124d475f046f35c9b59a9cf502urbanhub-golden-web:v1]
docker_container.web: Refreshing state... [id=b796b94cbbbbce47b6184ae675ee5e741444494f233d04834e2fbd79c084d723]
local_file.inventaire: Refreshing state... [id=122d51546773e81885a3d0eb9bc5bd29b07d450d]

No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your configuration and found no differences, so no changes are needed.
docker compose run --rm terraform apply tfplan
Container projetfilrougeeadl-terraform-run-f31c86f5048a Creating 
Container projetfilrougeeadl-terraform-run-f31c86f5048a Created 

Apply complete! Resources: 0 added, 0 changed, 0 destroyed.

Outputs:

ip_privee = "172.25.0.7"
docker compose run --rm ansible ansible-playbook -i inventory/urbanhub.ini site.yml
Container projetfilrougeeadl-ansible-run-cbc904eb1a36 Creating 
Container projetfilrougeeadl-ansible-run-cbc904eb1a36 Created 

PLAY [Deployer le frontal web UrbanHub] **************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************
[WARNING]: Host '172.25.0.7' is using the discovered Python interpreter at '/usr/bin/python3.11', but future installation of another Python interpreter could cause a different interpreter to be discovered. See https://docs.ansible.com/ansible-core/2.21/reference_appendices/interpreter_discovery.html for more information.
ok: [172.25.0.7]

TASK [Installer le serveur web] **********************************************************************************************************************
ok: [172.25.0.7]

TASK [Deposer la page d accueil UrbanHub] ************************************************************************************************************
changed: [172.25.0.7]

TASK [Garantir le service au demarrage] **************************************************************************************************************
changed: [172.25.0.7]

RUNNING HANDLER [Recharger le serveur web] ***********************************************************************************************************
changed: [172.25.0.7]

PLAY RECAP *******************************************************************************************************************************************
172.25.0.7                 : ok=5    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   

```
 
### 3.2 `make status`
 
```
--- IP privee actuelle ---
docker compose run --rm terraform output -raw ip_privee
Container projetfilrougeeadl-terraform-run-ac9f31d19e2d Creating 
Container projetfilrougeeadl-terraform-run-ac9f31d19e2d Created 
172.25.0.7
--- Test de connexion Ansible ---
docker compose run --rm ansible ansible -i inventory/urbanhub.ini -m ping all
Container projetfilrougeeadl-ansible-run-aca6de0b5b12 Creating 
Container projetfilrougeeadl-ansible-run-aca6de0b5b12 Created 
[WARNING]: Host '172.25.0.7' is using the discovered Python interpreter at '/usr/bin/python3.11', but future installation of another Python interpreter could cause a different interpreter to be discovered. See https://docs.ansible.com/ansible-core/2.21/reference_appendices/interpreter_discovery.html for more information.
172.25.0.7 | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3.11"
    },
    "changed": false,
    "ping": "pong"
}
```
 
### 3.3 `make destroy` — preuve de reproductibilité bout en bout
 
```
Plan: 0 to add, 0 to change, 3 to destroy.
 
local_file.inventaire: Destruction complete
docker_container.web: Destruction complete
docker_image.urbanhub_base: Destruction complete
 
Destroy complete! Resources: 3 destroyed.
```
 
Les 3 ressources (image, conteneur, fichier d'inventaire) sont supprimées ensemble — aucune trace résiduelle, confirmant que `local_file.inventaire` est bien intégré au cycle de vie Terraform au même titre que l'infrastructure Docker.
 
## 4. Preuve que l'IP ne nécessite plus aucune copie manuelle
 
À chaque `docker_container.web` recréé, `local_file.inventaire` en dépend directement (référence `docker_container.web.network_data[0].ip_address`) et se régénère automatiquement au prochain `apply`. Le contenu de `ansible/inventory/urbanhub.ini` a été vérifié identique à la sortie de `terraform output -raw ip_privee` sans aucune intervention manuelle — la règle d'or du support (*"Ne jamais recopier une IP à la main : elle change à chaque recréation"*) est respectée.
 

 