#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "${PYTHON_BIN:-}" ]; then
  PY="$PYTHON_BIN"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PY="$ROOT/venv/bin/python"
else
  PY="$(command -v python3)"
fi
LOG="$ROOT/ciclo_horario.log"
BUSCA_JANELA_SECONDS="${BUSCA_JANELA_SECONDS:-1800}"
BUSCA_NUM_RESULTADOS="${BUSCA_NUM_RESULTADOS:-45}"
BUSCA_RODADAS="${BUSCA_RODADAS:-3}"
BUSCA_MAX_URLS_POR_SITE="${BUSCA_MAX_URLS_POR_SITE:-12}"
BUSCA_LIMITE_TOTAL="${BUSCA_LIMITE_TOTAL:-2500}"
BUSCA_BACKOFF_BASE="${BUSCA_BACKOFF_BASE:-6.0}"
BUSCA_PAUSA_MIN="${BUSCA_PAUSA_MIN:-1.5}"
BUSCA_PAUSA_MAX="${BUSCA_PAUSA_MAX:-3.5}"
SHARD_COUNT="${SHARD_COUNT:-1}"
SHARD_INDEX="${SHARD_INDEX:-0}"
SAIDA_DIR="${SAIDA_DIR:-saida}"
export SAIDA_DIR
LISTA_URLS_REL="${LISTA_URLS_REL:-$SAIDA_DIR/lista_urls_faculdade.py}"
export LISTA_URLS_ARQUIVO="$LISTA_URLS_REL"
USAR_IA="${USAR_IA:-0}"
EMAILS_TOTAL_REL="${EMAILS_TOTAL_REL:-a_validar_faculdade.csv}"
VALIDADOS_FACULDADE_REL="${VALIDADOS_FACULDADE_REL:-$SAIDA_DIR/validados_faculdade.csv}"
JA_FILTRADOS_REL="${JA_FILTRADOS_REL:-$SAIDA_DIR/ja_filtrados_faculdade.csv}"
JANELA_AGRUPAR_BRUTOS_SECONDS="${JANELA_AGRUPAR_BRUTOS_SECONDS:-21600}"
SESSAO_LOG="$ROOT/$SAIDA_DIR/SESSOES.txt"
CONTADOR_SESSAO="$ROOT/.sessao_contador"

cd "$ROOT"

SESSION_MARCA="$(date '+%Y%m%d_%H%M%S')"
JANELA_INICIO_EPOCH="$(date +%s)"
JANELA_FIM_EPOCH="$((JANELA_INICIO_EPOCH + JANELA_AGRUPAR_BRUTOS_SECONDS))"
JANELA_FIM_FMT="$(date -d "@$JANELA_FIM_EPOCH" '+%Y%m%d_%H%M%S')"
BRUTOS_UNIFICADO_REL="ciclos/${SESSION_MARCA}_ATE_${JANELA_FIM_FMT}_emails_sobra_unificado.csv"
echo "[$(date '+%F %T')] ciclo_horario iniciado [SESSAO: $SESSION_MARCA]" >> "$LOG"
echo "[$(date '+%F %T')] shard ativo: index=$SHARD_INDEX count=$SHARD_COUNT" >> "$LOG"
echo "" >> "$SESSAO_LOG"
echo "=== SESSAO: $SESSION_MARCA ===" >> "$SESSAO_LOG"
echo "Início: $(date '+%F %T')" >> "$SESSAO_LOG"
echo "Arquivo sobra unificado (6h): $BRUTOS_UNIFICADO_REL" >> "$SESSAO_LOG"
echo "Shard: index=$SHARD_INDEX count=$SHARD_COUNT" >> "$SESSAO_LOG"
echo "Modo IA: $USAR_IA" >> "$SESSAO_LOG"
echo "Arquivo a validar: $EMAILS_TOTAL_REL" >> "$SESSAO_LOG"

"$PY" - <<PY
import csv
from pathlib import Path
destino = Path("$SAIDA_DIR") / "$BRUTOS_UNIFICADO_REL"
destino.parent.mkdir(parents=True, exist_ok=True)
if not destino.exists():
  with destino.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
PY

CICLO_NUM=0

ao_encerrar() {
  echo "[$(date '+%F %T')] encerrando ciclo_horario (sinal recebido)" >> "$LOG"
  echo "Fim: $(date '+%F %T')" >> "$SESSAO_LOG"
  pkill -f "python .*buscar_urls.py" || true
  exit 0
}
trap ao_encerrar INT TERM

while true; do
  CICLO_NUM=$((CICLO_NUM + 1))
  echo "[$(date '+%F %T')] ciclo #$CICLO_NUM iniciado [SESSAO: $SESSION_MARCA]" >> "$LOG"

  ciclo_id="$(date '+%Y%m%d_%H%M%S')"
  ciclo_prefixo="${SESSION_MARCA}_CICLO${CICLO_NUM}"
  mkdir -p "$ROOT/$SAIDA_DIR/ciclos"

  BRUTOS_CICLO_REL="ciclos/${ciclo_prefixo}_emails_brutos_${ciclo_id}.csv"
  VALIDADOS_CICLO_REL="ciclos/${ciclo_prefixo}_emails_validados_${ciclo_id}.csv"
  REJEITADOS_IA_CICLO_REL="ciclos/${ciclo_prefixo}_rejeitados_ia_${ciclo_id}.csv"

  echo "[$(date '+%F %T')] etapa 1: coleta sem IA" >> "$LOG"
  "$PY" coleta_emails.py --lote --shard-count "$SHARD_COUNT" --shard-index "$SHARD_INDEX" --saida "$BRUTOS_CICLO_REL" >> "$LOG" 2>&1 || true

  bash "$ROOT/sincronizar_filtrados_faculdade.sh" >> "$LOG" 2>&1 || true

  "$PY" - <<PY >> "$LOG" 2>&1 || true
import csv
from pathlib import Path

origem = Path("$SAIDA_DIR") / "$BRUTOS_CICLO_REL"
total = Path("$SAIDA_DIR") / "$EMAILS_TOTAL_REL"
validados = Path("$VALIDADOS_FACULDADE_REL")
filtrados = Path("$JA_FILTRADOS_REL")

def ler_emails(caminho: Path):
    if not caminho.exists():
        return []
    with caminho.open("r", newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames:
            return []
        coluna = "email_validado" if "email_validado" in leitor.fieldnames else leitor.fieldnames[0]
        return [
            (linha.get(coluna) or "").strip().lower()
            for linha in leitor
            if (linha.get(coluna) or "").strip()
        ]

vistos = set()
combinados = []
ja_validados = set(ler_emails(validados) + ler_emails(filtrados))
for email in ler_emails(total) + ler_emails(origem):
  if email in ja_validados:
    continue
  if email in vistos:
    continue
  vistos.add(email)
  combinados.append(email)

total.parent.mkdir(parents=True, exist_ok=True)
with total.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in combinados:
        writer.writerow([email])

print(f"EMAILS_TOTAL={len(combinados)}")
PY

  agora_janela="$(date +%s)"
  if [ "$agora_janela" -le "$JANELA_FIM_EPOCH" ]; then
    "$PY" - <<PY >> "$LOG" 2>&1
import csv
from pathlib import Path

origem = Path("$SAIDA_DIR") / "$BRUTOS_CICLO_REL"
destino = Path("$SAIDA_DIR") / "$BRUTOS_UNIFICADO_REL"
validados = Path("$SAIDA_DIR") / "emails_validados.csv"

def ler_emails(caminho: Path):
    if not caminho.exists():
        return []
    with caminho.open("r", newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames:
            return []
        coluna = "email_validado" if "email_validado" in leitor.fieldnames else leitor.fieldnames[0]
        return [
            (linha.get(coluna) or "").strip().lower()
            for linha in leitor
            if (linha.get(coluna) or "").strip()
        ]

validados_set = set(ler_emails(validados))

vistos = set()
combinados = []
for email in ler_emails(destino) + ler_emails(origem):
    if email in validados_set:
        continue
    if email in vistos:
        continue
    vistos.add(email)
    combinados.append(email)

destino.parent.mkdir(parents=True, exist_ok=True)
with destino.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in combinados:
        writer.writerow([email])

print(f"SOBRA_UNIFICADO_TOTAL={len(combinados)}")
PY
  else
    echo "[$(date '+%F %T')] janela de unificação de brutos encerrada: $BRUTOS_UNIFICADO_REL" >> "$LOG"
  fi

  if [ "$USAR_IA" = "1" ]; then
    echo "[$(date '+%F %T')] etapa 2: coleta com IA em cascata" >> "$LOG"
    "$PY" coleta_emails.py --lote --ia --shard-count "$SHARD_COUNT" --shard-index "$SHARD_INDEX" --saida "$VALIDADOS_CICLO_REL" --saida-rejeitados "$REJEITADOS_IA_CICLO_REL" >> "$LOG" 2>&1 || true

    echo "[$(date '+%F %T')] etapa 3: consolidar em Rejeitados (emails brutos)" >> "$LOG"
    VALIDADOS_NOVO_REL="$VALIDADOS_CICLO_REL" \
    BRUTOS_NOVO_REL="$BRUTOS_CICLO_REL" \
    REJEITADOS_IA_REL="$REJEITADOS_IA_CICLO_REL" \
    PRESERVAR_NOVOS=1 \
    SAIDA_DIR="$SAIDA_DIR" \
    bash auto_pos_coleta.sh >> "$LOG" 2>&1 || true
  else
    echo "[$(date '+%F %T')] etapa 2 (IA) desativada por USAR_IA=$USAR_IA" >> "$LOG"
    echo "[$(date '+%F %T')] etapa 3 (consolidação IA) desativada por USAR_IA=$USAR_IA" >> "$LOG"
  fi

  agora_janela="$(date +%s)"
  if [ "$agora_janela" -le "$JANELA_FIM_EPOCH" ]; then
    "$PY" - <<PY >> "$LOG" 2>&1
import csv
from pathlib import Path

destino = Path("$SAIDA_DIR") / "$BRUTOS_UNIFICADO_REL"
validados = Path("$SAIDA_DIR") / "emails_validados.csv"

def ler_emails(caminho: Path):
    if not caminho.exists():
        return []
    with caminho.open("r", newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames:
            return []
        coluna = "email_validado" if "email_validado" in leitor.fieldnames else leitor.fieldnames[0]
        return [
            (linha.get(coluna) or "").strip().lower()
            for linha in leitor
            if (linha.get(coluna) or "").strip()
        ]

validados_set = set(ler_emails(validados))
vistos = set()
sobra = []
for email in ler_emails(destino):
    if email in validados_set:
        continue
    if email in vistos:
        continue
    vistos.add(email)
    sobra.append(email)

destino.parent.mkdir(parents=True, exist_ok=True)
with destino.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in sobra:
        writer.writerow([email])

print(f"SOBRA_UNIFICADO_POS_CONSOLIDACAO={len(sobra)}")
PY
  fi

  echo "[$(date '+%F %T')] etapa 4: buscar_urls por janela fixa de ${BUSCA_JANELA_SECONDS}s" >> "$LOG"
  inicio_busca=$(date +%s)
  fim_busca=$((inicio_busca + BUSCA_JANELA_SECONDS))

  while true; do
    agora=$(date +%s)
    if [ "$agora" -ge "$fim_busca" ]; then
      break
    fi

    "$PY" buscar_urls.py \
      --acumular \
      --saida "$LISTA_URLS_REL" \
      --num-resultados "$BUSCA_NUM_RESULTADOS" \
      --rodadas "$BUSCA_RODADAS" \
      --max-urls-por-site "$BUSCA_MAX_URLS_POR_SITE" \
      --limite-total "$BUSCA_LIMITE_TOTAL" \
      --backoff-base "$BUSCA_BACKOFF_BASE" \
      --pausa-min "$BUSCA_PAUSA_MIN" \
      --pausa-max "$BUSCA_PAUSA_MAX" \
      >> "$LOG" 2>&1 &
    pid_busca=$!

    while true; do
      agora=$(date +%s)
      if [ "$agora" -ge "$fim_busca" ]; then
        if kill -0 "$pid_busca" >/dev/null 2>&1; then
          kill "$pid_busca" >/dev/null 2>&1 || true
          sleep 2
        fi
        break 2
      fi

      if ! kill -0 "$pid_busca" >/dev/null 2>&1; then
        break
      fi

      sleep 5
    done

    sleep 2
  done

  pkill -f "python .*buscar_urls.py" || true
  echo "[$(date '+%F %T')] ciclo #$CICLO_NUM finalizado [SESSAO: $SESSION_MARCA]" >> "$LOG"
  echo "  Ciclo #$CICLO_NUM: $(date '+%F %T') - $ciclo_prefixo" >> "$SESSAO_LOG"
done
