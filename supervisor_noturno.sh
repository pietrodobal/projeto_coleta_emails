#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"
LOG="$ROOT/supervisor_noturno.log"
SUP_PID_FILE="$ROOT/.supervisor_noturno.pid"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-60}"

cd "$ROOT"

log() {
  echo "[$(date '+%F %T')] $1" >> "$LOG"
}

is_supervisor_running() {
  if [[ -f "$SUP_PID_FILE" ]]; then
    local pid
    pid="$(cat "$SUP_PID_FILE" 2>/dev/null || true)"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
    return $?
  fi
  return 1
}

is_ciclo_running() {
  pgrep -af "bash ciclo_horario.sh" >/dev/null 2>&1
}

start_ciclo() {
  nohup bash "$ROOT/ciclo_horario.sh" >> "$ROOT/ciclo_horario.log" 2>&1 &
  local ciclo_pid=$!
  log "ciclo_horario iniciado automaticamente (pid=$ciclo_pid)"
}

run_supervisor() {
  log "supervisor iniciado (intervalo=${CHECK_INTERVAL_SECONDS}s)"
  trap 'rm -f "$SUP_PID_FILE"; log "supervisor finalizado"; exit 0' INT TERM

  local checks=0
  while true; do
    if ! is_ciclo_running; then
      log "ciclo_horario não encontrado; iniciando novamente"
      start_ciclo
      sleep 3
      if ! is_ciclo_running; then
        log "falha ao iniciar ciclo_horario; tentará novamente no próximo ciclo"
      fi
    fi

    checks=$((checks + 1))
    if (( checks % 30 == 0 )); then
      log "heartbeat: supervisor ativo e monitorando"
    fi

    sleep "$CHECK_INTERVAL_SECONDS"
  done
}

start_supervisor() {
  if is_supervisor_running; then
    echo "Supervisor já está rodando (pid=$(cat "$SUP_PID_FILE"))."
    return 0
  fi

  nohup bash "$ROOT/supervisor_noturno.sh" run >> "$LOG" 2>&1 &
  local sup_pid=$!
  echo "$sup_pid" > "$SUP_PID_FILE"
  echo "Supervisor iniciado (pid=$sup_pid)."
}

stop_supervisor() {
  if ! is_supervisor_running; then
    rm -f "$SUP_PID_FILE"
    echo "Supervisor já está parado."
    return 0
  fi

  local pid
  pid="$(cat "$SUP_PID_FILE")"
  kill "$pid" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi

  rm -f "$SUP_PID_FILE"
  echo "Supervisor parado."
}

status_supervisor() {
  if is_supervisor_running; then
    echo "Supervisor: RODANDO (pid=$(cat "$SUP_PID_FILE"))"
  else
    echo "Supervisor: PARADO"
  fi

  if is_ciclo_running; then
    echo "ciclo_horario: RODANDO"
  else
    echo "ciclo_horario: PARADO"
  fi
}

usage() {
  echo "Uso:"
  echo "  bash supervisor_noturno.sh start"
  echo "  bash supervisor_noturno.sh stop"
  echo "  bash supervisor_noturno.sh restart"
  echo "  bash supervisor_noturno.sh status"
  echo "  CHECK_INTERVAL_SECONDS=60 bash supervisor_noturno.sh start"
}

case "${1:-}" in
  start)
    start_supervisor
    ;;
  stop)
    stop_supervisor
    ;;
  restart)
    stop_supervisor
    start_supervisor
    ;;
  status)
    status_supervisor
    ;;
  run)
    run_supervisor
    ;;
  *)
    usage
    exit 1
    ;;
esac
