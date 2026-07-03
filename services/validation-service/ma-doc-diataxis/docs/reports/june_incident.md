# Rapport d'incident — Juin 2026

**Statut :** Résolu (faux positif confirmé)
**Sévérité :** Mineure (aucun impact production)
**Périmètre :** Dépôt Git — branches `main` / `refacto`

---

## BLUF (Bottom Line Up Front)

Lors d'une revue de code, la branche `main` semblait contenir les changements de
la branche `refacto` (introduction du dossier `services/`, réorganisation de
l'ancien code dans `archive/`), laissant penser qu'un push accidentel vers
`main` avait eu lieu. **Après vérification, aucun push n'a été effectué sur
`main`** : l'écart observé provenait de l'état local du dépôt (checkout,
cache, ou référence obsolète) et non d'une modification réelle de l'historique
distant. Aucune donnée, aucun service et aucun utilisateur n'ont été affectés.
L'incident est classé **faux positif** ; l'action corrective porte uniquement
sur le processus de vérification avant toute alerte.

---

## 1. Chronologie

| Heure | Événement |
|---|---|
| T0 | Constat : `main` semble afficher l'arborescence `services/` + `archive/` propre à `refacto` |
| T0 + Δ | Doute sur un push involontaire vers `main` |
| T0 + Δ | Vérification via `git log`, `git diff main origin/main`, `git reflog` |
| T0 + Δ | Confirmation : `origin/main` distant est intact, aucun commit `refacto` n'y figure |
| Clôture | Incident requalifié en anomalie locale, pas de rollback nécessaire |

*(Horodatages précis à compléter si nécessaire pour l'archivage officiel.)*

## 2. Cause probable

Aucune modification serveur n'étant en cause, l'origine la plus probable est
locale :

- checkout ou switch de branche laissant des fichiers non trackés/ignorés visibles dans l'arborescence de travail,
- cache de l'IDE ou de l'explorateur de fichiers non rafraîchi,
- confusion entre l'état du répertoire de travail et l'état réel de `main` distant (absence de `git status` / `git fetch --prune` avant analyse).

Aucun accès non autorisé, aucune erreur de configuration CI/CD et aucun force-push n'ont été identifiés.

## 3. Bénéfices

- Validation que les protections de branche sur `main` fonctionnent correctement.
- Occasion de documenter une procédure de vérification rapide (`git fetch`, comparaison avec `origin/main`, `reflog`) avant escalade.
- Renforcement de la confiance dans l'intégrité du dépôt sans qu'aucune action de remédiation destructive n'ait été nécessaire.

## 4. Impact financier

| Poste | Estimation |
|---|---|
| Temps d'investigation développeur | ~quelques heures (à chiffrer selon taux horaire interne) |
| Interruption de service | Aucune — 0 € |
| Perte de données | Aucune — 0 € |
| Astreinte / support additionnel | Non déclenché |

**Impact financier net : négligeable**, limité au coût d'investigation. Aucun
SLA client n'a été affecté, aucune facturation d'infrastructure additionnelle
n'a été générée.

## 5. Impact écologique

Aucun service supplémentaire n'a été déployé, aucune instance additionnelle
n'a tourné, et aucune réexécution de pipeline de données à grande échelle n'a
été nécessaire.

**Impact écologique net : nul**, hormis la consommation marginale liée aux
commandes Git et à l'exploration locale du dépôt (négligeable).

## 6. Actions correctives

1. Ajouter un rappel systématique de `git fetch --prune && git status` avant toute alerte d'écart entre branches.
2. Documenter dans le guide pratique (`how-to/`) la procédure de vérification "état local vs distant" pour éviter les faux positifs similaires.
3. Envisager un hook local (`post-checkout`) affichant un résumé de la branche active pour réduire l'ambiguïté visuelle dans l'explorateur de fichiers.

## 7. Conclusion

Incident sans impact réel sur la production, les données ou les coûts
d'infrastructure. La vigilance de l'équipe a permis une détection rapide ;
l'action de suivi se concentre sur l'amélioration du processus de
vérification plutôt que sur une correction technique du service.
