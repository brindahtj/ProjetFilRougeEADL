# UrbanHub — Observabilité : justification des alertes

## Tableau SLO de référence (TP1)

| SLO | Cible | Budget/mois | Politique |
|---|---|---|---|
| Fiabilité ingestion trafic + pollution | 99,95% | 21,6 min | Vert >50% ; Orange 10-50% ; Rouge <10% : feature freeze |
| Fraîcheur des données (<60s) | 99,90% | 43,2 min | Vert >50% ; Orange 10-50% : surveiller ingestion ; Rouge <10% : corriger avant nouvelles features |
| Synchronisation trafic-pollution (<60s) | 99% | 432 min | Vert >50% ; Orange 10-50% ; Rouge <10% : suspendre évolutions |
| Latence moteur de corrélation (P95 <2s) | 95% | 2160 min | Vert >50% ; Orange 10-50% : profiler ; Rouge <10% : priorité latence |
| Disponibilité API de consultation | 99,90% | 43,2 min | Vert >50% ; Orange 10-50% ; Rouge <10% : feature freeze |

---

## Alerte 1 — Latence P95 > 500ms sur 5 min → `warning`

**SLO concerné** : Disponibilité API de consultation (99,90%) et, indirectement, Latence du moteur de corrélation (P95 < 2s).

**Pourquoi 500ms et pas 2s ?**
Le SLO "moteur de corrélation" tolère jusqu'à 2s en P95 car c'est un
traitement lourd (calcul de corrélation trafic/pollution). L'endpoint
`ingestion` mesuré ici est une opération beaucoup plus simple (validation
+ publication RabbitMQ) : il doit rester très en-dessous de ce budget pour
laisser de la marge au reste de la chaîne. 500ms = 25% du budget du
moteur de corrélation, ce qui garde une réserve confortable pour les
étapes suivantes du pipeline (validation, corrélation, stockage).

**Pourquoi `warning` et pas `critical` ?**
Une latence élevée dégrade l'expérience mais ne casse pas encore le
service (les requêtes aboutissent). On alerte tôt pour agir avant que ça
ne devienne un problème de disponibilité.

---

## Alerte 2 — Error rate > 1% sur 5 min → `critical`

**SLO concerné** : Fiabilité ingestion trafic + pollution (99,95%, budget
21,6 min/mois, soit ~0,05% d'erreurs tolérées en continu).

**Pourquoi 1% et pas 0,05% ?**
0,05% est la cible *moyenne mensuelle*, pas un seuil d'alerte temps réel —
avec un trafic modeste, une seule requête en erreur peut dépasser 0,05%
sur une fenêtre de 5 min sans que ce soit un incident réel (bruit
statistique). 1% est un multiplicateur ×20 par rapport à la cible : c'est
la signature d'un **fast burn** (principe des burn-rate alerts façon
Google SRE) — à ce rythme, le budget mensuel de 21,6 min serait épuisé en
quelques heures si la situation persiste. D'où le niveau `critical` :
c'est un incident, pas du bruit.

---

## Alerte 3 — Capteur muet > 5 min → `warning`

**SLO concerné** : Fraîcheur des données (<60s, 99,90%, budget
43,2 min/mois).

**Pourquoi 5 min ?**
5 minutes de silence = 5 min de données non fraîches pour ce capteur, ce
qui représente **~11,5% du budget mensuel de fraîcheur (43,2 min)**
consommé par un seul incident. On alerte à ce stade — avant d'atteindre
la zone rouge (<10% de budget restant) — pour donner le temps
d'intervenir (politique "Orange" du SLO : surveiller ingestion, limiter
les changements risqués) plutôt que de découvrir le problème une fois le
budget épuisé.

**Pourquoi `warning` et pas `critical` ?**
Un seul capteur muet n'est pas encore une panne système globale — les
autres capteurs continuent de fournir des données. Ça deviendrait
`critical` si tous les capteurs d'un type (`air` ou `traffic`) étaient
muets simultanément.

**Limite connue** : la requête PromQL utilisée
(`sum(increase(urbanhub_measurements_total[5m])) by (sensor_type)`) ne
déclenche que si la série existe encore dans Prometheus avec une valeur
`< 1`. Si le capteur/service ne publie plus *aucune* métrique du tout
(processus arrêté), la série peut disparaître au lieu de passer à 0 —
Prometheus ne peut pas distinguer "0 mesure" de "aucune série". Pour un
projet plus poussé, on utiliserait `absent_over_time()` en complément.

---

## Comment provoquer chaque alerte (chaos manuel)

| Alerte | Comment la déclencher |
|---|---|
| Latence P95 | Charger la DB Postgres artificiellement (ex: boucle `INSERT` massive) ou ajouter un `time.sleep()` temporaire dans `post_sensor_metrics` |
| Error rate | Arrêter RabbitMQ (`docker stop urbanhub_rabbitmq`) le temps que `ingestion` échoue ses publications, ou envoyer des requêtes malformées en masse |
| Capteur muet | `docker stop urbanhub_simulator` — plus aucune mesure n'arrive, la série `urbanhub_measurements_total` cesse d'augmenter |

Pour chaque cas : capturez (1) la notification reçue sur webhook.site,
et (2) le graphe Grafana correspondant avec l'annotation d'alerte visible
(Grafana ajoute automatiquement une ligne verticale rouge sur le panneau
au moment du déclenchement).
