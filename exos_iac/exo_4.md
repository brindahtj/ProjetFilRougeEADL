# Rapport · Exercice 4 — Monter en charge sans interrompre le service
 
**Module :** BC04-FM02 · Infrastructure as Code
**Projet :** UrbanHub (Smart City IoT)
**Mode :** Mode C · AWS Academy Learner Lab (`us-east-1`)
**Compétence évaluée :** C22 · Automatiser la configuration et la gestion des ressources cloud
 
---
 
## 1. Objectif et contexte
 
Contrairement aux exercices 1 à 3 (Mode A, Docker local), cet exercice a été réalisé en **Mode C** sur un vrai compte AWS Academy, pour observer le comportement réel d'un remplacement d'instance EC2 — un scénario que le Mode A (conteneurs Docker) ne peut pas reproduire fidèlement (pas de notion de type d'instance ni de redémarrage matériel).
 
Le scénario du support : agrandir le serveur `t3.micro` en `t3.small` sans interrompre le service, en maîtrisant la lecture du plan et en anticipant un éventuel remplacement.
 
## 2. Infrastructure de départ
 
Le fichier `terraform/aws/main.tf` provisionne une instance EC2 Ubuntu avec clé SSH injectée et security group dédié (SSH restreint à l'IP du poste, HTTP ouvert) :
 
```hcl
resource "aws_instance" "web" {
  count                  = var.nb_web
  ami                    = data.aws_ami.ubuntu.id
  instance_type           = var.instance_type
  key_name                = aws_key_pair.formateur.key_name
  vpc_security_group_ids  = [aws_security_group.web.id]
 
  tags = {
    Name = "urbanhub-web-${count.index + 1}"
    Role = "web"
  }
 
  lifecycle {
    create_before_destroy = true
  }
}
```
 
Instance initiale déployée en `t3.micro`, connectivité SSH vérifiée (`ubuntu@<ip_publique>`) et testée avec un playbook Ansible simple (`echo.yml`), confirmant `ok=3, changed=1, failed=0`.
 
## 3. Étape 1 — Modifier la configuration
 
Changement de la variable `instance_type` :
```bash
docker compose run --rm -e TF_VAR_instance_type=t3.small terraform -chdir=/terraform/aws plan -out=tfplan
```
 
## 4. Étape 2 — Lire le plan et gérer les erreurs
 
### 4.1 Premier constat : pas de remplacement automatique
 
Le plan a révélé un résultat différent de celui attendu par défaut d'après le support :
 
```
~ update in-place
 
  # aws_instance.web[0] will be updated in-place
  ~ instance_type = "t3.micro" -> "t3.small"
  ~ public_ip     = "54.167.99.91" -> (known after apply)
 
Plan: 0 to add, 1 to change, 0 to destroy.
```
 
**Analyse.** Passer de `t3.micro` à `t3.small` reste dans la **même famille d'instance** (`t3`), une opération que l'API EC2 supporte via une simple modification d'attribut (stop/start interne géré par AWS), sans nécessiter que Terraform détruise et recrée la ressource. Seuls `public_ip` et `public_dns` changent, car AWS attribue une nouvelle IP publique dynamique à chaque redémarrage (pas d'Elastic IP configurée dans ce TP).
 
**Enseignement retenu.** Le `-/+` évoqué par le support ne se produit pas pour tout changement d'`instance_type` — cela dépend de la nature du changement (même famille vs changement de famille/AMI/subnet, qui eux forcent un vrai remplacement).
 
### 4.2 Démonstration forcée du remplacement avec `create_before_destroy`
 
Pour observer concrètement le mécanisme demandé par l'exercice, le remplacement a été **forcé explicitement** avec l'option `-replace`, qui indique à Terraform de traiter la ressource comme si elle devait être recréée, indépendamment de la nature du changement :
 
```bash
docker compose run --rm terraform -chdir=/terraform/aws plan -replace="aws_instance.web[0]" -out=tfplan
```
 
Résultat :
```
+/- create replacement and then destroy
 
  # aws_instance.web[0] will be replaced, as requested
+/- resource "aws_instance" "web" {
      ~ id = "i-03807fed08d24f1de" -> (known after apply)
      ...
    }
 
Plan: 1 to add, 0 to change, 1 to destroy.
```
 
Le symbole **`+/-`** (et non `-/+`) confirme que `create_before_destroy` inverse bien l'ordre d'exécution par rapport au comportement par défaut de Terraform.
 
### 4.3 Apply — preuve de l'ordre d'exécution
 
```bash
docker compose run --rm terraform -chdir=/terraform/aws apply tfplan
```
 
Sortie observée :
```
aws_instance.web[0]: Creating...
aws_instance.web[0]: Creation complete after 15s [id=i-05d5c844fb3f68607]
 
aws_instance.web[0] (deposed object d5fb5fc1): Destroying... [id=i-03807fed08d24f1de]
aws_instance.web[0]: Still destroying... [id=i-03807fed08d24f1de, 00m10s elapsed]
aws_instance.web[0]: Still destroying... [id=i-03807fed08d24f1de, 00m20s elapsed]
aws_instance.web[0]: Still destroying... [id=i-03807fed08d24f1de, 00m30s elapsed]
aws_instance.web[0]: Destruction complete after 31s
 
Apply complete! Resources: 1 added, 0 changed, 1 destroyed.
 
Outputs:
ip_publique = ["3.88.51.22"]
```
 
**Preuve du zéro-interruption de disponibilité.** La nouvelle instance (`i-05d5c844fb3f68607`) a atteint l'état `Creation complete` en 15 secondes — donc pleinement opérationnelle et joignable — **avant même que la destruction de l'ancienne instance (`i-03807fed08d24f1de`) ne commence**. Les deux instances ont coexisté pendant les 31 secondes qu'a duré la destruction de l'ancienne, garantissant qu'à aucun moment le service web n'a été totalement absent.
 
### 4.4 Erreur rencontrée et gérée
 
```bash
docker compose run --rm terraform -chdir=/terraform/aws output -raw ip_publique
```
```
Error: Unsupported value for raw output
The -raw option only supports strings, numbers, and boolean values,
but output value "ip_publique" is tuple.
```
 
**Cause.** L'output `ip_publique` est défini comme une liste (`aws_instance.web[*].public_ip`), donc de type `tuple` — incompatible avec `-raw`, réservé aux types simples.
 
**Correctif.**
```bash
docker compose run --rm terraform -chdir=/terraform/aws output ip_publique
# ou pour un usage scripte :
docker compose run --rm terraform -chdir=/terraform/aws output -json ip_publique
```
 
## 5. Étape 3 — Mesures prises pour minimiser l'interruption et les erreurs
 
| Mesure | Effet |
|---|---|
| `lifecycle { create_before_destroy = true }` | Garantit qu'une nouvelle instance est pleinement créée avant toute destruction de l'ancienne |
| Lecture systématique du `plan` avant `apply` | A permis d'identifier que le changement `t3.micro → t3.small` ne déclenche pas de remplacement par défaut, évitant une intervention inutile |
| Usage de `-replace` pour une démonstration contrôlée | A permis d'observer le comportement de remplacement dans un cadre maîtrisé plutôt que de le subir sur un changement de production réel |
| `key_name` et `vpc_security_group_ids` inchangés lors du remplacement | Évite tout conflit de nommage AWS (clé SSH et security group ne sont pas recréés, seule l'instance l'est) |
| Vérification de connectivité SSH après chaque changement d'IP | Confirme que le service reste joignable malgré le changement d'adresse publique |
 
## 6. Nettoyage — arrêt de la consommation de crédits AWS Academy
 
```bash
docker compose run --rm terraform -chdir=/terraform/aws destroy -auto-approve
```
 
Point de vigilance retenu : contrairement au Mode A (Docker, gratuit et local), toute ressource laissée active en Mode C consomme réellement les crédits limités du Learner Lab — la destruction en fin de séance est systématique, jamais optionnelle.
 

 