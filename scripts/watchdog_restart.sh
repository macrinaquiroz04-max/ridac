#!/usr/bin/env bash
# Watchdog para sistemaocr
# Monitorea el endpoint /health y los logs de login/auth para reiniciar servicios

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
WATCHDOG_LOG="$LOG_DIR/watchdog.log"
LOGIN_ERRORS_DIR="$LOG_DIR/login_errors"
AUTH_ERRORS_DIR="$LOG_DIR/auth_errors"

# Configuración
HEALTH_URL="http://localhost:8000/health"
CHECK_INTERVAL=30            # segundos
ERROR_THRESHOLD=3            # número de fallos antes de reiniciar
ERROR_WINDOW_MIN=1           # minutos para contar errores en login logs
RESTART_SERVICES=(backend)   # servicios a reiniciar (docker compose names)
DOCKER_COMPOSE_CMD="docker compose"

timestamp(){ date +"%Y-%m-%dT%H:%M:%S"; }
log(){ echo "[$(timestamp)] $*" | tee -a "$WATCHDOG_LOG"; }

# mantiene contador en /tmp
FAIL_COUNT_FILE="/tmp/sistemaocr_watchdog_fail_count"
if [ ! -f "$FAIL_COUNT_FILE" ]; then echo 0 > "$FAIL_COUNT_FILE"; fi

# Contador de archivos de error leídos
LAST_LOGIN_COUNT_FILE="/tmp/sistemaocr_watchdog_last_login_count"
if [ ! -f "$LAST_LOGIN_COUNT_FILE" ]; then echo 0 > "$LAST_LOGIN_COUNT_FILE"; fi

log "Iniciando watchdog. Health: $HEALTH_URL. Intervalo: ${CHECK_INTERVAL}s"

while true; do
  # 1) Check health endpoint
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" || echo "000")
  if [ "$http_code" != "200" ]; then
    # incrementar contador
    count=$(cat "$FAIL_COUNT_FILE")
    count=$((count+1))
    echo "$count" > "$FAIL_COUNT_FILE"
    log "Health check fallido (HTTP $http_code). contador=$count"
  else
    # resetear contador si está bien
    echo 0 > "$FAIL_COUNT_FILE"
  fi

  # 2) Check login errors new files in last ERROR_WINDOW_MIN minutes
  if [ -d "$LOGIN_ERRORS_DIR" ]; then
    # contar archivos creados en ventana
    new_errors=$(find "$LOGIN_ERRORS_DIR" -type f -mmin -$ERROR_WINDOW_MIN | wc -l)
    last_count=$(cat "$LAST_LOGIN_COUNT_FILE")
    if [ "$new_errors" -gt "$last_count" ]; then
      diff=$((new_errors-last_count))
      log "Nuevos errores de login detectados: +$diff (total ventana=$new_errors)"
      # incrementar contador proporcionalmente
      count=$(cat "$FAIL_COUNT_FILE")
      count=$((count + diff))
      echo "$count" > "$FAIL_COUNT_FILE"
    fi
    echo "$new_errors" > "$LAST_LOGIN_COUNT_FILE"
  fi

  # 3) Si contador supera umbral -> reiniciar servicios
  count=$(cat "$FAIL_COUNT_FILE")
  if [ "$count" -ge "$ERROR_THRESHOLD" ]; then
    log "Contador de fallos ($count) >= umbral ($ERROR_THRESHOLD). Intentando reiniciar servicios: ${RESTART_SERVICES[*]}"

    # Registrar acción
    ACTION_LOG="$LOG_DIR/watchdog_actions.log"
    echo "$(timestamp) - Reinicio por watchdog - contador=$count" >> "$ACTION_LOG"

    # Ejecutar docker compose restart para cada servicio
    for svc in "${RESTART_SERVICES[@]}"; do
      log "Reiniciando servicio: $svc"
      # Ejecutar en el directorio del repo
      (cd "$ROOT_DIR" && $DOCKER_COMPOSE_CMD restart "$svc" ) >> "$ACTION_LOG" 2>&1 || log "Fallo al reiniciar $svc"
    done

    # Después de reiniciar, esperar unos segundos y resetear contador
    sleep 8
    echo 0 > "$FAIL_COUNT_FILE"
    log "Reinicio ejecutado. contador reseteado. Esperando al siguiente chequeo."
  fi

  sleep "$CHECK_INTERVAL"
done
