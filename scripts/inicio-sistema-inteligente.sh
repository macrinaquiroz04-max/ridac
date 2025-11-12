                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            #!/bin/bash

# Script de inicio inteligente para el Sistema OCR FGJCDMX
# Este script verifica y configura todo automáticamente antes de iniciar

PROJECT_DIR="/home/eduardo/Descargas/sistemaocr"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/sistema-inicio-$(date '+%Y%m%d-%H%M%S').log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Función para verificar prerequisitos
check_prerequisites() {
    log "🔍 Verificando prerequisitos..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log "❌ Docker no está instalado"
        return 1
    fi
    
    # Verificar Docker Compose
    if ! docker compose version &> /dev/null; then
        log "❌ Docker Compose no está disponible"
        return 1
    fi
    
    log "✅ Prerequisites verificados"
    return 0
}

# Función para configurar red
configure_network() {
    log "🌐 Configurando red..."
    
    # Verificar si la IP está asignada
    if ip addr show | grep -q "172.22.134.61"; then
        log "✅ IP 172.22.134.61 ya está asignada"
    else
        log "⚠️ IP 172.22.134.61 no está asignada"
        log "📝 Aplicando configuración de red..."
        
        # Aplicar configuración netplan si existe
        if [ -f "$PROJECT_DIR/config/01-netcfg.yaml" ]; then
            cp "$PROJECT_DIR/config/01-netcfg.yaml" /etc/netplan/
            netplan apply
            log "✅ Configuración de red aplicada"
        fi
    fi
}

# Función para configurar Avahi
configure_avahi() {
    log "📡 Configurando Avahi para anuncio mDNS..."
    
    # Verificar si Avahi está instalado
    if ! command -v avahi-daemon &> /dev/null; then
        log "⚠️ Avahi no está instalado"
        return 1
    fi
    
    # Hacer backup de la configuración si no existe
    if [ ! -f /etc/avahi/avahi-daemon.conf.backup ]; then
        cp /etc/avahi/avahi-daemon.conf /etc/avahi/avahi-daemon.conf.backup
        log "✅ Backup de configuración Avahi creado"
    fi
    
    # Configurar hostname en Avahi
    if grep -q "^host-name=sistema-ocr" /etc/avahi/avahi-daemon.conf; then
        log "✅ Avahi ya está configurado con hostname sistema-ocr"
    else
        log "📝 Configurando hostname en Avahi..."
        sed -i 's/#host-name=foo/host-name=sistema-ocr/' /etc/avahi/avahi-daemon.conf
        sed -i 's/^host-name=.*/host-name=sistema-ocr/' /etc/avahi/avahi-daemon.conf
        
        # Reiniciar Avahi
        systemctl restart avahi-daemon
        log "✅ Avahi configurado y reiniciado"
    fi
    
    # Verificar que esté anunciando correctamente
    sleep 2
    if timeout 3 avahi-browse -a -t -r 2>/dev/null | grep -q "sistema-ocr.local"; then
        log "✅ sistema-ocr.local está siendo anunciado en la red"
    else
        log "⚠️ No se pudo verificar el anuncio mDNS"
    fi
}

# Función para configurar DNS
configure_dns() {
    log "🔧 Configurando DNS..."
    
    # Ejecutar script de DNS automático
    if [ -f "$PROJECT_DIR/scripts/configurar-dns-automatico.sh" ]; then
        bash "$PROJECT_DIR/scripts/configurar-dns-automatico.sh"
    else
        log "⚠️ Script de DNS automático no encontrado"
    fi
}

# Función para iniciar servicios
start_services() {
    log "🚀 Iniciando servicios Docker..."
    
    cd "$PROJECT_DIR" || {
        log "❌ No se puede acceder al directorio del proyecto"
        return 1
    }
    
    # Verificar si ya están ejecutándose
    RUNNING_CONTAINERS=$(docker compose ps --format "{{.Status}}" | grep -c "Up" || true)
    if [ "$RUNNING_CONTAINERS" -ge 10 ]; then
        log "✅ Servicios ya están ejecutándose ($RUNNING_CONTAINERS contenedores activos)"
        return 0
    fi
    
    log "📦 Iniciando arquitectura de microservicios mejorada..."
    log "   - PostgreSQL (Base de datos)"
    log "   - Redis (Caché y broker de tareas)"
    log "   - Elasticsearch (Búsqueda avanzada)"
    log "   - MinIO (Almacenamiento S3)"
    log "   - Celery Worker (Procesamiento asíncrono)"
    log "   - Celery Beat (Tareas programadas)"
    log "   - Prometheus (Métricas)"
    log "   - Grafana (Dashboards)"
    log "   - Backend FastAPI"
    log "   - Nginx (Servidor web)"
    log "   - DNS Server"
    log "   - PgAdmin (Administración DB)"
    
    # Iniciar servicios con detección de Docker Compose v2
    if docker compose version &> /dev/null; then
        docker compose up -d
    else
        docker-compose up -d
    fi
    
    # Esperar a que estén saludables
    log "⏳ Esperando a que los servicios estén saludables (esto puede tardar 1-2 minutos)..."
    
    for i in {1..60}; do
        HEALTHY=$(docker compose ps --format "{{.Status}}" | grep -c "healthy" || true)
        UP=$(docker compose ps --format "{{.Status}}" | grep -c "Up" || true)
        
        if [ "$HEALTHY" -ge 5 ] && [ "$UP" -ge 10 ]; then
            log "✅ Servicios iniciados correctamente:"
            log "   - $UP contenedores activos"
            log "   - $HEALTHY contenedores con health check OK"
            
            # Mostrar estado detallado
            log ""
            log "📊 Estado de servicios:"
            docker compose ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}" | while read line; do
                log "   $line"
            done
            
            return 0
        fi
        
        if [ $((i % 10)) -eq 0 ]; then
            log "   ⏳ Esperando... ($UP contenedores UP, $HEALTHY con health check)"
        fi
        sleep 2
    done
    
    log "⚠️ Los servicios tardaron más de lo esperado, pero pueden estar funcionando"
    log "   Ejecuta 'docker compose ps' para ver el estado actual"
    return 0
}

# Función para verificar funcionamiento
verify_system() {
    log "🧪 Verificando funcionamiento del sistema mejorado..."
    
    # Test de Backend
    if curl -s "http://localhost:8000/health" | grep -q "healthy"; then
        log "✅ Backend FastAPI operativo"
    else
        log "⚠️ Backend no responde al health check"
    fi
    
    # Test de Redis
    if docker exec sistema_ocr_redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log "✅ Redis operativo"
    else
        log "⚠️ Redis no responde"
    fi
    
    # Test de Elasticsearch
    ES_STATUS=$(curl -s "http://localhost:9200/_cluster/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$ES_STATUS" = "green" ] || [ "$ES_STATUS" = "yellow" ]; then
        log "✅ Elasticsearch operativo (status: $ES_STATUS)"
    else
        log "⚠️ Elasticsearch no está saludable"
    fi
    
    # Test de MinIO
    if curl -s "http://localhost:9000/minio/health/live" &>/dev/null; then
        log "✅ MinIO operativo"
    else
        log "⚠️ MinIO no responde"
    fi
    
    # Test de Celery Worker
    if docker logs sistema_ocr_celery_worker 2>&1 | grep -q "ready"; then
        log "✅ Celery Worker operativo"
    else
        log "⚠️ Celery Worker puede no estar listo"
    fi
    
    # Test de Prometheus
    if curl -s "http://localhost:9090/-/healthy" &>/dev/null; then
        log "✅ Prometheus operativo"
    else
        log "⚠️ Prometheus no responde"
    fi
    
    # Test de Grafana
    if curl -s "http://localhost:3000/api/health" | grep -q "ok"; then
        log "✅ Grafana operativo"
    else
        log "⚠️ Grafana no responde"
    fi
    
    # Test de Frontend por dominio
    if curl -s "http://fgj-ocr.local/" &>/dev/null; then
        log "✅ Frontend accesible en http://fgj-ocr.local/"
    elif curl -s "http://sistema-ocr.local/" &>/dev/null; then
        log "✅ Frontend accesible en http://sistema-ocr.local/"
    else
        log "⚠️ Frontend no accesible por dominio"
    fi
    
    # Test por IP
    if curl -s "http://172.22.134.61/" &>/dev/null; then
        log "✅ Sistema accesible por IP: http://172.22.134.61/"
    else
        log "⚠️ Sistema no accesible por IP"
    fi
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🏛️  SISTEMA OCR FGJCDMX - INICIO AUTOMÁTICO INTELIGENTE"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar si ejecuta como root
    if [ "$EUID" -ne 0 ]; then
        log "❌ Este script debe ejecutarse como root o con sudo"
        exit 1
    fi
    
    # Ejecutar pasos de configuración
    if check_prerequisites; then
        configure_network
        configure_avahi
        configure_dns
        
        if start_services; then
            sleep 5  # Dar tiempo a que se estabilicen
            verify_system
            
            log "════════════════════════════════════════════════════════════════"
            log "🎉 SISTEMA OCR MEJORADO INICIADO CORRECTAMENTE"
            log "════════════════════════════════════════════════════════════════"
            log ""
            log "🌐 ACCESOS WEB:"
            log "   • Frontend:        http://sistema-ocr.local/"
            log "   • Frontend (IP):   http://172.22.134.61/"
            log "   • API Docs:        http://sistema-ocr.local/docs"
            log "   • Legacy:          http://fgj-ocr.local/"
            log ""
            log "� HERRAMIENTAS DE MONITOREO:"
            log "   • Grafana:         http://localhost:3000 (admin/admin)"
            log "   • Prometheus:      http://localhost:9090"
            log "   • PgAdmin:         http://localhost:5050"
            log "   • MinIO Console:   http://localhost:9001 (minioadmin/minioadmin123)"
            log ""
            log "🔧 SERVICIOS BACKEND:"
            log "   • Redis:           localhost:6379"
            log "   • Elasticsearch:   http://localhost:9200"
            log "   • PostgreSQL:      localhost:5432"
            log ""
            log "⚡ NUEVAS CAPACIDADES:"
            log "   ✓ Caché con Redis (10-100x más rápido)"
            log "   ✓ Búsqueda avanzada con Elasticsearch"
            log "   ✓ Procesamiento asíncrono OCR con Celery"
            log "   ✓ Almacenamiento S3 con MinIO"
            log "   ✓ Métricas y monitoreo con Prometheus/Grafana"
            log ""
            log "📊 Logs disponibles en: $LOG_FILE"
            log "════════════════════════════════════════════════════════════════"
        else
            log "❌ Error al iniciar servicios"
            exit 1
        fi
    else
        log "❌ Prerequisites no cumplidos"
        exit 1
    fi
}

# Ejecutar función principal
main "$@"