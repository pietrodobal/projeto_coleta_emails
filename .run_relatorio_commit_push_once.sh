#!/usr/bin/env bash
set -euo pipefail
cd "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"

echo "[$(date '+%F %T')] execução agendada iniciada" >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log"

"/home/pietro/.virtualenvs/.venv/bin/python" "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/gerar_relatorio_madrugada.py" --start-epoch "1774432592" --output "RELATORIO_MADRUGADA.md" >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log" 2>&1

git add -A >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log" 2>&1
if git diff --cached --quiet; then
  echo "[$(date '+%F %T')] sem mudanças para commit" >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log"
  exit 0
fi

COMMIT_MSG="chore: relatório da madrugada + atualizações automáticas ($(date '+%Y-%m-%d %H:%M'))"
git commit -m "$COMMIT_MSG" >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log" 2>&1

git push origin main >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log" 2>&1

echo "[$(date '+%F %T')] commit/push concluído" >> "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails/commit_push_agendado.log"
