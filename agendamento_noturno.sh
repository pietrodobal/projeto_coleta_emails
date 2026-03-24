#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
PY="/home/pietro/.virtualenvs/.venv/bin/python"
LOG="$ROOT/agendamento_noturno.log"

# Uso:
#   bash agendamento_noturno.sh --em-horas 6
#   bash agendamento_noturno.sh --em-minutos 180
#   bash agendamento_noturno.sh --agora

MODO=""
VALOR=""

if [[ ${1:-} == "--agora" ]]; then
  MODO="agora"
elif [[ ${1:-} == "--em-horas" && -n ${2:-} ]]; then
  MODO="horas"
  VALOR="$2"
elif [[ ${1:-} == "--em-minutos" && -n ${2:-} ]]; then
  MODO="minutos"
  VALOR="$2"
else
  echo "Uso:"
  echo "  bash agendamento_noturno.sh --em-horas 6"
  echo "  bash agendamento_noturno.sh --em-minutos 180"
  echo "  bash agendamento_noturno.sh --agora"
  exit 1
fi

cd "$ROOT"

echo "[$(date '+%F %T')] agendamento iniciado (modo=$MODO valor=${VALOR:-0})" >> "$LOG"

if [[ "$MODO" == "horas" ]]; then
  sleep "$((VALOR * 3600))"
elif [[ "$MODO" == "minutos" ]]; then
  sleep "$((VALOR * 60))"
fi

echo "[$(date '+%F %T')] etapa 1: pausar buscar_urls" >> "$LOG"
if pgrep -af "python .*buscar_urls.py" >/dev/null 2>&1; then
  pkill -f "python .*buscar_urls.py" || true
  sleep 3
fi

if pgrep -af "python .*buscar_urls.py" >/dev/null 2>&1; then
  echo "[$(date '+%F %T')] aviso: buscar_urls ainda ativo após tentativa de pausa" >> "$LOG"
else
  echo "[$(date '+%F %T')] buscar_urls pausado" >> "$LOG"
fi

echo "[$(date '+%F %T')] etapa 2: coleta sem IA" >> "$LOG"
"$PY" coleta_emails.py --lote --saida emails_brutos_novos.csv >> "$LOG" 2>&1

echo "[$(date '+%F %T')] etapa 3: coleta com IA" >> "$LOG"
"$PY" coleta_emails.py --lote --ia --saida emails_validados_novos.csv >> "$LOG" 2>&1

echo "[$(date '+%F %T')] etapa 4: pós-processo (merge + Rejeitados)" >> "$LOG"
bash auto_pos_coleta.sh >> "$LOG" 2>&1

echo "[$(date '+%F %T')] fluxo noturno concluído" >> "$LOG"
