#!/bin/bash

# Script de backup automatizado para Sistema OCR FGJCDMX
# Crea backups completos de la base de datos PostgreSQL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="/var/log/sistema-ocr-backup.log"

# Función de logging
log() {
    if [ "$EUID" -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    fi
}

# Función para verificar prerequisitos
check_prerequisites() {
    log "🔍 Verificando prerequisitos para backup..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log "❌ Docker no está instalado"
        return 1
    fi
    
    # Verificar que el contenedor de DB está corriendo
    if ! docker ps | grep -q "sistema_ocr_db"; then
        log "❌ El contenedor de base de datos no está ejecutándose"
        return 1
    fi
    
    # Crear directorio de backups si no existe
    mkdir -p "$BACKUP_DIR"
    
    log "✅ Prerequisites verificados"
    return 0
}

# Función para crear backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/sistema_ocr_backup_${timestamp}.sql"
    
    log "💾 Iniciando backup de base de datos..."
    log "📁 Archivo: ${backup_file}"
    
    # Crear backup usando pg_dump
    if docker exec sistema_ocr_db pg_dump -U postgres -d sistema_ocr > "$backup_file" 2>/dev/null; then
        local size=$(du -h "$backup_file" | cut -f1)
        log "✅ Backup creado exitosamente"
        log "📊 Tamaño: ${size}"
        log "📍 Ubicación: ${backup_file}"
        
        # Verificar integridad del backup
        if [ -s "$backup_file" ]; then
            log "✅ Backup verificado - archivo no está vacío"
        else
            log "⚠️ Advertencia: El archivo de backup parece estar vacío"
        fi
        
        return 0
    else
        log "❌ Error al crear backup"
        rm -f "$backup_file" 2>/dev/null
        return 1
    fi
}

# Función para listar backups existentes
list_backups() {
    log "📋 Backups disponibles:"
    
    if [ "$(ls -A "$BACKUP_DIR"/*.sql 2>/dev/null)" ]; then
        echo "══════════════════════════════════════════════════════════════"
        printf "%-35s %-10s %-20s\n" "ARCHIVO" "TAMAÑO" "FECHA"
        echo "══════════════════════════════════════════════════════════════"
        
        for backup in "$BACKUP_DIR"/*.sql; do
            if [ -f "$backup" ]; then
                filename=$(basename "$backup")
                size=$(du -h "$backup" | cut -f1)
                date=$(stat -c %y "$backup" | cut -d'.' -f1)
                printf "%-35s %-10s %-20s\n" "$filename" "$size" "$date"
            fi
        done
        echo "══════════════════════════════════════════════════════════════"
    else
        log "📂 No hay backups disponibles"
    fi
}

# Función para limpiar backups antiguos (mantener últimos 10)
cleanup_old_backups() {
    log "🧹 Limpiando backups antiguos..."
    
    local backup_count=$(ls -1 "$BACKUP_DIR"/*.sql 2>/dev/null | wc -l)
    
    if [ "$backup_count" -gt 10 ]; then
        log "📊 Se encontraron $backup_count backups, manteniendo los últimos 10"
        
        # Eliminar backups más antiguos (mantener últimos 10)
        ls -1t "$BACKUP_DIR"/*.sql | tail -n +11 | while read -r old_backup; do
            log "🗑️ Eliminando backup antiguo: $(basename "$old_backup")"
            rm -f "$old_backup"
        done
        
        log "✅ Limpieza completada"
    else
        log "📊 Se encontraron $backup_count backups, no es necesario limpiar"
    fi
}

# Función para mostrar estadísticas
show_statistics() {
    log "📊 Estadísticas de backups:"
    
    local total_backups=$(ls -1 "$BACKUP_DIR"/*.sql 2>/dev/null | wc -l)
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local latest_backup=$(ls -1t "$BACKUP_DIR"/*.sql 2>/dev/null | head -1)
    
    echo "  • Total de backups: $total_backups"
    echo "  • Tamaño total: ${total_size:-0}"
    
    if [ -n "$latest_backup" ]; then
        local latest_date=$(stat -c %y "$latest_backup" | cut -d'.' -f1)
        echo "  • Último backup: $(basename "$latest_backup") ($latest_date)"
    fi
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🏛️  SISTEMA OCR FGJCDMX - BACKUP AUTOMATIZADO"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar si ejecuta como root (opcional para logs)
    if [ "$EUID" -eq 0 ]; then
        log "🔑 Ejecutando como root - acceso completo a logs"
    else
        log "👤 Ejecutando como usuario - logs limitados"
        LOG_FILE="$HOME/sistema-ocr-backup.log"
    fi
    
    # Ejecutar proceso de backup
    if check_prerequisites; then
        if create_backup; then
            cleanup_old_backups
            list_backups
            show_statistics
            
            log "════════════════════════════════════════════════════════════════"
            log "✅ PROCESO DE BACKUP COMPLETADO EXITOSAMENTE"
            log "🔗 Sistema disponible en: http://fgj-ocr.local/"
            log "📊 Logs disponibles en: $LOG_FILE"
            log "════════════════════════════════════════════════════════════════"
        else
            log "❌ PROCESO DE BACKUP FALLÓ"
            exit 1
        fi
    else
        log "❌ Prerequisites no cumplidos"
        exit 1
    fi
}

# Mostrar ayuda si se solicita
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Sistema OCR FGJCDMX - Script de Backup"
    echo ""
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  --help, -h     Mostrar esta ayuda"
    echo "  --list, -l     Solo listar backups existentes"
    echo "  --stats, -s    Mostrar estadísticas de backups"
    echo ""
    echo "Funcionalidades:"
    echo "  • Backup completo de base de datos PostgreSQL"
    echo "  • Limpieza automática de backups antiguos"
    echo "  • Verificación de integridad"
    echo "  • Logs detallados de operaciones"
    echo ""
    exit 0
fi

# Opciones especiales
if [[ "$1" == "--list" || "$1" == "-l" ]]; then
    mkdir -p "$BACKUP_DIR"
    list_backups
    exit 0
fi

if [[ "$1" == "--stats" || "$1" == "-s" ]]; then
    mkdir -p "$BACKUP_DIR"
    show_statistics
    exit 0
fi

# Ejecutar función principal
main "$@"