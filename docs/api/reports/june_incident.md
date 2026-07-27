# Rapport d'évaluation – Incident de pollution (Juin)

## Résumé exécutif (BLUF)

Le système Smart City a détecté automatiquement un épisode de pollution dans la zone de Paris. Les données reçues par les capteurs IoT ont été validées, enregistrées et une alerte a été générée afin de prévenir les services concernés. Le système a fonctionné conformément aux exigences prévues.

---

## Contexte

Le projet Smart City supervise en temps réel les données issues de capteurs environnementaux répartis dans différentes zones urbaines.

Le 30 juin, un capteur de pollution a transmis une mesure dépassant le seuil critique défini par le système.

---

## Déroulement de l'incident

1. Réception des données du capteur IoT.
2. Validation des informations reçues.
3. Détection d'un dépassement du seuil critique.
4. Enregistrement de la mesure.
5. Génération d'une alerte RabbitMQ.
6. Journalisation de l'événement.

---

## Impacts

### Impact environnemental

- Détection rapide d'un épisode de pollution.
- Possibilité d'avertir rapidement les autorités compétentes.

### Impact financier

- Réduction du coût des interventions grâce à une détection précoce.
- Diminution des risques liés aux incidents environnementaux.

### Impact opérationnel

- Surveillance continue des capteurs.
- Amélioration de la réactivité des équipes.
- Traçabilité complète des événements.

---

## Conclusion

L'incident a été correctement pris en charge par le système Smart City. Les différentes étapes du traitement (collecte, validation, stockage et génération d'alerte) se sont déroulées conformément aux spécifications fonctionnelles.