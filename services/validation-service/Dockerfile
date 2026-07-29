# Image Python légère et version explicitement définie
FROM python:3.12-slim

# Variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Création d'un utilisateur non-root
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser

# Copier les dépendances avant le code
# Cela améliore l'utilisation du cache Docker
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier uniquement le code de l'application
COPY --chown=appuser:appgroup app/ ./app/

# Utiliser un utilisateur non-root
USER appuser

# Port documenté
EXPOSE 8002

# Vérification de l'état du service
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

# Démarrage du service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]