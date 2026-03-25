#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SAIDA_DIR="${SAIDA_DIR:-saida_faculdade}"
ORIGEM_REL="${ORIGEM_REL:-$SAIDA_DIR/validados_faculdade.csv}"
DESTINO_REL="${DESTINO_REL:-$SAIDA_DIR/ja_filtrados_faculdade.csv}"

python3 - <<PY
import csv
from pathlib import Path

origem = Path("$ORIGEM_REL")
destino = Path("$DESTINO_REL")

def ler_emails(caminho: Path):
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        coluna = "email_validado" if "email_validado" in reader.fieldnames else reader.fieldnames[0]
        return [
            (linha.get(coluna) or "").strip().lower()
            for linha in reader
            if (linha.get(coluna) or "").strip()
        ]

vistos = set()
emails = []
for email in ler_emails(destino) + ler_emails(origem):
    if email in vistos:
        continue
    vistos.add(email)
    emails.append(email)

destino.parent.mkdir(parents=True, exist_ok=True)
with destino.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in emails:
        writer.writerow([email])

print(f"FILTRADOS_SINCRONIZADOS={len(emails)}")
PY
