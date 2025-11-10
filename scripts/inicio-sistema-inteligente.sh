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
    if docker compose ps | grep -q "Up.*healthy"; then
        log "✅ Servicios ya están ejecutándose y saludables"
        return 0
    fi
    
    # Iniciar servicios
    docker compose up -d
    
    # Esperar a que estén saludables
    log "⏳ Esperando a que los servicios estén saludables..."
    
    for i in {1..30}; do
        if docker compose ps | grep -q "Up.*healthy"; then
            log "✅ Servicios iniciados y saludables"
            return 0
        fi
        sleep 2
    done
    
    log "⚠️ Los servicios tardaron más de lo esperado en estar saludables"
    return 1
}

# Función para verificar funcionamiento
verify_system() {
    log "🧪 Verificando funcionamiento del sistema..."
    
    # Test de conectividad local
    if curl -s "http://fgj-ocr.local/" > /dev/null; then
        log "✅ Frontend accesible en http://fgj-ocr.local/"
    else
        log "⚠️ Frontend no accesible por dominio"
    fi
    
    # Test de API
    if curl -s "http://fgj-ocr.local/api/auth/login" | grep -q "Method Not Allowed"; then
        log "✅ API accesible en http://fgj-ocr.local/api/"
    else
        log "⚠️ API no responde correctamente"
    fi
    
    # Test por IP
    if curl -s "http://172.22.134.61/" > /dev/null; then
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
            log "🎉 SISTEMA OCR INICIADO CORRECTAMENTE"
            log "🌐 Acceso por dominio: http://fgj-ocr.local/"
            log "🔗 Acceso por IP: http://172.22.134.61/"
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