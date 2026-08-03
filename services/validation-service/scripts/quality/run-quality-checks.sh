#!/usr/bin/env bash
#
# Script de qualité code pour UrbanHub
# - ruff
# - bandit
#
# Usage:
#   ./run-quality-checks.sh
#
# Retour:
#   0 si OK
#   1 si erreurs
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $*" >&2; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $*" >&2; }
log_error() { echo -e "${RED}[✗]${NC} $*" >&2; }
log_check() { echo -e "${BLUE}[?]${NC} $*" >&2; }

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_python_tooling() {
    log_check "Vérification de Python et des outils..."

    local missing=0

    if ! command_exists python; then
        log_error "python introuvable"
        missing=1
    else
        log_info "python disponible"
    fi

    if ! command_exists ruff; then
        log_error "ruff introuvable"
        missing=1
    else
        log_info "ruff disponible"
    fi

    if ! command_exists bandit; then
        log_error "bandit introuvable"
        missing=1
    else
        log_info "bandit disponible"
    fi

    return "$missing"
}

run_ruff_check() {
    log_check "Exécution de ruff check..."

    if ! ruff check \
        "$ROOT_DIR/sensor-simulator" \
        "$ROOT_DIR/services/ingestion-service/app" \
        "$ROOT_DIR/services/validation-service/app"; then
        log_error "ruff check a échoué"
        return 1
    fi

    log_info "ruff check OK"
    return 0
}

run_ruff_format_check() {
    log_check "Exécution de ruff format --check..."

    if ! ruff format --check \
        "$ROOT_DIR/sensor-simulator" \
        "$ROOT_DIR/services/ingestion-service/app" \
        "$ROOT_DIR/services/validation-service/app"; then
        log_error "ruff format --check a échoué"
        return 1
    fi

    log_info "ruff format --check OK"
    return 0
}

run_bandit() {
    log_check "Exécution de bandit..."

    if ! bandit -r \
        "$ROOT_DIR/sensor-simulator" \
        "$ROOT_DIR/services/ingestion-service/app" \
        "$ROOT_DIR/services/validation-service/app" \
        -x "$ROOT_DIR/services/validation-service/tests" \
        -x "$ROOT_DIR/services/ingestion-service/tests"; then
        log_error "bandit a échoué"
        return 1
    fi

    log_info "bandit OK"
    return 0
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

main() {
    echo "=========================================="
    echo "        CONTRÔLE QUALITÉ URBANHUB"
    echo "=========================================="
    echo "Racine projet : $ROOT_DIR"
    echo ""

    local passed=0
    local failed=0

    local checks=(
        check_python_tooling
        run_ruff_check
        run_ruff_format_check
        run_bandit
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
        exit 1
    fi

    log_info "Contrôles qualité terminés avec succès."
    exit 0
}

main "$@"