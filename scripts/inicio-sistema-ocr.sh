#!/bin/bash

# Script de inicio automático del Sistema OCR FGJCDMX
# Fecha: $(date +"%Y-%m-%d")

set -e

LOG_FILE="/var/log/sistema-ocr-startup.log"
PROJECT_DIR="/home/vboxuser/Downloads/FJ1"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== INICIANDO SISTEMA OCR FGJCDMX ==="

# Verificar y configurar IP de red si es necesario
if ! ip addr show enp0s8 | grep -q "172.22.134.61"; then
    log "Configurando IP 172.22.134.61 en enp0s8..."
    ip addr add 172.22.134.61/24 dev enp0s8 || log "IP ya configurada o error al configurar"
else
    log "IP 172.22.134.61 ya está configurada"
fi

# Verificar que Docker esté corriendo
if ! systemctl is-active --quiet docker; then
    log "Iniciando servicio Docker..."
    systemctl start docker
    sleep 5
fi

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR" || {
    log "ERROR: No se puede acceder al directorio $PROJECT_DIR"
    exit 1
}

# Verificar archivos necesarios
for file in "docker-compose.yml" "nginx.conf"; do
    if [ ! -f "$file" ]; then
        log "ERROR: Archivo necesario no encontrado: $file"
        exit 1
    fi
done

# Detener contenedores si están corriendo
log "Deteniendo contenedores existentes..."
docker compose down --timeout 30 || log "No había contenedores corriendo"

# Limpiar imágenes huérfanas y contenedores parados
log "Limpiando recursos Docker..."
docker system prune -f || true

# Iniciar todos los servicios
log "Iniciando servicios del Sistema OCR..."
docker compose up -d postgres backend nginx dns-server

# Esperar a que los servicios estén listos
log "Esperando a que los servicios estén listos..."
sleep 20

# Verificar estado de los servicios
log "Verificando estado de los servicios..."
docker compose ps

# Verificar conectividad
log "Verificando conectividad..."
for i in {1..10}; do
    if curl -s http://localhost/health >/dev/null; then
        log "✅ Sistema OCR funcionando correctamente"
        log "🌐 Acceso disponible en: http://fgj-ocr.local"
        log "🔑 Usuario: eduardo | Contraseña: lalo1998c33"
        break
    else
        log "Intento $i/10: Esperando que el sistema esté listo..."
        sleep 10
    fi
done

# Verificar acceso al dominio
if curl -s http://fgj-ocr.local >/dev/null; then
    log "✅ Dominio fgj-ocr.local accesible"
else
    log "⚠️  Advertencia: El dominio fgj-ocr.local no responde"
fi

log "=== INICIO DEL SISTEMA OCR COMPLETADO ==="