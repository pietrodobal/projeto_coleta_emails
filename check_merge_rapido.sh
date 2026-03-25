#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "== Estado do merge =="
git status --short
echo "Conflitos indexados:"
git ls-files -u

echo
echo "== Comparação rápida de resultados =="
python3 - <<'PY'
import csv
import ast
from pathlib import Path


def ler_csv(path: str) -> set[str]:
    arquivo = Path(path)
    if not arquivo.exists():
        return set()

    with arquivo.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return set()
        coluna = "email_validado" if "email_validado" in reader.fieldnames else reader.fieldnames[0]
        return {
            (linha.get(coluna) or "").strip().lower()
            for linha in reader
            if (linha.get(coluna) or "").strip()
        }


def contar_urls_py(path: str) -> int:
    arquivo = Path(path)
    if not arquivo.exists():
        return 0

    conteudo = arquivo.read_text(encoding="utf-8")
    arvore = ast.parse(conteudo)
    for node in arvore.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "urls":
                    valor = ast.literal_eval(node.value)
                    return len(valor) if isinstance(valor, list) else 0
    return 0


main_validados = ler_csv("saida/emails_validados.csv")
faculdade_validados = ler_csv("saida_faculdade/emails_validados.csv")
main_rejeitados = ler_csv("saida/Rejeitados.csv")
faculdade_rejeitados = ler_csv("saida_faculdade/Rejeitados.csv")

print(f"validados_main={len(main_validados)}")
print(f"validados_faculdade={len(faculdade_validados)}")
print(f"validados_intersecao={len(main_validados & faculdade_validados)}")
print(f"validados_so_main={len(main_validados - faculdade_validados)}")
print(f"validados_so_faculdade={len(faculdade_validados - main_validados)}")
print()
print(f"rejeitados_main={len(main_rejeitados)}")
print(f"rejeitados_faculdade={len(faculdade_rejeitados)}")
print(f"rejeitados_intersecao={len(main_rejeitados & faculdade_rejeitados)}")
print()
print(f"urls_faculdade={contar_urls_py('saida_faculdade/lista_urls_faculdade.py')}")
PY
