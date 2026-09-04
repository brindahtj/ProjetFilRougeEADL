# Exercice 4 — Automatiser les mises à jour sur un parc de VMs

**Projet fil rouge : UrbanHub — Groupe [X]**
**Module BC04 · Jour 4 PM · Exercice 4 (noté 40 pts)**
**Mode utilisé : Mode A (Ansible + conteneurs Docker locaux)**

---

## Contexte et environnement

Sans compte AWS facturé, ce rendu utilise le parc de conteneurs Docker déjà
déployé pour l'exercice 3 (`site-a`, `site-b` — nœuds WireGuard du tunnel VPN
simulé) comme cible d'automatisation, cohérent avec l'esprit Mode A de
l'énoncé.

- **Outil retenu** : Ansible, installé en environnement virtuel Python
  (`ansible-venv`) sur le VPS hôte, communiquant avec les conteneurs via le
  plugin de connexion `ansible_connection=docker`.
- **Cibles** : `site-a` et `site-b`, systèmes Alpine Linux (gestionnaire de
  paquets `apk`).

---

## Étape 1 — Choix de l'outil

### Ansible retenu, plutôt qu'Ansible AWX, Puppet, Chef ou AWS SSM

| Outil | Écarté / retenu | Justification |
|---|---|---|
| **Ansible (CLI)** | ✅ Retenu | Sans agent (agentless), utilise SSH ou une connexion directe (ici Docker), léger à déployer, cohérent avec le reste du cursus (chapitre 4.2 du cours) |
| Ansible AWX | ❌ Écarté | Nécessite une interface web + base de données dédiée — disproportionné pour un parc de 2 nœuds de test |
| Puppet / Chef | ❌ Écartés | Architecture agent/master à déployer, complexité supplémentaire injustifiée pour ce périmètre |
| AWS SSM Patch Manager | ❌ Écarté | Nécessite des instances EC2 réelles et un compte AWS facturé, non disponible dans notre contexte (cf. étape 1 exo 1) |

### Inventaire (`hosts.ini`)

```ini
[mes_conteneurs]
site-a ansible_connection=docker
site-b ansible_connection=docker
```

### Installation de l'environnement Ansible

```bash
python3 -m venv ~/ansible-venv
source ~/ansible-venv/bin/activate
pip install ansible
```

Python 3 a également dû être installé dans les conteneurs cibles (absent des
images de base) :
```bash
docker exec site-a apk add --no-cache python3
docker exec site-b apk add --no-cache python3
```

### Validation de la connectivité

```bash
ansible mes_conteneurs -i hosts.ini -m ping
```

```
site-a | SUCCESS => {"ping": "pong"}
site-b | SUCCESS => {"ping": "pong"}
```

---

## Étape 2 — Playbook inventaire + vérification des patches disponibles

### `check-updates.yml`

```yaml
---
- name: Vérification des mises à jour disponibles
  hosts: mes_conteneurs
  gather_facts: yes
  tasks:
    - name: Rafraîchir l'index des paquets
      command: apk update
      changed_when: "'Fetched' in apk_update_result.stdout"
      register: apk_update_result

    - name: Lister les paquets à mettre à jour (Alpine)
      command: apk list --upgradable
      register: paquets_maj
      changed_when: false

    - name: Afficher le résultat
      debug:
        var: paquets_maj.stdout_lines
```

### Résultat

```bash
ansible-playbook -i hosts.ini check-updates.yml
```

8 paquets obsolètes détectés sur les deux nœuds (identiques, car même image
de base) :

```
apk-tools-3.0.8-r0        [upgradable from: apk-tools-3.0.7-r0]
curl-8.22.0-r0             [upgradable from: curl-8.21.0-r0]
jq-1.8.2-r0                 [upgradable from: jq-1.8.1-r0]
libapk-3.0.8-r0             [upgradable from: libapk-3.0.7-r0]
libcrypto3-3.5.8-r0        [upgradable from: libcrypto3-3.5.7-r0]
libcurl-8.22.0-r0           [upgradable from: libcurl-8.21.0-r0]
libssl3-3.5.8-r0            [upgradable from: libssl3-3.5.7-r0]
pcre2-10.48-r0               [upgradable from: pcre2-10.47-r1]
```

`PLAY RECAP` : `ok=4, failed=0` sur les deux nœuds — inventaire et détection
des patches disponibles validés.

---

## Étape 3 — Test Canary sur `site-a`

### Principe

Avant de propager les 8 mises à jour à l'ensemble du parc, un test **canary**
est exécuté sur un seul nœud (`site-a`) afin de détecter toute régression
avant impact généralisé.

### `canary-patch.yml`

```yaml
---
- name: Patch canary - site-a uniquement
  hosts: site-a
  gather_facts: yes
  tasks:
    - name: Rafraîchir l'index des paquets
      command: apk update

    - name: Appliquer les mises à jour disponibles
      command: apk upgrade
      register: resultat_upgrade

    - name: Afficher le résultat de l'upgrade
      debug:
        var: resultat_upgrade.stdout_lines

    - name: Vérifier que l'interface WireGuard est toujours active après patch
      command: ip link show wg0
      register: wg_check
      failed_when: wg_check.rc != 0

    - name: Afficher l'état de l'interface WireGuard
      debug:
        var: wg_check.stdout_lines

    - name: Vérifier la connectivité tunnel (ping vers site-b)
      command: ping -c 2 10.99.0.2
      register: ping_check
      failed_when: ping_check.rc != 0

    - name: Rapport canary final
      debug:
        msg: "Canary OK sur site-a — WireGuard actif et tunnel fonctionnel après patch."
```

### Choix du contrôle de santé post-patch

Le contrôle vérifie l'**application réelle du nœud** (interface WireGuard +
connectivité du tunnel VPN), plutôt qu'un service générique. Un premier essai
utilisant `pgrep sshd` a été écarté après investigation : `site-a` n'héberge
qu'un client SSH (`openssh-client`), jamais de serveur SSH — ce contrôle
n'était pas pertinent pour ce nœud (voir incident documenté ci-dessous).

### Incident rencontré et résolu pendant la mise au point

Lors d'un premier essai de contrôle santé (test `pgrep sshd`), le patch a
semblé faire disparaître le service SSH sur `site-a`. Investigation :

```bash
docker exec site-a which sshd
docker exec site-a apk info | grep -i ssh
```

```
openssh-client-common
openssh-client-default
openssh-keygen
```

**Diagnostic** : `site-a` n'a jamais eu de serveur SSH installé (rôle de
client uniquement dans la topologie VPN de l'exercice 3) — le test de santé
initial ciblait le mauvais composant, pas une régression réelle causée par
le patch. Le contrôle a été corrigé pour vérifier l'élément réellement
pertinent pour ce nœud : l'interface WireGuard et la connectivité tunnel.

**Leçon retenue** : un test canary doit vérifier la santé de **l'application
réelle du nœud testé**, pas un service générique supposé présent par
défaut — erreur classique en environnement hétérogène (chaque nœud du parc
n'a pas nécessairement les mêmes services actifs).

### Résultat final du canary

```bash
ansible-playbook -i hosts.ini canary-patch.yml
```

```
TASK [Vérifier que l'interface WireGuard est toujours active après patch]
changed: [site-a]

TASK [Afficher l'état de l'interface WireGuard]
ok: [site-a] => {
    "wg_check.stdout_lines": [
        "4: wg0: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420 qdisc noqueue state UNKNOWN...",
        "    link/none "
    ]
}

TASK [Vérifier la connectivité tunnel (ping vers site-b)]
changed: [site-a]

TASK [Rapport canary final]
ok: [site-a] => {
    "msg": "Canary OK sur site-a — WireGuard actif et tunnel fonctionnel après patch."
}

PLAY RECAP
site-a : ok=8    changed=4    unreachable=0    failed=0    skipped=0
```

**Verdict** : canary validé — 6 paquets mis à jour (dont `libcrypto3` et
`libssl3`, sensibles), interface WireGuard toujours `UP`, tunnel toujours
fonctionnel. Autorisation de rollout complet.

---

## Étape 4 — Rollout complet & notifications

### `rollout-patch-with-notif.yml`

```yaml
---
- name: Rollout complet avec notifications
  hosts: mes_conteneurs
  gather_facts: yes
  tasks:
    - name: Rafraîchir l'index des paquets
      command: apk update

    - name: Appliquer les mises à jour
      command: apk upgrade
      register: resultat_upgrade
      ignore_errors: yes

    - name: Notification succès
      ansible.builtin.lineinfile:
        path: "{{ lookup('env', 'HOME') }}/amis/notifications-patch.log"
        line: "[{{ ansible_date_time.iso8601 }}] SUCCESS - {{ inventory_hostname }} - patché avec succès"
        create: yes
      delegate_to: localhost
      when: resultat_upgrade is succeeded

    - name: Notification échec
      ansible.builtin.lineinfile:
        path: "{{ lookup('env', 'HOME') }}/amis/notifications-patch.log"
        line: "[{{ ansible_date_time.iso8601 }}] FAILURE - {{ inventory_hostname }} - échec du patch, voir logs"
        create: yes
      delegate_to: localhost
      when: resultat_upgrade is failed
```

### Choix technique — simulation SNS

En l'absence de compte AWS (SNS réel indisponible), les notifications sont
simulées via un **fichier de log centralisé** sur le contrôleur Ansible
(`~/amis/notifications-patch.log`), utilisant `delegate_to: localhost` pour
écrire depuis la machine de contrôle plutôt que depuis les nœuds cibles —
reproduisant le principe d'un point de collecte centralisé, équivalent
fonctionnel d'un topic SNS.

**Point de vigilance rencontré** : la première tentative avec la syntaxe
`local_action` (dépréciée depuis Ansible 2.23) a échoué avec une erreur de
permissions car le chemin `/home/brendah` n'existe pas sur ce VPS (le vrai
répertoire personnel est `/opt/brendah`). Correction appliquée :
`{{ lookup('env', 'HOME') }}` résout dynamiquement le bon chemin, rendant le
playbook portable indépendamment de la structure de répertoires de l'hôte.

### Résultat

```bash
ansible-playbook -i hosts.ini rollout-patch-with-notif.yml
```

```
PLAY RECAP
site-a : ok=4    changed=3    unreachable=0    failed=0    skipped=1
site-b : ok=4    changed=3    unreachable=0    failed=0    skipped=1
```

Contenu de `notifications-patch.log` :
```
[2026-09-03T14:35:xx] SUCCESS - site-a - patché avec succès
[2026-09-03T14:35:xx] SUCCESS - site-b - patché avec succès
```

Rollout complet validé sur l'ensemble du parc (2/2 nœuds), notifications
tracées avec horodatage.

---

## Runbook — Procédure de patch management UrbanHub

### Objectif

Documenter la procédure standard de mise à jour du parc UrbanHub, ainsi que
la conduite à tenir en cas d'échec, pour permettre à tout membre du groupe
(ou tout administrateur futur) d'exécuter ou de dépanner ce processus sans
connaissance préalable de l'historique de mise au point.

### Procédure standard (cas nominal)

| Étape | Commande | Objectif |
|---|---|---|
| 1. Audit | `ansible-playbook -i hosts.ini check-updates.yml` | Lister les paquets obsolètes sur l'ensemble du parc |
| 2. Canary | `ansible-playbook -i hosts.ini canary-patch.yml` | Patcher un seul nœud représentatif, vérifier son application réelle |
| 3. Décision | Revue manuelle du `PLAY RECAP` du canary | `failed=0` → autoriser le rollout ; sinon → procédure d'exception |
| 4. Rollout | `ansible-playbook -i hosts.ini rollout-patch-with-notif.yml` | Propager le patch à tout le parc avec notification |
| 5. Vérification finale | `cat ~/amis/notifications-patch.log` | Confirmer que tous les nœuds sont en statut SUCCESS |

### Procédure d'exception (canary en échec)

Si le `PLAY RECAP` du canary affiche `failed >= 1` :

1. **Ne pas lancer le rollout.** Le patch ne doit jamais être propagé tant que
   le canary n'est pas résolu.
2. **Diagnostiquer la cause** :
   - Consulter la sortie détaillée de la tâche en échec (`ansible-playbook -vvv`)
   - Vérifier manuellement l'état du service concerné sur le nœud canary :
     ```bash
     docker exec <nœud> ps aux
     docker logs <nœud> --tail 50
     ```
   - Distinguer une **vraie régression du patch** (ex. dépendance cassée)
     d'une **erreur de test** (ex. contrôle de santé mal ciblé, comme
     rencontré lors de la mise au point sur `site-a` — voir étape 3)
3. **Si régression confirmée** : rollback du nœud canary
   ```bash
   docker restart <nœud>
   # ou, si les paquets doivent être explicitement rétrogradés :
   docker exec <nœud> apk add --no-cache <paquet>=<version_precedente>
   ```
4. **Si erreur de test** : corriger le playbook canary (contrôle de santé
   adapté au rôle réel du nœud), puis relancer le canary depuis l'étape 2.
5. **Escalade** : si la cause reste indéterminée après investigation, notifier
   les autres membres du groupe avant toute nouvelle tentative — ne pas
   relancer le rollout sans consensus sur la cause racine.

### Fréquence recommandée

Cohérent avec les bonnes pratiques du cours (chapitre 4.4, Maintenance
Window) : exécution hors heures de forte activité, jamais un vendredi ni
juste avant une démonstration/soutenance, avec fenêtre de rollback possible
(conserver les logs `notifications-patch.log` comme trace d'audit).

### Limites connues de cette procédure (environnement de simulation)

- Les notifications sont simulées en fichier local plutôt qu'en SNS réel —
  en production AWS, ce fichier serait remplacé par un appel
  `aws sns publish` vers un topic dédié aux résultats de patch.
- Le rollback de paquets `apk` n'a pas été testé en conditions réelles dans
  cet exercice (paquets déjà à jour après le patch initial) — à valider avant
  mise en production.

---

## Synthèse — Correspondance avec les critères de notation

| Critère (40 pts) | Élément livré |
|---|---|
| Choix de l'outil justifié | Ansible retenu, alternatives écartées avec motif (étape 1) |
| Playbook inventaire + check patches | `check-updates.yml`, 8 paquets détectés |
| Test Canary avant propagation | `canary-patch.yml`, incident réel détecté et corrigé |
| Notifications succès/échec | `rollout-patch-with-notif.yml` + `notifications-patch.log` |
| Runbook procédure d'exception | Section dédiée ci-dessus, basée sur l'incident réel rencontré |