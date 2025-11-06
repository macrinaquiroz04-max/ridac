#!/bin/bash

# Script de monitoreo y auto-recuperación del sistema OCR
# Verifica que todos los servicios estén funcionando y los reinicia si es necesario
# Se ejecuta automáticamente cada minuto via cron

PROJECT_DIR="/home/eduardo-lozada/proyectos/sistemaocr"
LOG_FILE="/tmp/sistema-ocr-monitor.log"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Verificar Docker
if ! docker ps > /dev/null 2>&1; then
    log "❌ Docker no está respondiendo. Intentando reiniciar servicio..."
    sudo systemctl restart docker
    sleep 10
fi

cd "$PROJECT_DIR" || exit 1

# Verificar cada servicio crítico
SERVICES=("sistema_ocr_backend" "sistema_ocr_db" "sistema_ocr_nginx")

for service in "${SERVICES[@]}"; do
    # Verificar si el contenedor está corriendo
    if ! docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        log "⚠️  Servicio $service no está corriendo. Reiniciando..."
        docker start "$service" >> "$LOG_FILE" 2>&1
        sleep 5
    fi
    
    # Verificar health status
    health=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null)
    if [[ "$health" == "unhealthy" ]]; then
        log "⚠️  Servicio $service unhealthy. Reiniciando..."
        docker restart "$service" >> "$LOG_FILE" 2>&1
        sleep 10
    fi
done

# Verificar que el sistema web responda
if ! curl -s -f http://sistema-ocr.local/health > /dev/null 2>&1; then
    log "⚠️  Sistema no responde en HTTP. Reiniciando nginx y backend..."
    docker restart sistema_ocr_nginx sistema_ocr_backend >> "$LOG_FILE" 2>&1
    sleep 10
fi

# Limpiar log si es muy grande (>10MB)
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt 10485760 ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp"
    mv "${LOG_FILE}.tmp" "$LOG_FILE"
    log "🧹 Log limpiado (demasiado grande)"
fi

# Verificar uso de disco de logs
LOGS_SIZE=$(docker exec sistema_ocr_backend du -sm /app/logs 2>/dev/null | awk '{print $1}')
if [ "$LOGS_SIZE" -gt 200 ]; then
    log "⚠️  Logs ocupan ${LOGS_SIZE}MB. Limpiando logs antiguos..."
    docker exec sistema_ocr_backend python -c "from app.utils.error_logger import cleanup_old_logs; cleanup_old_logs(days=3)" >> "$LOG_FILE" 2>&1
fi

# Todo OK
log "✅ Sistema operando normalmente"
