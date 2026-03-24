#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
cd "$ROOT"

LOG="auto_pos_coleta.log"
echo "[$(date '+%F %T')] monitor iniciado" >> "$LOG"

while pgrep -af "python .*coleta_emails.py --lote --ia" >/dev/null 2>&1; do
  sleep 30
done

echo "[$(date '+%F %T')] job IA finalizado, iniciando merge" >> "$LOG"

"/home/pietro/.virtualenvs/.venv/bin/python" - << 'PY'
import csv
from pathlib import Path

base = Path("saida")

validados_antigo = base / "emails_validados.csv"
validados_novo = base / "emails_validados_novos.csv"
brutos_antigo = base / "emails_brutos_sem_ia.csv"
brutos_novo = base / "emails_brutos_novos.csv"
rejeitados = base / "Rejeitados.csv"


def ler_emails(caminho: Path):
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        campo = "email_validado" if "email_validado" in reader.fieldnames else reader.fieldnames[0]
        return [
            (linha.get(campo) or "").strip()
            for linha in reader
            if (linha.get(campo) or "").strip()
        ]


def salvar_unicos(caminho: Path, emails):
    vistos = set()
    unicos = []
    for e in emails:
        k = e.lower()
        if k in vistos:
            continue
        vistos.add(k)
        unicos.append(e)

    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["email_validado"])
        for e in unicos:
            writer.writerow([e])
    return len(unicos)

validados_count = salvar_unicos(
    validados_antigo,
    ler_emails(validados_antigo) + ler_emails(validados_novo),
)

brutos_count = salvar_unicos(
    rejeitados,
    ler_emails(rejeitados) + ler_emails(brutos_antigo) + ler_emails(brutos_novo),
)

if brutos_novo.exists():
    brutos_novo.unlink()

if brutos_antigo.exists():
    brutos_antigo.unlink()

print(f"VALIDADOS_UNICOS={validados_count}")
print(f"BRUTOS_UNICOS={brutos_count}")
print(f"REMOVIDO_BRUTO_NOVO={not brutos_novo.exists()}")
PY

STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "[$(date '+%F %T')] merge concluído com sucesso" >> "$LOG"
else
  echo "[$(date '+%F %T')] merge falhou com status $STATUS" >> "$LOG"
fi
