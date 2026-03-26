#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
PY="/home/pietro/.virtualenvs/.venv/bin/python"
LOG="$ROOT/ciclo_horario.log"

if [ -f "$ROOT/.credenciais" ]; then
  set -a
  source "$ROOT/.credenciais"
  set +a
fi

BUSCA_JANELA_SECONDS="${BUSCA_JANELA_SECONDS:-1800}"
BUSCA_ENGINE="${BUSCA_ENGINE:-auto}"
BUSCA_AUTO_PROVEDORES="${BUSCA_AUTO_PROVEDORES:-google,bing,duckduckgo,yandex,brave,qwant,cse}"
BUSCA_APENAS_BR="0"
BUSCA_APENAS_LATAM="${BUSCA_APENAS_LATAM:-1}"
BUSCA_NUM_RESULTADOS="${BUSCA_NUM_RESULTADOS:-80}"
BUSCA_RODADAS="${BUSCA_RODADAS:-7}"
BUSCA_MAX_URLS_POR_SITE="${BUSCA_MAX_URLS_POR_SITE:-30}"
BUSCA_LIMITE_TOTAL="${BUSCA_LIMITE_TOTAL:-8000}"
BUSCA_MAX_TENTATIVAS="${BUSCA_MAX_TENTATIVAS:-2}"
BUSCA_BACKOFF_BASE="${BUSCA_BACKOFF_BASE:-6.0}"
BUSCA_PAUSA_MIN="${BUSCA_PAUSA_MIN:-2.0}"
BUSCA_PAUSA_MAX="${BUSCA_PAUSA_MAX:-4.5}"
BUSCA_DESCANSO_ENTRE_EXECUCOES="${BUSCA_DESCANSO_ENTRE_EXECUCOES:-2}"
A_VALIDAR_ARQUIVO_REL="${A_VALIDAR_ARQUIVO_REL:-a_validar_manual.csv}"
JANELA_AGRUPAR_BRUTOS_SECONDS="${JANELA_AGRUPAR_BRUTOS_SECONDS:-21600}"
SESSAO_LOG="$ROOT/saida/SESSOES.txt"
CONTADOR_SESSAO="$ROOT/.sessao_contador"

cd "$ROOT"

SESSION_MARCA="$(date '+%Y%m%d_%H%M%S')"
JANELA_INICIO_EPOCH="$(date +%s)"
JANELA_FIM_EPOCH="$((JANELA_INICIO_EPOCH + JANELA_AGRUPAR_BRUTOS_SECONDS))"
JANELA_FIM_FMT="$(date -d "@$JANELA_FIM_EPOCH" '+%Y%m%d_%H%M%S')"
BRUTOS_UNIFICADO_REL="ciclos/${SESSION_MARCA}_ATE_${JANELA_FIM_FMT}_emails_sobra_unificado.csv"
echo "[$(date '+%F %T')] ciclo_horario iniciado [SESSAO: $SESSION_MARCA]" >> "$LOG"
echo "" >> "$SESSAO_LOG"
echo "=== SESSAO: $SESSION_MARCA ===" >> "$SESSAO_LOG"
echo "Início: $(date '+%F %T')" >> "$SESSAO_LOG"
echo "Arquivo sobra unificado (6h): $BRUTOS_UNIFICADO_REL" >> "$SESSAO_LOG"

"$PY" - <<PY
import csv
from pathlib import Path
destino = Path("saida") / "$BRUTOS_UNIFICADO_REL"
destino.parent.mkdir(parents=True, exist_ok=True)
if not destino.exists():
  with destino.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
PY

"$PY" - <<PY
import csv
from pathlib import Path
destino = Path("saida") / "$A_VALIDAR_ARQUIVO_REL"
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

BUSCA_APENAS_BR_FLAG=""
if [ "$BUSCA_APENAS_BR" = "1" ]; then
  BUSCA_APENAS_BR_FLAG="--apenas-br"
fi

BUSCA_APENAS_LATAM_FLAG=""
if [ "$BUSCA_APENAS_LATAM" = "1" ]; then
  BUSCA_APENAS_LATAM_FLAG="--apenas-latam"
fi

while true; do
  CICLO_NUM=$((CICLO_NUM + 1))
  echo "[$(date '+%F %T')] ciclo #$CICLO_NUM iniciado [SESSAO: $SESSION_MARCA]" >> "$LOG"

  ciclo_id="$(date '+%Y%m%d_%H%M%S')"
  ciclo_prefixo="${SESSION_MARCA}_CICLO${CICLO_NUM}"
  mkdir -p "$ROOT/saida/ciclos"

  BRUTOS_CICLO_REL="ciclos/${ciclo_prefixo}_emails_brutos_${ciclo_id}.csv"
  VALIDADOS_CICLO_REL="ciclos/${ciclo_prefixo}_emails_validados_${ciclo_id}.csv"
  REJEITADOS_IA_CICLO_REL="ciclos/${ciclo_prefixo}_rejeitados_ia_${ciclo_id}.csv"

  echo "[$(date '+%F %T')] etapa 1: coleta sem IA" >> "$LOG"
  "$PY" coleta_emails.py --lote --saida "$BRUTOS_CICLO_REL" >> "$LOG" 2>&1 || true

  agora_janela="$(date +%s)"
  if [ "$agora_janela" -le "$JANELA_FIM_EPOCH" ]; then
    "$PY" - <<PY >> "$LOG" 2>&1
import csv
from pathlib import Path

origem = Path("saida") / "$BRUTOS_CICLO_REL"
destino = Path("saida") / "$BRUTOS_UNIFICADO_REL"
validados = Path("saida") / "emails_validados.csv"

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

  echo "[$(date '+%F %T')] etapa 2: coleta com IA em cascata" >> "$LOG"
  "$PY" coleta_emails.py --lote --ia --saida "$VALIDADOS_CICLO_REL" --saida-rejeitados "$REJEITADOS_IA_CICLO_REL" >> "$LOG" 2>&1 || true

  echo "[$(date '+%F %T')] etapa 3: consolidar em Rejeitados (emails brutos)" >> "$LOG"
  VALIDADOS_NOVO_REL="$VALIDADOS_CICLO_REL" \
  BRUTOS_NOVO_REL="$BRUTOS_CICLO_REL" \
  REJEITADOS_IA_REL="$REJEITADOS_IA_CICLO_REL" \
  PRESERVAR_NOVOS=1 \
  bash auto_pos_coleta.sh >> "$LOG" 2>&1 || true

  A_VALIDAR_CICLO_REL="ciclos/${ciclo_prefixo}_A_VALIDAR_MANUAL_${ciclo_id}.csv"
  "$PY" - <<PY >> "$LOG" 2>&1
import csv
from pathlib import Path

brutos_ciclo = Path("saida") / "$BRUTOS_CICLO_REL"
validados = Path("saida") / "emails_validados.csv"
a_validar = Path("saida") / "$A_VALIDAR_ARQUIVO_REL"
a_validar_ciclo = Path("saida") / "$A_VALIDAR_CICLO_REL"

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
pendentes_atuais = ler_emails(a_validar)
pendentes_set = set(pendentes_atuais)
novos = []

for email in ler_emails(brutos_ciclo):
    if email in validados_set:
        continue
    if email in pendentes_set:
        continue
    pendentes_set.add(email)
    novos.append(email)

final = []
vistos = set()
for email in pendentes_atuais + novos:
    if email in validados_set:
        continue
    if email in vistos:
        continue
    vistos.add(email)
    final.append(email)

a_validar.parent.mkdir(parents=True, exist_ok=True)
with a_validar.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in final:
        writer.writerow([email])

a_validar_ciclo.parent.mkdir(parents=True, exist_ok=True)
with a_validar_ciclo.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["email_validado"])
    for email in novos:
        writer.writerow([email])

print(f"A_VALIDAR_NOVOS_CICLO={len(novos)}")
print(f"A_VALIDAR_TOTAL={len(final)}")
print(f"A_VALIDAR_ARQUIVO=saida/$A_VALIDAR_ARQUIVO_REL")
print(f"A_VALIDAR_CICLO_ARQUIVO=saida/$A_VALIDAR_CICLO_REL")
PY

  agora_janela="$(date +%s)"
  if [ "$agora_janela" -le "$JANELA_FIM_EPOCH" ]; then
    "$PY" - <<PY >> "$LOG" 2>&1
import csv
from pathlib import Path

destino = Path("saida") / "$BRUTOS_UNIFICADO_REL"
validados = Path("saida") / "emails_validados.csv"

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
      --engine "$BUSCA_ENGINE" \
      --acumular \
      $BUSCA_APENAS_BR_FLAG \
      $BUSCA_APENAS_LATAM_FLAG \
      --num-resultados "$BUSCA_NUM_RESULTADOS" \
      --rodadas "$BUSCA_RODADAS" \
      --max-urls-por-site "$BUSCA_MAX_URLS_POR_SITE" \
      --limite-total "$BUSCA_LIMITE_TOTAL" \
      --max-tentativas "$BUSCA_MAX_TENTATIVAS" \
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

    sleep "$BUSCA_DESCANSO_ENTRE_EXECUCOES"
  done

  pkill -f "python .*buscar_urls.py" || true
  echo "[$(date '+%F %T')] ciclo #$CICLO_NUM finalizado [SESSAO: $SESSION_MARCA]" >> "$LOG"
  echo "  Ciclo #$CICLO_NUM: $(date '+%F %T') - $ciclo_prefixo" >> "$SESSAO_LOG"
done
