#!/usr/bin/env bash
# Marca o início de uma sessão de coleta/validação
# Cria um ID único e adiciona ao ciclo_horario.sh para rastrear ciclos

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
SESSAO_LOG="$ROOT/saida/SESSOES.txt"

SESSION_ID="$(date '+%Y%m%d_%H%M%S')"
echo "[SESSION_START] $SESSION_ID" >> "$SESSAO_LOG"
echo "Sessão marcada: $SESSION_ID" >&2

export SESSION_MARKER="$SESSION_ID"
