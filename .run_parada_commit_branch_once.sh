#!/usr/bin/env bash
set -euo pipefail
cd "/workspaces/projeto_coleta_emails"

echo "[$(date '+%F %T')] execução agendada iniciada" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log"

bash "/workspaces/projeto_coleta_emails/supervisor_noturno.sh" stop >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1 || true
pkill -f "ciclo_horario.sh" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1 || true
sleep 2

if [ ! -x "/home/codespace/.python/current/bin/python3" ]; then
  echo "[$(date '+%F %T')] python não encontrado em /home/codespace/.python/current/bin/python3" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log"
  exit 1
fi

"/home/codespace/.python/current/bin/python3" "/workspaces/projeto_coleta_emails/gerar_relatorio_madrugada.py"   --start-epoch "1774439471"   --output "RELATORIO_MADRUGADA.md"   --saida-dir "saida_faculdade"   >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1

if git show-ref --verify --quiet "refs/heads/results/saida_faculdade_hoje"; then
  git switch "results/saida_faculdade_hoje" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1
else
  git switch -c "results/saida_faculdade_hoje" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1
fi

git add "saida_faculdade" "RELATORIO_MADRUGADA.md" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1 || true

if git diff --cached --quiet; then
  echo "[$(date '+%F %T')] sem mudanças para commit em results/saida_faculdade_hoje" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log"
else
  COMMIT_MSG="chore: resultados saida_faculdade até 11:10 ($(date '+%Y-%m-%d %H:%M'))"
  git commit -m "$COMMIT_MSG" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1
  git push -u "origin" "results/saida_faculdade_hoje" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1
  echo "[$(date '+%F %T')] commit/push concluído em results/saida_faculdade_hoje" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log"
fi

git switch "main" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log" 2>&1 || true
echo "[$(date '+%F %T')] execução agendada finalizada" >> "/workspaces/projeto_coleta_emails/commit_branch_agendado.log"
