#!/usr/bin/env bash
set -euo pipefail
ROOT="/workspaces/projeto_coleta_emails"
LOG="$ROOT/commit_branch_agendado.log"
BRANCH="Remoto"
REMOTE="origin"
cd "$ROOT"

echo "[$(date '+%F %T')] execução agendada iniciada (branch=$BRANCH)" >> "$LOG"
echo "[$(date '+%F %T')] coleta mantida em execução (sem stop/pkill)" >> "$LOG"

git fetch "$REMOTE" >> "$LOG" 2>&1 || true
git switch "$BRANCH" >> "$LOG" 2>&1
echo "[$(date '+%F %T')] pull desativado: fluxo configurado para apenas commit/push" >> "$LOG"

git add saida_faculdade RELATORIO_MADRUGADA.md >> "$LOG" 2>&1 || true
if git diff --cached --quiet; then
  echo "[$(date '+%F %T')] sem mudanças para commit" >> "$LOG"
else
  git commit -m "chore: atualização automática da coleta remota ($(date '+%Y-%m-%d %H:%M'))" >> "$LOG" 2>&1
  git push -u "$REMOTE" "$BRANCH" >> "$LOG" 2>&1
  echo "[$(date '+%F %T')] commit/push concluído em $BRANCH" >> "$LOG"
fi

echo "[$(date '+%F %T')] execução agendada finalizada" >> "$LOG"
