#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
cd "$ROOT"

LOG="auto_pos_coleta.log"
echo "[$(date '+%F %T')] monitor iniciado" >> "$LOG"

VALIDADOS_NOVO_REL="${VALIDADOS_NOVO_REL:-emails_validados_novos.csv}"
BRUTOS_NOVO_REL="${BRUTOS_NOVO_REL:-emails_brutos_novos.csv}"
REJEITADOS_IA_REL="${REJEITADOS_IA_REL:-}"
PRESERVAR_NOVOS="${PRESERVAR_NOVOS:-0}"

while pgrep -af "python .*coleta_emails.py --lote --ia" >/dev/null 2>&1; do
  sleep 30
done

echo "[$(date '+%F %T')] job IA finalizado, iniciando merge" >> "$LOG"

"/home/pietro/.virtualenvs/.venv/bin/python" - << 'PY'
import csv
import os
from pathlib import Path

base = Path("saida")

validados_antigo = base / "emails_validados.csv"
validados_novo = base / os.getenv("VALIDADOS_NOVO_REL", "emails_validados_novos.csv")
brutos_antigo = base / "emails_brutos_sem_ia.csv"
brutos_novo = base / os.getenv("BRUTOS_NOVO_REL", "emails_brutos_novos.csv")
rejeitados = base / "Rejeitados.csv"

rejeitados_ia_rel = os.getenv("REJEITADOS_IA_REL", "").strip()
rejeitados_ia_novo = base / rejeitados_ia_rel if rejeitados_ia_rel else None

preservar_novos = os.getenv("PRESERVAR_NOVOS", "0") == "1"


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


def dedupe_preserva_ordem(emails):
    vistos = set()
    unicos = []
    for e in emails:
        chave = e.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(e)
    return unicos


validados_existentes = dedupe_preserva_ordem(ler_emails(validados_antigo))
validados_existentes_set = {e.lower() for e in validados_existentes}
validados_novos_raw = dedupe_preserva_ordem(ler_emails(validados_novo))

validados_novos_filtrados = [
    e for e in validados_novos_raw
    if e.lower() not in validados_existentes_set
]

if validados_novo.exists():
    salvar_unicos(validados_novo, validados_novos_filtrados)

validados_finais = validados_existentes + validados_novos_filtrados
validados_count = salvar_unicos(validados_antigo, validados_finais)

rejeitados_existentes = dedupe_preserva_ordem(ler_emails(rejeitados) + ler_emails(brutos_antigo))
rejeitados_existentes_set = {e.lower() for e in rejeitados_existentes}

rejeitados_novos_raw = dedupe_preserva_ordem(
    ler_emails(brutos_novo) + (ler_emails(rejeitados_ia_novo) if rejeitados_ia_novo else [])
)

validados_finais_set = {e.lower() for e in dedupe_preserva_ordem(validados_finais)}
rejeitados_novos_filtrados = [
    e for e in rejeitados_novos_raw
    if e.lower() not in rejeitados_existentes_set and e.lower() not in validados_finais_set
]

if brutos_novo.exists():
    salvar_unicos(brutos_novo, rejeitados_novos_filtrados)

if rejeitados_ia_novo and rejeitados_ia_novo.exists():
    salvar_unicos(rejeitados_ia_novo, rejeitados_novos_filtrados)

rejeitados_finais = rejeitados_existentes + rejeitados_novos_filtrados
brutos_count = salvar_unicos(rejeitados, rejeitados_finais)

if not preservar_novos and brutos_novo.exists():
    brutos_novo.unlink()

if not preservar_novos and validados_novo.exists():
    validados_novo.unlink()

if rejeitados_ia_novo and not preservar_novos and rejeitados_ia_novo.exists():
    rejeitados_ia_novo.unlink()

if brutos_antigo.exists():
    brutos_antigo.unlink()

print(f"VALIDADOS_UNICOS={validados_count}")
print(f"BRUTOS_UNICOS={brutos_count}")
print(f"PRESERVOU_ARQUIVOS_NOVOS={preservar_novos}")
print(f"VALIDADOS_NOVOS_REL={os.getenv('VALIDADOS_NOVO_REL', '')}")
print(f"BRUTOS_NOVOS_REL={os.getenv('BRUTOS_NOVO_REL', '')}")
PY

STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "[$(date '+%F %T')] merge concluído com sucesso" >> "$LOG"
else
  echo "[$(date '+%F %T')] merge falhou com status $STATUS" >> "$LOG"
fi
