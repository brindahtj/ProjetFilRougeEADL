## Résultat du test Canary (site-a)

Le patch mineur (6 paquets, notamment libssl3/libcrypto3) a révélé un effet de
bord réaliste : le processus sshd, démarré manuellement avant le patch, a été
interrompu suite à la mise à jour de la librairie SSL qu'il avait chargée en
mémoire. Ce comportement, bien que spécifique à notre configuration de test
(sshd lancé manuellement plutôt que via un service systemd/OpenRC avec
rechargement automatique), illustre concrètement l'intérêt du test canary :
détecter une régression sur 1 nœud avant propagation au reste du parc.

Action corrective : redémarrage automatisé du service dans le playbook,
avec vérification post-patch. Recommandation avant rollout complet : dans un
environnement de production réel, utiliser un gestionnaire de service
(systemd/OpenRC) capable de recharger sshd automatiquement après mise à jour
de ses dépendances, plutôt qu'un lancement manuel.