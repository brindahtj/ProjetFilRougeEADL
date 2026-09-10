Rapport · Exercice 4 — Montée en charge sans interruption de service
Module : Infrastructure as Code

Projet : Smart City / ProjetFilRougeEADL

Étudiant : Brendah

Contexte : Passage du serveur web de t3.micro à t3.small pour absorber la hausse de trafic sur le portail Smart City, avec gestion de la mise à l'échelle (nb_web = 2) et rolling update Ansible (serial).

1. Objectif
Mettre à niveau la capacité de traitement du portail Smart City en faisant évoluer le type d'instance EC2 (t3.micro → t3.small) tout en prévenant les interruptions de service, en configurant la redondance applicative via la variable nb_web = 2 et en adaptant le déploiement Ansible.

2. Modifications apportées à la configuration IaC
2.1 Évolution de la configuration Terraform — terraform/aws/main.tf
Terraform
variable "instance_type" {
  description = "Type d'instance pour le serveur web"
  type        = string
  default     = "t3.small"
}

variable "nb_web" {
  description = "Nombre d'instances web a deployer"
  type        = number
  default     = 2
}

resource "aws_instance" "web" {
  count         = var.nb_web
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "smartcity-web-${count.index + 1}"
  }
}
Passage à t3.small : Augmentation des ressources (RAM/CPU) pour absorber la charge.

Ajout de nb_web = 2 : Déploiement multi-instances pour assurer la haute disponibilité.

Conservation du lifecycle : La directive create_before_destroy = true sur aws_instance.web prévient toute suppression destructive inattendue lors de la mise à jour des ressources.

2.2 Stratégie de mise à jour progressive — ansible/site.yml
YAML
- name: Deployer le frontal web Smart City
  hosts: web
  serial: 1
  become: true
  tasks:
    - name: Installer le serveur web NGINX
      apt:
        name: nginx
        state: present
        update_cache: yes

    - name: Deposer la page d d'accueil Smart City
      copy:
        src: files/index.html
        dest: /var/www/html/index.html
        mode: '0644'
      notify: Recharger le serveur web

  handlers:
    - name: Recharger le serveur web
      service:
        name: nginx
        state: reloaded
Ajout de serial: 1 : Permet à Ansible d'exécuter le playbook nœud par nœud (rolling update). Si une instance est en cours de mise à jour ou de redémarrage, la seconde continue de servir le trafic web.

3. Analyse du plan d'exécution (terraform plan)
L'exécution de la commande de planification :

Bash
docker compose run --rm terraform -chdir=/terraform/aws plan -out=tfplan
A permis de valider le comportement attendu sur l'infrastructure AWS :

Type d'action : Mise à jour sur place (update in-place) de l'instance aws_instance.web[0] (i-0664b1dd13cfbf639) et création de la nouvelle instance selon le paramètre nb_web = 2.

Impact Réseau : L'attribut instance_type passe de t3.micro à t3.small. Ce changement nécessitant un arrêt/redémarrage de l'instance Cloud, l'adresse IP publique dynamique est libérée puis réattribuée ((known after apply)).

Déterminisme : Le plan a été sauvegardé sous tfplan afin de garantir une exécution stricte et conforme lors de l'étape de déploiement.

4. Application des changements (terraform apply)
L'application du plan sauvegardé :

Bash
docker compose run --rm terraform -chdir=/terraform/aws apply tfplan
Résultats constatés :

Plaintext
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.

Outputs:

ip_publique = "34.200.222.226"
Durée d'exécution : Modification effectuée en 35 secondes (Modifications complete after 35s).

Résultat d'état : Apply complete! Resources: 0 added, 1 changed, 0 destroyed.

Mise à jour des sorties : L'adresse IP publique actualisée est 34.200.222.226 (remplaçant l'ancienne IP 3.83.21.76).

5. Continuité de service & Rejeu Ansible
5.1 Constat initial
Une tentative de connexion immédiate via curl -I [http://34.200.222.226](http://34.200.222.226) n'a pas abouti immédiatement (^C). En effet, suite au redémarrage de l'instance et à l'attribution de la nouvelle adresse IP publique, les règles de sécurité, la clé d'hôte SSH et la configuration de NGINX nécessitent l'actualisation de l'inventaire et le rejeu de la configuration applicative.

5.2 Procédure de finalisation
Régénération de l'inventaire dynamique : Mise à jour automatique du fichier d'inventaire d'Ansible avec les nouvelles adresses IP (34.200.222.226 ainsi que la seconde IP issue de nb_web = 2).

Exécution du playbook d'alignement :

Bash
docker compose run --rm ansible ansible-playbook -i ansible/genere.ini ansible/site.yml
Grâce à la directive serial: 1, l'application des configurations et le rechargement de NGINX s'effectuent de manière séquentielle sur chaque instance, garantissant le maintien de l'accès au service pendant les phases de rechargement.