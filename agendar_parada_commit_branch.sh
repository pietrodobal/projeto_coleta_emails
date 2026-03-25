#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$ROOT/commit_branch_agendado.log"
if [ -n "${PYTHON_BIN:-}" ]; then
  PY="$PYTHON_BIN"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PY="$ROOT/venv/bin/python"
else
  PY="$(command -v python3)"
fi

ALVO_HORA="${1:-11:10}"
TARGET_BRANCH="${2:-results/saida_faculdade_$(date '+%Y%m%d_%H%M')}"
BASE_BRANCH="${BASE_BRANCH:-main}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
SAIDA_DIR="${SAIDA_DIR:-saida_faculdade}"
TARGET_TZ="${TARGET_TZ:-America/Sao_Paulo}"

cd "$ROOT"

AGORA_EPOCH="$(date +%s)"
HOJE_LOCAL="$(TZ="$TARGET_TZ" date +%F)"
STOP_EPOCH="$(TZ="$TARGET_TZ" date -d "$HOJE_LOCAL $ALVO_HORA" +%s)"
if [ "$STOP_EPOCH" -le "$AGORA_EPOCH" ]; then
  AMANHA_LOCAL="$(TZ="$TARGET_TZ" date -d "tomorrow" +%F)"
  STOP_EPOCH="$(TZ="$TARGET_TZ" date -d "$AMANHA_LOCAL $ALVO_HORA" +%s)"
fi
DELAY_SECONDS="$((STOP_EPOCH - AGORA_EPOCH))"
START_EPOCH="$AGORA_EPOCH"
DISPARO_EM_LOCAL="$(TZ="$TARGET_TZ" date -d "@$STOP_EPOCH" '+%Y-%m-%d %H:%M:%S %Z')"
DISPARO_EM_SERVIDOR="$(date -d "@$STOP_EPOCH" '+%Y-%m-%d %H:%M:%S %Z')"

echo "[$(date '+%F %T')] agendamento criado: alvo=$ALVO_HORA tz=$TARGET_TZ disparo_local=$DISPARO_EM_LOCAL disparo_servidor=$DISPARO_EM_SERVIDOR branch=$TARGET_BRANCH saida_dir=$SAIDA_DIR" >> "$LOG"

action_script="$ROOT/.run_parada_commit_branch_once.sh"
cat > "$action_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"

echo "[\$(date '+%F %T')] execução agendada iniciada" >> "$LOG"

bash "$ROOT/supervisor_noturno.sh" stop >> "$LOG" 2>&1 || true
pkill -f "ciclo_horario.sh" >> "$LOG" 2>&1 || true
sleep 2

if [ ! -x "$PY" ]; then
  echo "[\$(date '+%F %T')] python não encontrado em $PY" >> "$LOG"
  exit 1
fi

"$PY" "$ROOT/gerar_relatorio_madrugada.py" \
  --start-epoch "$START_EPOCH" \
  --output "RELATORIO_MADRUGADA.md" \
  --saida-dir "$SAIDA_DIR" \
  >> "$LOG" 2>&1

if git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
  git switch "$TARGET_BRANCH" >> "$LOG" 2>&1
else
  git switch -c "$TARGET_BRANCH" >> "$LOG" 2>&1
fi

git add "$SAIDA_DIR" "RELATORIO_MADRUGADA.md" >> "$LOG" 2>&1 || true

if git diff --cached --quiet; then
  echo "[\$(date '+%F %T')] sem mudanças para commit em $TARGET_BRANCH" >> "$LOG"
else
  COMMIT_MSG="chore: resultados $SAIDA_DIR até $ALVO_HORA (\$(date '+%Y-%m-%d %H:%M'))"
  git commit -m "\$COMMIT_MSG" >> "$LOG" 2>&1
  git push -u "$REMOTE_NAME" "$TARGET_BRANCH" >> "$LOG" 2>&1
  echo "[\$(date '+%F %T')] commit/push concluído em $TARGET_BRANCH" >> "$LOG"
fi

git switch "$BASE_BRANCH" >> "$LOG" 2>&1 || true
echo "[\$(date '+%F %T')] execução agendada finalizada" >> "$LOG"
EOF

chmod +x "$action_script"
nohup bash -c "sleep $DELAY_SECONDS; bash '$action_script'" >> "$LOG" 2>&1 &
SCHED_PID=$!

echo "AGENDADO_PID=$SCHED_PID"
echo "AGENDADO_PARA_LOCAL=$DISPARO_EM_LOCAL"
echo "AGENDADO_PARA_SERVIDOR=$DISPARO_EM_SERVIDOR"
echo "TARGET_TZ=$TARGET_TZ"
echo "BRANCH_ALVO=$TARGET_BRANCH"
echo "SAIDA_DIR=$SAIDA_DIR"
echo "LOG=$LOG"
