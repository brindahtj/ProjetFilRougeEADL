# Exercice 3 — Réseau privé sécurisé & tunnel VPN opérationnel

**Projet fil rouge : UrbanHub — Groupe [X]**
**Module BC04 · Jour 3 PM · Exercice 3 (noté 40 pts)**
**Mode utilisé : Mode B (LocalStack VPC) + simulation WireGuard sur VPS unique**

---

## Contexte et environnement

Faute d'accès à un compte AWS facturé, ce rendu a été réalisé intégralement en
environnement local, sans dépendance à un cloud provider payant :

- **VPC / Subnets / Security Groups** : simulés via **LocalStack** (édition Pro,
  licence freemium étudiante), piloté par l'AWS CLI standard avec
  `--endpoint-url=http://localhost:4566`. Les commandes utilisées sont
  rigoureusement identiques à celles qui seraient exécutées contre un vrai compte
  AWS — seul le endpoint change, garantissant la transférabilité des compétences.
- **VPN Site-to-Site** : simulé via **WireGuard** (alternative à strongSwan,
  toutes deux autorisées par l'énoncé), déployé dans deux conteneurs Docker
  distincts sur le même VPS, représentant chacun un "site" séparé.

---

## Étape 1 — VPC + 2 sous-réseaux

### Architecture réseau

| Élément | Valeur | Rôle |
|---|---|---|
| VPC | `10.0.0.0/16` (`vpc-65ab44483d9c28192`) | Réseau privé du projet UrbanHub |
| Subnet applicatif | `10.0.10.0/24` (`sc-subnet-app`) | Héberge sc-api, sc-worker |
| Subnet management | `10.0.99.0/24` (`sc-subnet-mgmt`) | Héberge le bastion SSH |

### Commandes clés

```bash
# Création du VPC
awslocal-docker ec2 create-vpc --cidr-block 10.0.0.0/16 --region eu-west-3

# Création des subnets
awslocal-docker ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.10.0/24 \
  --availability-zone eu-west-3a
awslocal-docker ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.99.0/24 \
  --availability-zone eu-west-3a
```

### Preuve — `describe-subnets`

```
------------------------------------------------------------
|                      DescribeSubnets                     |
+------------+----------------+----------------------------+
|     AZ     |     CIDR       |            ID              |
+------------+----------------+----------------------------+
|  eu-west-3a|  10.0.10.0/24  |  subnet-82eab75a11793aec1  |
+------------+----------------+----------------------------+
||  Name           |  sc-subnet-app                       ||
+------------+----------------+----------------------------+
|  eu-west-3a|  10.0.99.0/24  |  subnet-d9805786b0f047be5  |
+------------+----------------+----------------------------+
||  Name          |  sc-subnet-mgmt                       ||
```


---

## Étape 2 — NACL & Security Groups strictes

### Adaptation du besoin métier

> L'énoncé de référence mentionne le port MQTT 1883 comme protocole IoT type.
> Notre groupe ayant fait le choix architectural de **RabbitMQ (AMQP)** plutôt
> que MQTT (cf. justification du choix technique, section stockage/broker du
> projet), les règles de sécurité ont été adaptées en conséquence — la logique
> de moindre privilège reste identique, seul le port change.

### Security Groups créés

| Security Group | Port | Source autorisée | Justification |
|---|---|---|---|
| `sc-sg-app` | 5672 (AMQP) | `10.0.0.0/16` (tout le VPC) | Communication broker intra-VPC uniquement |
| `sc-sg-app` | 15672 (management RabbitMQ) | `10.0.99.0/24` (subnet mgmt uniquement) | Interface d'administration accessible uniquement depuis le management |
| `sc-sg-bastion` | 22 (SSH) | `10.0.99.0/24` (subnet mgmt uniquement) | Accès SSH restreint au bastion, pas d'exposition publique |

### Commandes clés

```bash
awslocal-docker ec2 authorize-security-group-ingress \
  --group-id $SG_APP --protocol tcp --port 5672 --cidr 10.0.0.0/16

awslocal-docker ec2 authorize-security-group-ingress \
  --group-id $SG_APP --protocol tcp --port 15672 --cidr 10.0.99.0/24

awslocal-docker ec2 authorize-security-group-ingress \
  --group-id $SG_BASTION --protocol tcp --port 22 --cidr 10.0.99.0/24
```

### Preuve — `describe-security-groups`

```json
[
    {
        "Name": "sc-sg-app",
        "Rules": [
            {"FromPort": 5672,  "ToPort": 5672,  "IpRanges": [{"CidrIp": "10.0.0.0/16"}]},
            {"FromPort": 15672, "ToPort": 15672, "IpRanges": [{"CidrIp": "10.0.99.0/24"}]}
        ]
    },
    {
        "Name": "sc-sg-bastion",
        "Rules": [
            {"FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "10.0.99.0/24"}]}
        ]
    }
]
```


### Principe de sécurité appliqué (moindre privilège)

Aucune règle n'ouvre un port vers `0.0.0.0/0` (Internet). Tous les accès sont
restreints à des plages CIDR internes au VPC, cohérent avec la matrice d'accès
étudiée en chapitre 2.4 du cours (principe : chaque composant n'a accès qu'à ce
qui lui est strictement nécessaire).

---

## Étape 3 — VPN Site-to-Site (WireGuard)

### Choix technique : WireGuard plutôt que strongSwan

L'énoncé autorise explicitement les deux options. Notre groupe a retenu
**WireGuard** pour sa simplicité de configuration et sa fiabilité de mise en
œuvre dans le temps imparti. Le module WireGuard était déjà actif sur le noyau
du VPS pédagogique, facilitant grandement le déploiement sans compilation ni
dépendance supplémentaire.

Nous notons que WireGuard n'utilise pas le protocole IPSec (contrairement à
AWS Site-to-Site VPN réel, qui s'appuie sur `ipsec.1`), mais reproduit
fonctionnellement l'objectif pédagogique demandé : un tunnel chiffré
point-à-point avec validation par ping et SSH.

### Topologie simulée

En l'absence de deux VPS physiquement séparés, les deux extrémités du tunnel
ont été simulées via **deux conteneurs Docker distincts** sur la même machine,
chacun représentant un "site" indépendant, connectés via un réseau Docker dédié
(`vpn-test-net`) puis reliés par un tunnel WireGuard chiffré par-dessus :

```
[site-a : 10.99.0.1/24]  <== tunnel WireGuard chiffré (UDP 51820) ==>  [site-b : 10.99.0.2/24]
   IP réseau Docker : 172.20.0.2                                          IP réseau Docker : 172.20.0.3
```

### Configuration des pairs (extrait)

**site-a** (`/config/wg_confs/wg0.conf`) :
```ini
[Interface]
PrivateKey = <clé privée site-a>
Address = 10.99.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <clé publique site-b>
Endpoint = 172.20.0.3:51820
AllowedIPs = 10.99.0.2/32
PersistentKeepalive = 25
```

**site-b** (`/config/wg_confs/wg0.conf`) : configuration symétrique, adresse
`10.99.0.2/24`, endpoint vers `172.20.0.2:51820`.

### Preuve — Activation du tunnel

```
**** Activating tunnel /config/wg_confs/wg0.conf ****
[#] ip link add dev wg0 type wireguard
[#] wg addconf wg0 /dev/fd/63
[#] ip -4 address add 10.99.0.1/24 dev wg0
[#] ip link set mtu 1420 up dev wg0
**** All tunnels are now active ****
```

### Test 1 — Connectivité (ping) à travers le tunnel

```
$ docker exec site-a ping -c 4 10.99.0.2
PING 10.99.0.2 (10.99.0.2) 56(84) bytes of data.
64 bytes from 10.99.0.2: icmp_seq=1 ttl=64 time=1.10 ms
64 bytes from 10.99.0.2: icmp_seq=2 ttl=64 time=0.820 ms
64 bytes from 10.99.0.2: icmp_seq=3 ttl=64 time=4.58 ms
64 bytes from 10.99.0.2: icmp_seq=4 ttl=64 time=0.286 ms
--- 10.99.0.2 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3004ms
```

Résultat symétrique validé dans l'autre sens (site-b → site-a), **0% de perte
dans les deux sens**.

### Test 2 — État du tunnel (`wg show`)

```
interface: wg0
  public key: PZMcqtAuJo8dOdEjzH829bWyiyR1ooDZyxtXI+9QZjc=
  listening port: 51820

peer: kU24ePYxzR2ocranIfdsjIKdVU5YOAgydeHL/dLDoxc=
  endpoint: 172.20.0.3:51820
  allowed ips: 10.99.0.2/32
  latest handshake: 1 second ago
  transfer: 1.75 KiB received, 1.70 KiB sent
  persistent keepalive: every 25 seconds
```

Le handshake WireGuard confirmé récemment (`1 second ago`) atteste que le
chiffrement est actif et le tunnel opérationnel, pas seulement configuré.

### Test 3 — Connexion SSH à travers le tunnel

```
$ docker exec -it site-a ssh root@10.99.0.2
The authenticity of host '10.99.0.2 (10.99.0.2)' can't be established.
ED25519 key fingerprint is: SHA256:z30B+raw7DOt3i6iYFNKmMukRUd/kQOMc02r4mxDgzg
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
root@10.99.0.2's password:
Welcome to Alpine!
```

📷 *[Capture d'écran à insérer ici : session SSH complète + `hostname` +
`ip addr show wg0` pour prouver que la connexion transite bien par
l'interface wg0]*

**Validation** : la connexion SSH aboutit sur l'adresse `10.99.0.2`, qui
n'existe que sur l'interface virtuelle `wg0` (pas une IP réseau Docker
classique) — preuve que le trafic SSH transite bien à travers le tunnel
chiffré, et non par un accès direct non sécurisé.

---

## Étape 4 — Tests d'attaque & synthèse sécurité

### Test 1 — Scan de la surface d'attaque exposée

**Contrainte technique rencontrée** : `nmap` (mode `-sV`, scan SYN) échoue
systématiquement sur ce VPS, y compris avec `--cap-add=NET_RAW --cap-add=NET_ADMIN` :

```
Couldn't open a raw socket. Error: (1) Operation not permitted
dnet: failed to open device lo
Couldn't open a raw socket or eth handle.
QUITTING!
```

Cause : le VPS pédagogique fonctionne en **Docker rootless**, qui refuse
l'attribution de capacités réseau bas niveau même explicitement demandées.
C'est une restriction volontaire de l'environnement partagé, pas un incident.

**Contournement retenu** : scan TCP simple via `/dev/tcp` (bash), qui teste
l'ouverture de chaque port sans nécessiter de privilèges système :

```bash
for port in 22 1883 5672 8085 8086 8087 9005 9006 15672; do
  timeout 1 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null \
    && echo "Port $port : OUVERT" || echo "Port $port : fermé"
done
```

**Résultat** :

```
Port 22 : OUVERT
Port 1883 : fermé
Port 5672 : fermé
Port 8085 : OUVERT
Port 8086 : OUVERT
Port 8087 : OUVERT
Port 9005 : OUVERT
Port 9006 : OUVERT
Port 15672 : fermé
```

**Analyse** :

| Port | Service | Statut | Commentaire |
|---|---|---|---|
| 22 | SSH bastion | Ouvert | Attendu — accès administrateur |
| 1883 | MQTT | Fermé | Normal — non utilisé, RabbitMQ (AMQP) retenu à la place |
| 5672 | AMQP interne | Fermé côté hôte | Accès prévu uniquement en interne réseau Docker (`my-network`), pas exposé publiquement |
| 8085 | API FastAPI | Ouvert | Attendu — point d'entrée applicatif |
| 8086 | RabbitMQ management | Ouvert | Interface d'admin — à restreindre en production (voir recommandation) |
| 8087 | RabbitMQ AMQP (mappé) | Ouvert | Broker exposé pour les tests locaux |
| 9005 | MinIO API (S3) | Ouvert | Nécessaire pour les scripts d'ingestion |
| 9006 | MinIO Console | Ouvert | Interface d'admin — à restreindre en production |
| 15672 | RabbitMQ mgmt natif | Fermé | Port non mappé sur l'hôte (mappé sur 8086 à la place) |

**Constat sécurité important** : ce scan révèle un écart entre la théorie
(Security Groups définis en Mode B/LocalStack, cf. étape 2) et la pratique
Docker locale — les ports Docker publiés via `-p` sont accessibles
**indépendamment des règles Security Group**, car ces dernières ne sont
qu'une simulation API sans effet sur le trafic réseau réel de l'hôte. En
environnement AWS réel, les Security Groups filtreraient effectivement ce
trafic au niveau de l'hyperviseur, avant d'atteindre l'instance.

**Recommandation retenue** : en production réelle, les interfaces
d'administration (RabbitMQ management port 8086/15672, MinIO console port
9006) ne devraient jamais être exposées publiquement — seulement accessibles
depuis le subnet management via VPN, à l'image du modèle appliqué à l'étape 2.

---

### Test 2 — Détection et blocage d'intrusion (fail2ban)

**Objectif** : simuler une attaque par force brute SSH sur le bastion
(`site-b`, à travers le tunnel WireGuard) et démontrer la détection +
blocage automatique.

**Configuration retenue** (`/etc/fail2ban/jail.local`) :

```ini
[DEFAULT]
banaction = iptables-multiport
backend = polling

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 1d
bantime = 600

[sshd-ddos]
enabled = false
```

Point technique : le jail `sshd-ddos`, activé par défaut dans la config
système Alpine, a dû être explicitement désactivé (`enabled = false`) car il
recherchait un fichier de log inexistant et empêchait le démarrage du service.
`backend = polling` a également été nécessaire pour la compatibilité avec le
système de fichiers du conteneur.

**Simulation de l'attaque** — 4 tentatives de connexion SSH avec mot de passe
erroné :

```bash
for i in {1..4}; do
  docker exec site-a ssh -o StrictHostKeyChecking=no root@10.99.0.2 "echo test" <<< "mauvais_mdp_$i"
  sleep 1
done
```

**Résultat observé** :

```
Permission denied, please try again.
Permission denied, please try again.
root@10.99.0.2: Permission denied (publickey,password,keyboard-interactive).
Permission denied, please try again.
Permission denied, please try again.
root@10.99.0.2: Permission denied (publickey,password,keyboard-interactive).
ssh: connect to host 10.99.0.2 port 22: Connection refused
ssh: connect to host 10.99.0.2 port 22: Connection refused
```

**Analyse** : les deux premières tentatives échouent normalement (mauvais mot
de passe, comportement SSH standard). À partir de la 3ᵉ tentative, la
connexion est **activement refusée** (`Connection refused`) au lieu d'un
simple refus d'authentification — preuve que fail2ban a détecté le seuil de
`maxretry = 3` et déclenché le blocage réseau via `iptables` avant même que
la tentative de connexion n'atteigne le service SSH.

**Confirmation via `fail2ban-client status`** :

```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 0
|  |- Total failed:     0
|  `- File list:        /var/log/auth.log
`- Actions
   |- Currently banned: 1
   |- Total banned:     1
   `- Banned IP list:   10.99.0.1
```

L'IP `10.99.0.1` (adresse WireGuard de site-a, l'attaquant simulé) est
confirmée bannie pour une durée de `bantime = 600` secondes (10 minutes).

**Conclusion** : le mécanisme de détection et blocage d'intrusion fonctionne
de bout en bout — détection du seuil d'échecs, bannissement automatique par
IP, et effet réel constaté (connexions suivantes rejetées).

---

### Résumé des principes de sécurité appliqués

| Principe | Mise en œuvre |
|---|---|
| Moindre privilège | Aucun port ouvert vers 0.0.0.0/0 ; toutes les règles restreintes à des CIDR internes |
| Segmentation réseau | Subnet applicatif et subnet management séparés |
| Chiffrement en transit | Tunnel WireGuard (ChaCha20-Poly1305) pour toute communication inter-sites |
| Accès administratif isolé | SSH restreint au subnet mgmt ; interface RabbitMQ management restreinte au subnet mgmt |
| Détection & blocage d'intrusion | fail2ban actif sur le bastion SSH — blocage automatique après 3 échecs (voir étape 4) |
| Défense en profondeur | Constat documenté : Security Groups (couche AWS/LocalStack) + fail2ban (couche applicative) sont complémentaires, la seconde compensant les limites de la première en environnement de simulation Docker |

---

## Annexe — Commandes de récupération de session

En cas de déconnexion SSH (les variables bash ne persistent pas), les
identifiants de ressources LocalStack peuvent être retrouvés via :

```bash
VPC_ID=$(awslocal-docker ec2 describe-vpcs --filters "Name=cidr,Values=10.0.0.0/16" \
  --query 'Vpcs[0].VpcId' --output text)
SG_APP=$(awslocal-docker ec2 describe-security-groups \
  --filters "Name=group-name,Values=sc-sg-app" --query 'SecurityGroups[0].GroupId' --output text)
SG_BASTION=$(awslocal-docker ec2 describe-security-groups \
  --filters "Name=group-name,Values=sc-sg-bastion" --query 'SecurityGroups[0].GroupId' --output text)
```

⚠️ **Limite connue** : LocalStack ne persiste pas les données entre redémarrages
du conteneur (`persistence: disabled` en édition freemium). Un redémarrage du
conteneur `localstack-test` nécessite de recréer l'ensemble des ressources
VPC/subnets/SG.