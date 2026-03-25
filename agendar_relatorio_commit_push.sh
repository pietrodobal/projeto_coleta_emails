#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
LOG="$ROOT/commit_push_agendado.log"
PY="/home/pietro/.virtualenvs/.venv/bin/python"
DELAY_SECONDS="${1:-28800}"

cd "$ROOT"

START_EPOCH="$(date +%s)"
DISPARO_EM="$(date -d "+${DELAY_SECONDS} seconds" '+%Y-%m-%d %H:%M:%S')"

echo "[$(date '+%F %T')] agendamento criado: delay=${DELAY_SECONDS}s disparo=${DISPARO_EM}" >> "$LOG"

action_script="$ROOT/.run_relatorio_commit_push_once.sh"
cat > "$action_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"

echo "[\$(date '+%F %T')] execução agendada iniciada" >> "$LOG"

"$PY" "$ROOT/gerar_relatorio_madrugada.py" --start-epoch "$START_EPOCH" --output "RELATORIO_MADRUGADA.md" >> "$LOG" 2>&1

git add -A >> "$LOG" 2>&1
if git diff --cached --quiet; then
  echo "[\$(date '+%F %T')] sem mudanças para commit" >> "$LOG"
  exit 0
fi

COMMIT_MSG="chore: relatório da madrugada + atualizações automáticas (\$(date '+%Y-%m-%d %H:%M'))"
git commit -m "\$COMMIT_MSG" >> "$LOG" 2>&1

git push origin main >> "$LOG" 2>&1

echo "[\$(date '+%F %T')] commit/push concluído" >> "$LOG"
EOF

nohup bash -c "sleep $DELAY_SECONDS; bash '$action_script'" >> "$LOG" 2>&1 &
SCHED_PID=$!

echo "AGENDADO_PID=$SCHED_PID"
echo "AGENDADO_PARA=$DISPARO_EM"
echo "LOG=$LOG"
