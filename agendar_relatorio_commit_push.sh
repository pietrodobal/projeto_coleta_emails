#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$ROOT/commit_push_agendado.log"
if [ -n "${PYTHON_BIN:-}" ]; then
  PY="$PYTHON_BIN"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PY="$ROOT/venv/bin/python"
else
  PY="$(command -v python3)"
fi
DELAY_SECONDS="${1:-28800}"
SAIDA_DIR="${SAIDA_DIR:-saida}"

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

"$PY" "$ROOT/gerar_relatorio_madrugada.py" --start-epoch "$START_EPOCH" --output "RELATORIO_MADRUGADA.md" --saida-dir "$SAIDA_DIR" >> "$LOG" 2>&1

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
