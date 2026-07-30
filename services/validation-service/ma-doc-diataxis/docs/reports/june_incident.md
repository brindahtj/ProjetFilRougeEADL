# Rapport d’incident — UrbanHub

| Information | Valeur |
|---|---|
| **Identifiant** | `INC-2026-06-27-001` |
| **Date de l’incident** | 27 juin 2026 |
| **Heure de détection** | 09 h 12 |
| **Heure de résolution** | 10 h 05 |
| **Durée** | 53 minutes |
| **Statut** | Résolu — faux positif confirmé |
| **Sévérité** | Mineure — aucun impact sur la production |
| **Périmètre** | Dépôt Git UrbanHub — branches `main` et `refacto` |
| **Nature** | Anomalie apparente entre l’état local et l’état distant du dépôt |
| **Responsable de l’investigation** | Équipe de développement UrbanHub |
| **Type de document** | Exemple fictif à vocation pédagogique |

> **Note pédagogique :** Les dates, horaires et éléments de contexte de ce rapport sont fictifs. Ils sont utilisés uniquement pour illustrer la structure et le niveau de traçabilité attendus dans une documentation technique.

---

## BLUF — Bottom Line Up Front

Le **27 juin 2026 à 09 h 12**, lors d’une revue du dépôt UrbanHub, la branche locale `main` semblait contenir des changements associés à la branche `refacto`, notamment l’apparition du dossier `services/` et la réorganisation d’anciens fichiers dans `archive/`.

Cette observation a fait craindre qu’un **push involontaire vers la branche `main`** ait été effectué. Une investigation a été ouverte immédiatement.

Les vérifications réalisées entre **09 h 18 et 09 h 52** ont confirmé que la branche distante `origin/main` était intacte et qu’aucun commit provenant de `refacto` n’avait été intégré à son historique.

À **10 h 05**, l’incident a été requalifié comme **faux positif lié à l’environnement local**. Aucun rollback n’a été nécessaire. Aucun service, aucune donnée et aucun utilisateur n’ont été affectés.

---

# 1. Chronologie détaillée

| Date | Heure | Action / événement | Résultat |
|---|---:|---|---|
| 27/06/2026 | 09 h 12 | Observation de l’arborescence locale de la branche `main` | Le dossier `services/` et le dossier `archive/`, associés à `refacto`, semblent présents |
| 27/06/2026 | 09 h 15 | Signalement de l’anomalie à l’équipe de développement | Hypothèse initiale : push ou fusion involontaire vers `main` |
| 27/06/2026 | 09 h 18 | Exécution de `git status` | Vérification de la branche active et de l’état du répertoire de travail |
| 27/06/2026 | 09 h 21 | Exécution de `git branch --show-current` | Confirmation que la branche locale active est `main` |
| 27/06/2026 | 09 h 24 | Exécution de `git fetch --prune origin` | Mise à jour des références distantes et suppression des références obsolètes |
| 27/06/2026 | 09 h 28 | Consultation de `git log --oneline --decorate --graph` | Aucun commit provenant de `refacto` n’est identifié dans l’historique local de `main` |
| 27/06/2026 | 09 h 33 | Exécution de `git diff main origin/main` | Aucun écart significatif entre la branche locale et la référence distante |
| 27/06/2026 | 09 h 37 | Exécution de `git log origin/main --oneline` | L’historique distant de `main` est confirmé comme intact |
| 27/06/2026 | 09 h 41 | Consultation de `git reflog` | Aucun changement anormal, force-push ou déplacement inattendu n’est détecté |
| 27/06/2026 | 09 h 45 | Vérification des fichiers non suivis et ignorés | Présence possible de fichiers locaux expliquant l’affichage observé |
| 27/06/2026 | 09 h 49 | Actualisation de l’IDE et de l’explorateur de fichiers | L’hypothèse d’un cache ou d’un état local non rafraîchi est retenue |
| 27/06/2026 | 09 h 52 | Validation finale de l’intégrité de `origin/main` | Aucun push involontaire ni modification distante n’est confirmé |
| 27/06/2026 | 10 h 00 | Requalification de l’incident | Incident classé comme faux positif lié à l’environnement local |
| 27/06/2026 | 10 h 05 | Clôture de l’incident | Aucun rollback ni action de restauration nécessaire |

---

# 2. Détection et qualification

## 2.1 Mode de détection

L’anomalie a été détectée manuellement lors d’une revue de l’arborescence du projet dans l’environnement de développement.

Les éléments suivants ont été observés :

- présence apparente du dossier `services/` ;
- présence du dossier `archive/` ;
- organisation des fichiers similaire à celle de la branche `refacto` ;
- impression que les changements de refactorisation étaient visibles depuis `main`.

## 2.2 Hypothèse initiale

L’hypothèse initiale était la suivante :

> Un commit de la branche `refacto` aurait pu être poussé ou fusionné accidentellement dans la branche `main`.

Cette hypothèse présentait un risque potentiel pour l’intégrité du dépôt, mais elle n’a pas été confirmée.

## 2.3 Niveau de sévérité

**Sévérité retenue : Mineure**

Justification :

- aucun déploiement en production ;
- aucune indisponibilité de service ;
- aucune perte ou corruption de données ;
- aucun utilisateur affecté ;
- aucune modification confirmée de la branche distante `main` ;
- investigation limitée au dépôt local.

---

# 3. Analyse de la cause probable

Les contrôles effectués ont démontré que la branche distante `origin/main` était intacte.

Aucune preuve n’a été trouvée concernant :

- un push involontaire ;
- une fusion non autorisée ;
- un force-push ;
- une modification de l’historique distant ;
- une erreur de la pipeline CI/CD ;
- un accès non autorisé au dépôt.

L’origine la plus probable est une **incohérence ou une confusion liée à l’environnement local**.

Les causes possibles sont :

1. **Fichiers non suivis ou ignorés**

   Des fichiers ou dossiers présents dans le répertoire de travail peuvent rester visibles après un changement de branche sans appartenir réellement à la branche active.

2. **État local non synchronisé**

   L’absence de `git fetch --prune` avant l’analyse peut conduire à comparer la branche locale avec des références distantes obsolètes.

3. **Cache de l’IDE**

   L’explorateur de fichiers ou l’index interne de l’IDE peut afficher temporairement une arborescence non actualisée.

4. **Confusion entre l’état local et l’état distant**

   L’apparence du répertoire de travail ne constitue pas une preuve qu’un changement a été poussé sur le dépôt distant.

### Cause racine retenue

> Absence de procédure de vérification systématique permettant de distinguer rapidement l’état local du répertoire de travail et l’état réel de la branche distante `origin/main`.

---

# 4. Impact

## 4.1 Impact technique

| Élément | Impact |
|---|---|
| Branche distante `main` | Aucun |
| Historique Git | Aucun |
| Code de production | Aucun |
| Pipeline CI/CD | Aucun |
| Services UrbanHub | Aucun |
| Base de données | Aucun |
| Données métier | Aucun |
| Utilisateurs | Aucun |

## 4.2 Impact opérationnel

L’impact opérationnel a été limité au temps consacré à l’investigation.

Aucune action d’urgence n’a été nécessaire :

- aucun rollback ;
- aucune restauration ;
- aucun arrêt de service ;
- aucune intervention d’astreinte ;
- aucune communication client.

---

# 5. Impact financier

| Poste | Estimation |
|---|---:|
| Temps d’investigation | 53 minutes |
| Coût horaire estimé | 60 €/heure |
| Coût estimé de l’investigation | environ **53 €** |
| Interruption de service | 0 € |
| Perte de données | 0 € |
| Pénalité SLA | 0 € |
| Coût d’infrastructure supplémentaire | 0 € |
| **Impact financier total estimé** | **environ 53 €** |

> Le coût est estimé à partir d’un taux fictif de **60 €/heure**. Il représente uniquement le temps consacré à l’analyse et à la vérification.

---

# 6. Impact écologique

Aucun service supplémentaire n’a été déployé.

Aucune instance supplémentaire n’a été démarrée et aucune réexécution importante de pipeline n’a été nécessaire.

Les seules ressources consommées sont liées à :

- l’exécution de commandes Git ;
- la synchronisation des références distantes ;
- l’utilisation de l’environnement de développement.

**Impact écologique estimé : négligeable.**

---

# 7. Actions correctives et préventives

| ID | Action | Responsable | Priorité | Échéance | Statut |
|---|---|---|---|---|---|
| `AC-01` | Ajouter la vérification `git fetch --prune origin` avant toute analyse d’écart | Équipe de développement | Haute | 04/07/2026 | À réaliser |
| `AC-02` | Ajouter `git status` à la procédure de contrôle | Équipe de développement | Haute | 04/07/2026 | À réaliser |
| `AC-03` | Documenter la comparaison entre `main` et `origin/main` | Référent technique | Moyenne | 11/07/2026 | À réaliser |
| `AC-04` | Créer un guide pratique dans `docs/how-to/` | Référent documentation | Moyenne | 11/07/2026 | À réaliser |
| `AC-05` | Étudier un hook `post-checkout` affichant la branche active | Équipe de développement | Faible | 18/07/2026 | À étudier |

---

# 8. Procédure de vérification ajoutée

Avant de déclencher une alerte concernant une modification supposée de `main`, exécuter les commandes suivantes.

## Étape 1 — Vérifier l’état local

```bash
git status
```

Vérifier :

- la branche active ;
- les fichiers modifiés ;
- les fichiers non suivis.

## Étape 2 — Mettre à jour les références distantes

```bash
git fetch --prune origin
```

Cette commande permet de mettre à jour les références distantes et de supprimer les références obsolètes.

## Étape 3 — Comparer la branche locale et la branche distante

```bash
git diff main origin/main
```

Cette commande permet de comparer le contenu de la branche locale avec la branche distante.

## Étape 4 — Vérifier l’historique des commits

```bash
git log --oneline --decorate --graph --all
```

Cette commande permet de visualiser les commits et les relations entre les branches.

## Étape 5 — Vérifier les changements locaux récents

```bash
git reflog
```

Cette commande permet de contrôler les changements de branche et les déplacements de références.

---

# 9. Conclusion

L’incident du **27 juin 2026** a été détecté rapidement et traité sans impact sur les services UrbanHub, les données ou les utilisateurs.

L’investigation a confirmé que :

- la branche distante `origin/main` était intacte ;
- aucun commit de `refacto` n’avait été poussé sur `main` ;
- aucune erreur de CI/CD n’était impliquée ;
- aucun rollback n’était nécessaire.

L’incident est donc classé comme un **faux positif lié à l’environnement local**.

La principale amélioration retenue consiste à formaliser une procédure de vérification distinguant :

> **l’état du répertoire de travail local**, **l’état de la branche locale** et **l’état réel de la branche distante**.

Cette action permettra de réduire les faux positifs et d’éviter des investigations inutiles lors de futures revues du dépôt.

---

## Historique du document

| Version | Date | Auteur | Modification |
|---|---|---|---|
| `1.0` | 27/06/2026 | Équipe UrbanHub | Création du rapport d’incident fictif |