#!/usr/bin/env bash
#
# Script d'installation et vérification du stack UrbanHub via docker-compose.yml
#
# Usage:
#   ./install-and-check.sh
#
# Retour:
#   0 si OK
#   1 si erreur
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

# Détection du runtime conteneur
CONTAINER_RUNTIME=""
COMPOSE_CMD=""

detect_container_runtime() {
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        CONTAINER_RUNTIME="docker"
        COMPOSE_CMD="docker compose"
    elif command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
        CONTAINER_RUNTIME="podman"
        if podman compose version >/dev/null 2>&1; then
            COMPOSE_CMD="podman compose"
        elif command -v podman-compose >/dev/null 2>&1; then
            COMPOSE_CMD="podman-compose"
        else
            COMPOSE_CMD=""
        fi
    fi
}

detect_container_runtime

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# LOGS
# ============================================================================

log_info()  { echo -e "${GREEN}[✓]${NC} $*" >&2; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $*" >&2; }
log_error() { echo -e "${RED}[✗]${NC} $*" >&2; }
log_check() { echo -e "${BLUE}[?]${NC} $*" >&2; }

# ============================================================================
# UTILITAIRES
# ============================================================================

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_file() {
    local file="$1"
    if [ ! -e "$ROOT_DIR/$file" ]; then
        log_error "Fichier ou dossier manquant: $file"
        return 1
    fi
    log_info "Présent: $file"
    return 0
}

wait_for_http() {
    local url="$1"
    local expected_code="${2:-200}"
    local max_attempts="${3:-30}"
    local delay="${4:-3}"

    local attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
        local code
        code="$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$url" || echo "000")"

        if [ "$code" = "$expected_code" ]; then
            log_info "OK: $url (HTTP $code)"
            return 0
        fi

        if [ $((attempt % 10)) -eq 0 ]; then
            log_warn "Attente de $url... tentative $attempt/$max_attempts (HTTP $code)"
        fi

        sleep "$delay"
        attempt=$((attempt + 1))
    done

    log_error "Timeout: $url n'a pas répondu avec HTTP $expected_code"
    return 1
}

# ============================================================================
# VÉRIFICATIONS SYSTÈME
# ============================================================================

check_prerequisites() {
    log_check "Vérification des outils système..."

    local failed=0

    if ! command_exists curl; then
        log_error "curl est requis"
        failed=1
    else
        log_info "curl disponible"
    fi

    if ! command_exists git; then
        log_warn "git n'est pas disponible (pas bloquant pour l'exécution du compose)"
    else
        log_info "git disponible"
    fi

    if ! command_exists openssl; then
        log_warn "openssl n'est pas disponible (utile seulement si tu veux générer des secrets)"
    else
        log_info "openssl disponible"
    fi

    if ! command_exists df; then
        log_warn "df non trouvé"
    fi

    return "$failed"
}

check_runtime() {
    log_check "Vérification du runtime conteneur..."

    if [ -z "$CONTAINER_RUNTIME" ] || [ -z "$COMPOSE_CMD" ]; then
        log_error "Docker/Podman avec compose n'est pas disponible"
        return 1
    fi

    log_info "Runtime détecté: $CONTAINER_RUNTIME"
    log_info "Commande compose: $COMPOSE_CMD"
    return 0
}

check_project_files() {
    log_check "Vérification des fichiers attendus..."

    local ok=0

    check_file "docker-compose.yml" || ok=1
    check_file "prometheus.yml" || ok=1
    check_file "tempo.yaml" || log_warn "tempo.yaml non trouvé à la racine (vérifie le volume du service tempo)"
    check_file "logstash" || ok=1
    check_file "grafana/provisioning/alerting/alerting.yml" || ok=1
    check_file "grafana/provisioning/alerting/alerts.yml" || ok=1
    check_file "sensor-simulator" || ok=1
    check_file "services/ingestion-service" || ok=1
    check_file "services/validation-service" || ok=1

    return "$ok"
}

validate_compose() {
    log_check "Validation du fichier compose..."

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose introuvable: $COMPOSE_FILE"
        return 1
    fi

    if ! $COMPOSE_CMD -f "$COMPOSE_FILE" config >/dev/null; then
        log_error "Le compose contient une erreur de syntaxe ou de résolution"
        return 1
    fi

    log_info "docker-compose.yml valide"
    return 0
}

check_env_file() {
    log_check "Vérification du fichier .env..."

    if [ ! -f "$ENV_FILE" ]; then
        log_warn "Aucun .env trouvé à la racine. Le compose peut quand même fonctionner si toutes les variables sont définies ailleurs."
        return 0
    fi

    log_info ".env trouvé: $ENV_FILE"

    local required_vars=(
        "RABBIT_USER"
        "RABBIT_PASS"
        "RABBIT_VHOST"
        "RABBIT_QUEUE"
        "RABBIT_HOST"
        "RABBIT_PORT"
        "INGESTION_API_URL"
        "MEASUREMENTS_PER_SECOND"
    )

    local missing=0
    for var in "${required_vars[@]}"; do
        if ! grep -Eq "^${var}=" "$ENV_FILE"; then
            log_warn "Variable absente du .env: $var"
            missing=1
        fi
    done

    return 0
}

# ============================================================================
# LANCEMENT DES SERVICES
# ============================================================================

start_services() {
    log_check "Arrêt/nettoyage des anciens conteneurs..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true

    log_check "Démarrage du stack..."
    if ! $COMPOSE_CMD -f "$COMPOSE_FILE" up -d; then
        log_error "Échec du démarrage du stack"
        return 1
    fi

    log_info "Stack démarré"
    return 0
}

wait_for_services() {
    log_check "Attente des services HTTP..."

    local ok=0

    wait_for_http "http://localhost:8000/health" 200 40 3 || ok=1
    wait_for_http "http://localhost:8002/health" 200 40 3 || ok=1

    # Services avec UI/ports exposés: on teste seulement l'ouverture TCP implicite via HTTP
    # Grafana / pgAdmin / Prometheus peuvent répondre avec des codes différents selon l'état.
    wait_for_http "http://localhost:3000" 200 20 3 || log_warn "Grafana ne répond pas en HTTP 200 immédiatement"
    wait_for_http "http://localhost:9090" 200 20 3 || log_warn "Prometheus ne répond pas en HTTP 200 immédiatement"
    wait_for_http "http://localhost:5050" 200 20 3 || log_warn "pgAdmin ne répond pas en HTTP 200 immédiatement"

    return "$ok"
}

smoke_test_ingestion() {
    log_check "Smoke test ingestion..."

    local payload
    payload='[{"metric":"pm25","value":12.3,"unit":"µg/m³","recorded_at":"2026-08-03T00:00:00Z"}]'

    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "http://localhost:8000/api/v1/sensors/TEST-001/metrics" \
        -H "Content-Type: application/json" \
        -d "$payload" || echo "000")"

    if [ "$code" = "202" ] || [ "$code" = "200" ]; then
        log_info "Ingestion OK (HTTP $code)"
        return 0
    fi

    log_warn "Ingestion a répondu HTTP $code"
    return 1
}

smoke_test_validation() {
    log_check "Smoke test validation..."

    local payload
    payload='{"sensor_type":"air","city":"Paris","latitude":48.8566,"longitude":2.3522,"timestamp":"2026-08-03T00:00:00Z","pollutant":"pm25","value":12.3}'

    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "http://localhost:8002/validate" \
        -H "Content-Type: application/json" \
        -d "$payload" || echo "000")"

    if [ "$code" = "200" ]; then
        log_info "Validation OK (HTTP $code)"
        return 0
    fi

    log_warn "Validation a répondu HTTP $code"
    return 1
}

print_summary() {
    local passed="$1"
    local failed="$2"

    echo ""
    echo "=========================================="
    echo "              RÉSUMÉ"
    echo "=========================================="
    echo -e "Tests réussis: ${GREEN}${passed}${NC}"
    echo -e "Tests échoués : ${RED}${failed}${NC}"
    echo "=========================================="
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo "=========================================="
    echo "   INSTALLATION / VÉRIFICATION URBANHUB"
    echo "=========================================="
    echo "Racine projet : $ROOT_DIR"
    echo "Compose       : $COMPOSE_FILE"
    echo "Runtime       : ${CONTAINER_RUNTIME:-non détecté}"
    echo ""

    local passed=0
    local failed=0

    local checks=(
        check_prerequisites
        check_runtime
        check_project_files
        validate_compose
        check_env_file
    )

    for check in "${checks[@]}"; do
        if "$check"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
        echo ""
    done

    print_summary "$passed" "$failed"

    if [ "$failed" -gt 0 ]; then
        log_error "Des prérequis ne sont pas satisfaits."
        exit 1
    fi

    if ! start_services; then
        exit 1
    fi

    echo ""
    if ! wait_for_services; then
        log_warn "Tous les services n'ont pas répondu correctement."
    fi

    echo ""
    smoke_test_ingestion || true
    smoke_test_validation || true

    echo ""
    log_info "Script terminé."
    exit 0
}

main "$@"