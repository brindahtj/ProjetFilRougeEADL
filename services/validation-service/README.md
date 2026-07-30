## 🤖 Utilisation de l'IA Générative dans le Projet

L'intelligence artificielle a été intégrée dans le processus de développement comme un **assistant de programmation (Pair Programmer)** afin d'accélérer la résolution de problèmes et d'améliorer la qualité du code.

### 🎯 Cas d'usage principaux
* **Débogage et résolution d'erreurs :** Analyse des logs d'erreurs d'intégration continue (CI/CD) sur GitHub Actions (erreurs d'import Python `E402`, fausses alertes de couverture avec `pytest-cov`, résolutions de chemins Docker).
* **Sécurisation de la CI/CD :** Configuration et correction des étapes du pipeline DevSecOps (intégration de Trivy, Cosign, Syft, OWASP ZAP).
* **Optimisation des Dockerfiles :** Restructuration des conteneurs (mise en place de build multi-étapes et réduction des vulnérabilités d'images de base).
* **Debogage de tests après ruff:** Correction tests unitaires pour passer ruff.

### 🛡️ Contrôle Qualité et Supervision Humaine
L'ensemble du code généré ou suggéré par l'IA a suivi un processus stricte de vérification :
1. **Revue de code :** Chaque suggestion a été relue, comprise et adaptée à l'architecture du projet.
2. **Validation automatisée :** Exécution des linters (`ruff`), des scanners SAST/SCA (`bandit`, `trivy`) et des tests unitaires (`pytest`) pour s'assurer qu'aucune régression ou vulnérabilité n'était introduite.
3. **Prise de décision finale :** Les choix d'architecture (structure des dossiers, stratégie d'ingestion des variables d'environnement) ont été entièrement pilotés par moi .