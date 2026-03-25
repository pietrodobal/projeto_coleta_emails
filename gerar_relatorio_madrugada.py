#!/usr/bin/env python3
import argparse
import ast
import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera relatório da madrugada para coleta de e-mails.")
    parser.add_argument("--start-epoch", type=int, required=True, help="Epoch de início da janela.")
    parser.add_argument("--output", default="RELATORIO_MADRUGADA.md", help="Arquivo de saída do relatório.")
    return parser.parse_args()


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)


def list_recent_files(folder: Path, pattern: str, start_epoch: int, end_epoch: int) -> list[tuple[float, Path]]:
    out = []
    if not folder.exists():
        return out
    for item in folder.glob(pattern):
        try:
            mtime = item.stat().st_mtime
        except FileNotFoundError:
            continue
        if start_epoch <= mtime <= end_epoch:
            out.append((mtime, item))
    out.sort(key=lambda x: x[0])
    return out


def count_urls_lista(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return 0

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "urls":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        return 0
                    return len(value) if isinstance(value, list) else 0
    return 0


def count_log_events(path: Path, start_epoch: int, end_epoch: int) -> dict:
    stats = {
        "ciclos_iniciados": 0,
        "ciclos_finalizados": 0,
        "erros_indentacao": 0,
        "etapa1": 0,
        "etapa2": 0,
        "etapa3": 0,
        "etapa4": 0,
    }
    if not path.exists():
        return stats

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if len(line) < 21 or line[0] != "[":
            if "IndentationError" in line:
                stats["erros_indentacao"] += 1
            continue

        try:
            ts_str = line[1:20]
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            epoch = int(dt.timestamp())
        except Exception:
            if "IndentationError" in line:
                stats["erros_indentacao"] += 1
            continue

        if not (start_epoch <= epoch <= end_epoch):
            continue

        low = line.lower()
        if "ciclo #" in low and "iniciado" in low:
            stats["ciclos_iniciados"] += 1
        if "ciclo #" in low and "finalizado" in low:
            stats["ciclos_finalizados"] += 1
        if "etapa 1" in low:
            stats["etapa1"] += 1
        if "etapa 2" in low:
            stats["etapa2"] += 1
        if "etapa 3" in low:
            stats["etapa3"] += 1
        if "etapa 4" in low:
            stats["etapa4"] += 1
        if "indentationerror" in low:
            stats["erros_indentacao"] += 1

    return stats


def main() -> int:
    args = parse_args()
    start_epoch = args.start_epoch
    end_epoch = int(datetime.now().timestamp())

    saida = ROOT / "saida"
    ciclos = saida / "ciclos"

    validados = count_csv_rows(saida / "emails_validados.csv")
    rejeitados = count_csv_rows(saida / "Rejeitados.csv")

    sobras = sorted(ciclos.glob("*emails_sobra_unificado.csv"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    sobra_ativa = sobras[-1] if sobras else None
    sobra_ativa_count = count_csv_rows(sobra_ativa) if sobra_ativa else 0

    novos_brutos = list_recent_files(ciclos, "*emails_brutos*.csv", start_epoch, end_epoch)
    novos_validados_ciclo = list_recent_files(ciclos, "*emails_validados*.csv", start_epoch, end_epoch)
    novos_rejeitados_ciclo = list_recent_files(ciclos, "*rejeitados_ia*.csv", start_epoch, end_epoch)
    novas_sobras = list_recent_files(ciclos, "*emails_sobra_unificado.csv", start_epoch, end_epoch)

    total_urls_lista = count_urls_lista(ROOT / "lista_urls.py")
    log_stats = count_log_events(ROOT / "ciclo_horario.log", start_epoch, end_epoch)

    start_fmt = datetime.fromtimestamp(start_epoch).strftime("%Y-%m-%d %H:%M:%S")
    end_fmt = datetime.fromtimestamp(end_epoch).strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# Relatório da Madrugada")
    lines.append("")
    lines.append(f"- Janela analisada: {start_fmt} até {end_fmt}")
    lines.append(f"- URLs totais em lista_urls.py: {total_urls_lista}")
    lines.append("")
    lines.append("## Resultado acumulado")
    lines.append("")
    lines.append(f"- emails_validados.csv: {validados}")
    lines.append(f"- Rejeitados.csv: {rejeitados}")
    if sobra_ativa:
        lines.append(f"- Sobra ativa: {sobra_ativa.as_posix()} ({sobra_ativa_count} linhas)")
    else:
        lines.append("- Sobra ativa: não encontrada")
    lines.append("")
    lines.append("## Atividade de ciclos")
    lines.append("")
    lines.append(f"- Ciclos iniciados: {log_stats['ciclos_iniciados']}")
    lines.append(f"- Ciclos finalizados: {log_stats['ciclos_finalizados']}")
    lines.append(f"- Etapa 1 executada: {log_stats['etapa1']} vez(es)")
    lines.append(f"- Etapa 2 executada: {log_stats['etapa2']} vez(es)")
    lines.append(f"- Etapa 3 executada: {log_stats['etapa3']} vez(es)")
    lines.append(f"- Etapa 4 executada: {log_stats['etapa4']} vez(es)")
    lines.append(f"- IndentationError no período: {log_stats['erros_indentacao']}")
    lines.append("")

    def section(title: str, rows: list[tuple[float, Path]]):
        lines.append(f"## {title}")
        lines.append("")
        if not rows:
            lines.append("- Nenhum arquivo no período")
            lines.append("")
            return
        for mtime, p in rows:
            dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"- {dt} — {p.as_posix()}")
        lines.append("")

    section("Brutos criados/atualizados", novos_brutos)
    section("Validados de ciclo criados/atualizados", novos_validados_ciclo)
    section("Rejeitados IA de ciclo criados/atualizados", novos_rejeitados_ciclo)
    section("Sobras unificadas criadas/atualizadas", novas_sobras)

    output = ROOT / args.output
    output.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"RELATORIO_GERADO={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
