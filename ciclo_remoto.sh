#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export SAIDA_DIR="${SAIDA_DIR:-saida_faculdade}"
export USAR_IA="${USAR_IA:-0}"
export LISTA_URLS_REL="${LISTA_URLS_REL:-$SAIDA_DIR/lista_urls_faculdade.py}"
export EMAILS_TOTAL_REL="${EMAILS_TOTAL_REL:-a_validar_faculdade.csv}"

export SHARD_COUNT="${SHARD_COUNT_REMOTE:-1}"
export SHARD_INDEX="${SHARD_INDEX_REMOTE:-0}"

exec bash "$ROOT/ciclo_horario.sh"
