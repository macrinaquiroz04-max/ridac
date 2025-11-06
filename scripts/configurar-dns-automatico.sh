#!/bin/bash

# Script para configurar automáticamente el DNS del sistema OCR
# Este script asegura que sistema-ocr.local y fgj-ocr.local siempre resuelvan correctamente

echo "🔧 Configurando DNS automático para el Sistema OCR FGJCDMX..."

# Variables
DOMAIN_PRIMARY="sistema-ocr.local"
DOMAIN_LEGACY="fgj-ocr.local"
IP="172.22.134.61"
HOSTS_FILE="/etc/hosts"

# Función para verificar si la entrada ya existe
check_hosts_entry() {
    local domain=$1
    if grep -q "$IP.*$domain" "$HOSTS_FILE"; then
        return 0  # Existe
    else
        return 1  # No existe
    fi
}

# Función para agregar entrada al hosts
add_hosts_entry() {
    local domain=$1
    echo "📝 Agregando entrada DNS a $HOSTS_FILE: $domain..."
    
    # Hacer backup si no existe
    if [ ! -f "${HOSTS_FILE}.backup-ocr" ]; then
        cp "$HOSTS_FILE" "${HOSTS_FILE}.backup-ocr"
        echo "💾 Backup creado: ${HOSTS_FILE}.backup-ocr"
    fi
    
    # Agregar entrada
    echo "$IP    $domain" >> "$HOSTS_FILE"
    echo "✅ Entrada agregada: $IP    $domain"
}

# Función para verificar resolución DNS
test_dns_resolution() {
    local domain=$1
    echo "🔍 Verificando resolución DNS para $domain..."
    
    if ping -c 1 -W 2 "$domain" > /dev/null 2>&1; then
        echo "✅ DNS funciona correctamente: $domain resuelve a la IP correcta"
        return 0
    else
        echo "❌ DNS no funciona: $domain no resuelve"
        return 1
    fi
}

# Función para verificar servicios Docker
check_docker_services() {
    echo "🐳 Verificando servicios Docker..."
    
    cd "$(dirname "$0")/.." || exit 1
    
    if docker compose ps | grep -q "sistema_ocr.*Up"; then
        echo "✅ Servicios Docker están ejecutándose"
        return 0
    else
        echo "⚠️ Algunos servicios Docker no están ejecutándose"
        return 1
    fi
}

# Función principal
main() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🏛️  SISTEMA OCR FGJCDMX - CONFIGURACIÓN AUTOMÁTICA DNS"
    echo "════════════════════════════════════════════════════════════════"
    
    # Verificar si ejecuta como root/sudo
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Este script debe ejecutarse como root o con sudo"
        echo "   Uso: sudo $0"
        exit 1
    fi
    
    # Verificar y agregar entrada hosts para dominio principal
    if check_hosts_entry "$DOMAIN_PRIMARY"; then
        echo "✅ Entrada DNS principal ya existe: $DOMAIN_PRIMARY"
    else
        echo "📝 Entrada DNS principal no encontrada, agregando..."
        add_hosts_entry "$DOMAIN_PRIMARY"
    fi
    
    # Verificar y agregar entrada hosts para dominio legacy
    if check_hosts_entry "$DOMAIN_LEGACY"; then
        echo "✅ Entrada DNS legacy ya existe: $DOMAIN_LEGACY"
    else
        echo "📝 Entrada DNS legacy no encontrada, agregando..."
        add_hosts_entry "$DOMAIN_LEGACY"
    fi
    
    # Verificar resolución DNS para ambos dominios
    dns_ok=0
    if test_dns_resolution "$DOMAIN_PRIMARY"; then
        ((dns_ok++))
    fi
    
    if test_dns_resolution "$DOMAIN_LEGACY"; then
        ((dns_ok++))
    fi
    
    if [ $dns_ok -eq 2 ]; then
        echo "🎯 DNS configurado correctamente para ambos dominios"
    else
        echo "⚠️ Hay problemas con la resolución DNS"
        echo "   Esto podría deberse a caché DNS del sistema"
        echo "   Intentando limpiar caché..."
        
        # Limpiar caché DNS
        systemctl restart systemd-resolved 2>/dev/null || true
        sleep 2
        
        # Verificar nuevamente
        test_dns_resolution "$DOMAIN_PRIMARY"
        test_dns_resolution "$DOMAIN_LEGACY"
    fi
    
    # Verificar servicios Docker
    check_docker_services
    
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ Configuración DNS completada"
    echo "🌐 Dominio principal: http://$DOMAIN_PRIMARY"
    echo "🔄 Dominio legacy: http://$DOMAIN_LEGACY"
    echo "🔗 También disponible por IP: http://$IP"
    echo "════════════════════════════════════════════════════════════════"
}

# Ejecutar función principal
main "$@"