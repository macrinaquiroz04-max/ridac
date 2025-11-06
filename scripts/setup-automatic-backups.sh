#!/bin/bash

# Script para configurar backups automáticos del Sistema OCR FGJCDMX
# Configura cron jobs para backups programados

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup-database.sh"
CRON_FILE="/etc/cron.d/sistema-ocr-backup"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Función para configurar backup diario
setup_daily_backup() {
    log "📅 Configurando backup automático diario..."
    
    # Crear archivo de cron
    cat > "$CRON_FILE" << EOF
# Sistema OCR FGJCDMX - Backup Automático Diario
# Ejecuta backup todos los días a las 2:00 AM
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 2 * * * root $BACKUP_SCRIPT >> /var/log/sistema-ocr-backup-cron.log 2>&1
EOF
    
    # Asegurar permisos correctos
    chmod 644 "$CRON_FILE"
    
    # Reiniciar servicio cron
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null
    
    log "✅ Backup diario configurado para las 2:00 AM"
}

# Función para configurar backup semanal
setup_weekly_backup() {
    log "📅 Configurando backup automático semanal..."
    
    # Crear archivo de cron
    cat > "$CRON_FILE" << EOF
# Sistema OCR FGJCDMX - Backup Automático Semanal
# Ejecuta backup todos los domingos a las 1:00 AM
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 1 * * 0 root $BACKUP_SCRIPT >> /var/log/sistema-ocr-backup-cron.log 2>&1
EOF
    
    # Asegurar permisos correctos
    chmod 644 "$CRON_FILE"
    
    # Reiniciar servicio cron
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null
    
    log "✅ Backup semanal configurado para domingos a la 1:00 AM"
}

# Función para configurar backup personalizado
setup_custom_backup() {
    local schedule="$1"
    
    log "📅 Configurando backup automático personalizado..."
    
    # Validar formato de cron
    if ! [[ "$schedule" =~ ^[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+[[:space:]]+[0-9\*\,\-\/]+$ ]]; then
        log "❌ Formato de horario inválido: $schedule"
        log "💡 Formato esperado: 'minuto hora día mes día_semana'"
        log "💡 Ejemplo: '30 3 * * *' (todos los días a las 3:30 AM)"
        return 1
    fi
    
    # Crear archivo de cron
    cat > "$CRON_FILE" << EOF
# Sistema OCR FGJCDMX - Backup Automático Personalizado
# Programado por el usuario
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

$schedule root $BACKUP_SCRIPT >> /var/log/sistema-ocr-backup-cron.log 2>&1
EOF
    
    # Asegurar permisos correctos
    chmod 644 "$CRON_FILE"
    
    # Reiniciar servicio cron
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null
    
    log "✅ Backup personalizado configurado: $schedule"
}

# Función para desactivar backups automáticos
disable_automatic_backup() {
    log "🚫 Desactivando backups automáticos..."
    
    if [ -f "$CRON_FILE" ]; then
        rm -f "$CRON_FILE"
        systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null
        log "✅ Backups automáticos desactivados"
    else
        log "📋 No hay backups automáticos configurados"
    fi
}

# Función para mostrar estado
show_status() {
    log "📊 Estado de backups automáticos:"
    
    if [ -f "$CRON_FILE" ]; then
        echo "✅ Backup automático ACTIVADO"
        echo ""
        echo "Configuración actual:"
        cat "$CRON_FILE" | grep -v "^#" | grep -v "^$"
        echo ""
        
        # Mostrar próxima ejecución
        log "📅 Próximas ejecuciones programadas:"
        # Mostrar las próximas 3 ejecuciones
        grep -v "^#" "$CRON_FILE" | grep -v "^$" | while read line; do
            if [[ "$line" =~ ^[0-9\*] ]]; then
                echo "  • Programado según: $(echo "$line" | cut -d' ' -f1-5)"
            fi
        done
    else
        echo "❌ Backup automático DESACTIVADO"
        echo "💡 Use las opciones --daily, --weekly o --custom para activar"
    fi
    
    echo ""
    log "📂 Logs de backups automáticos:"
    if [ -f "/var/log/sistema-ocr-backup-cron.log" ]; then
        echo "  • /var/log/sistema-ocr-backup-cron.log"
        echo "  • Últimas líneas:"
        tail -5 /var/log/sistema-ocr-backup-cron.log 2>/dev/null | sed 's/^/    /'
    else
        echo "  • No hay logs disponibles"
    fi
}

# Función para hacer backup manual
run_manual_backup() {
    log "🔄 Ejecutando backup manual..."
    
    if [ -x "$BACKUP_SCRIPT" ]; then
        "$BACKUP_SCRIPT"
    else
        log "❌ Script de backup no encontrado o no ejecutable: $BACKUP_SCRIPT"
        return 1
    fi
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🏛️  SISTEMA OCR FGJCDMX - CONFIGURACIÓN DE BACKUPS AUTOMÁTICOS"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar que ejecuta como root
    if [ "$EUID" -ne 0 ]; then
        log "❌ Este script debe ejecutarse como root o con sudo"
        log "💡 Uso: sudo $0 [opciones]"
        exit 1
    fi
    
    # Verificar que existe el script de backup
    if [ ! -x "$BACKUP_SCRIPT" ]; then
        log "❌ Script de backup no encontrado: $BACKUP_SCRIPT"
        log "💡 Ejecute primero: chmod +x $BACKUP_SCRIPT"
        exit 1
    fi
    
    case "$1" in
        --daily)
            setup_daily_backup
            ;;
        --weekly)
            setup_weekly_backup
            ;;
        --custom)
            if [ -z "$2" ]; then
                log "❌ Debe especificar el horario para backup personalizado"
                log "💡 Ejemplo: sudo $0 --custom '30 3 * * *'"
                exit 1
            fi
            setup_custom_backup "$2"
            ;;
        --disable)
            disable_automatic_backup
            ;;
        --status)
            show_status
            ;;
        --run)
            run_manual_backup
            ;;
        --help|-h|"")
            echo "Sistema OCR FGJCDMX - Configuración de Backups Automáticos"
            echo ""
            echo "Uso: sudo $0 [opción]"
            echo ""
            echo "Opciones:"
            echo "  --daily              Activar backup diario (2:00 AM)"
            echo "  --weekly             Activar backup semanal (domingos 1:00 AM)"
            echo "  --custom 'horario'   Activar backup personalizado"
            echo "  --disable            Desactivar backups automáticos"
            echo "  --status             Mostrar estado actual"
            echo "  --run                Ejecutar backup manual"
            echo "  --help, -h           Mostrar esta ayuda"
            echo ""
            echo "Formato de horario personalizado (cron):"
            echo "  'minuto hora día mes día_semana'"
            echo ""
            echo "Ejemplos:"
            echo "  sudo $0 --daily                    # Backup diario a las 2:00 AM"
            echo "  sudo $0 --weekly                   # Backup semanal domingos 1:00 AM"
            echo "  sudo $0 --custom '0 4 * * *'       # Todos los días a las 4:00 AM"
            echo "  sudo $0 --custom '30 2 * * 1,3,5'  # Lunes, miércoles y viernes a las 2:30 AM"
            echo "  sudo $0 --status                   # Ver configuración actual"
            echo ""
            ;;
        *)
            log "❌ Opción no reconocida: $1"
            log "💡 Use --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
    
    log "════════════════════════════════════════════════════════════════"
    log "✅ CONFIGURACIÓN COMPLETADA"
    log "🔗 Sistema disponible en: http://fgj-ocr.local/"
    log "════════════════════════════════════════════════════════════════"
}

# Ejecutar función principal
main "$@"