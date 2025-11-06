#!/bin/bash

# Script de restauración para Sistema OCR FGJCDMX
# Restaura backups de la base de datos PostgreSQL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="/var/log/sistema-ocr-restore.log"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Función para verificar prerequisitos
check_prerequisites() {
    log "🔍 Verificando prerequisitos para restauración..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log "❌ Docker no está instalado"
        return 1
    fi
    
    # Verificar que el contenedor de DB está corriendo
    if ! docker ps | grep -q "sistema_ocr_db.*Up"; then
        log "❌ El contenedor de base de datos no está ejecutándose"
        return 1
    fi
    
    # Verificar que existe el directorio de backups
    if [ ! -d "$BACKUP_DIR" ]; then
        log "❌ No existe el directorio de backups: $BACKUP_DIR"
        return 1
    fi
    
    log "✅ Prerequisites verificados"
    return 0
}

# Función para listar backups disponibles
list_available_backups() {
    log "📋 Backups disponibles para restauración:"
    
    if [ "$(ls -A "$BACKUP_DIR"/*.sql 2>/dev/null)" ]; then
        echo "══════════════════════════════════════════════════════════════"
        printf "%-5s %-35s %-10s %-20s\n" "NUM" "ARCHIVO" "TAMAÑO" "FECHA"
        echo "══════════════════════════════════════════════════════════════"
        
        local counter=1
        for backup in $(ls -1t "$BACKUP_DIR"/*.sql); do
            if [ -f "$backup" ]; then
                filename=$(basename "$backup")
                size=$(du -h "$backup" | cut -f1)
                date=$(stat -c %y "$backup" | cut -d'.' -f1)
                printf "%-5s %-35s %-10s %-20s\n" "$counter" "$filename" "$size" "$date"
                counter=$((counter + 1))
            fi
        done
        echo "══════════════════════════════════════════════════════════════"
        return 0
    else
        log "❌ No hay backups disponibles en $BACKUP_DIR"
        return 1
    fi
}

# Función para seleccionar backup
select_backup() {
    local backup_file="$1"
    
    if [ -n "$backup_file" ]; then
        # Backup especificado como parámetro
        if [ -f "$BACKUP_DIR/$backup_file" ]; then
            echo "$BACKUP_DIR/$backup_file"
            return 0
        elif [ -f "$backup_file" ]; then
            echo "$backup_file"
            return 0
        else
            log "❌ Archivo de backup no encontrado: $backup_file"
            return 1
        fi
    else
        # Selección interactiva
        list_available_backups || return 1
        
        echo ""
        read -p "Selecciona el número del backup a restaurar (o 'q' para salir): " selection
        
        if [[ "$selection" == "q" || "$selection" == "Q" ]]; then
            log "🚫 Restauración cancelada por el usuario"
            exit 0
        fi
        
        if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
            log "❌ Selección inválida: $selection"
            return 1
        fi
        
        local backup_files=($(ls -1t "$BACKUP_DIR"/*.sql))
        local selected_backup="${backup_files[$((selection-1))]}"
        
        if [ -f "$selected_backup" ]; then
            echo "$selected_backup"
            return 0
        else
            log "❌ Selección inválida: $selection"
            return 1
        fi
    fi
}

# Función para crear backup de seguridad antes de restaurar
create_safety_backup() {
    log "🛡️ Creando backup de seguridad antes de restaurar..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local safety_backup="$BACKUP_DIR/pre_restore_safety_backup_${timestamp}.sql"
    
    if docker exec sistema_ocr_db pg_dump -U postgres -d sistema_ocr > "$safety_backup" 2>> "$LOG_FILE"; then
        log "✅ Backup de seguridad creado: $(basename "$safety_backup")"
        return 0
    else
        log "❌ Error al crear backup de seguridad"
        return 1
    fi
}

# Función para restaurar backup
restore_backup() {
    local backup_file="$1"
    
    log "🔄 Iniciando restauración de backup..."
    log "📁 Archivo: $(basename "$backup_file")"
    
    # Verificar que el archivo existe y no está vacío
    if [ ! -s "$backup_file" ]; then
        log "❌ El archivo de backup está vacío o no existe"
        return 1
    fi
    
    # Mostrar información del backup
    local size=$(du -h "$backup_file" | cut -f1)
    local date=$(stat -c %y "$backup_file" | cut -d'.' -f1)
    log "📊 Tamaño: $size"
    log "📅 Fecha: $date"
    
    # Confirmar restauración
    echo ""
    echo "⚠️  ADVERTENCIA: Esta operación reemplazará TODOS los datos actuales"
    echo "   en la base de datos con los datos del backup seleccionado."
    echo ""
    read -p "¿Estás seguro de que quieres continuar? (escriba 'SI' para confirmar): " confirmation
    
    if [ "$confirmation" != "SI" ]; then
        log "🚫 Restauración cancelada por el usuario"
        return 1
    fi
    
    # Crear backup de seguridad
    if ! create_safety_backup; then
        log "❌ No se pudo crear backup de seguridad. Abortando restauración."
        return 1
    fi
    
    # Detener servicios temporalmente
    log "⏸️ Deteniendo servicios temporalmente..."
    cd "$PROJECT_DIR"
    docker compose stop backend
    
    # Restaurar base de datos
    log "🔄 Restaurando base de datos..."
    
    # Eliminar conexiones activas y recrear base de datos
    docker exec sistema_ocr_db psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'sistema_ocr' AND pid <> pg_backend_pid();" 2>> "$LOG_FILE"
    docker exec sistema_ocr_db psql -U postgres -c "DROP DATABASE IF EXISTS sistema_ocr;" 2>> "$LOG_FILE"
    docker exec sistema_ocr_db psql -U postgres -c "CREATE DATABASE sistema_ocr;" 2>> "$LOG_FILE"
    
    # Restaurar datos
    if docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr < "$backup_file" 2>> "$LOG_FILE"; then
        log "✅ Base de datos restaurada exitosamente"
        
        # Reiniciar servicios
        log "🚀 Reiniciando servicios..."
        docker compose up -d backend
        
        # Esperar a que el backend esté listo
        log "⏳ Esperando a que los servicios estén listos..."
        sleep 10
        
        # Verificar que el sistema está funcionando
        if curl -s "http://fgj-ocr.local/health" > /dev/null 2>&1; then
            log "✅ Sistema restaurado y funcionando correctamente"
            log "🌐 Disponible en: http://fgj-ocr.local/"
            return 0
        else
            log "⚠️ Sistema restaurado pero hay problemas de conectividad"
            return 0
        fi
    else
        log "❌ Error durante la restauración"
        
        # Intentar reiniciar servicios de todos modos
        log "🔄 Intentando reiniciar servicios..."
        docker compose up -d backend
        
        return 1
    fi
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🏛️  SISTEMA OCR FGJCDMX - RESTAURACIÓN DE BACKUP"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar prerequisitos
    if ! check_prerequisites; then
        log "❌ Prerequisites no cumplidos"
        exit 1
    fi
    
    # Seleccionar backup
    local backup_file
    if ! backup_file=$(select_backup "$1"); then
        exit 1
    fi
    
    # Restaurar backup
    if restore_backup "$backup_file"; then
        log "════════════════════════════════════════════════════════════════"
        log "✅ RESTAURACIÓN COMPLETADA EXITOSAMENTE"
        log "🔗 Sistema disponible en: http://fgj-ocr.local/"
        log "📊 Logs disponibles en: $LOG_FILE"
        log "════════════════════════════════════════════════════════════════"
    else
        log "❌ RESTAURACIÓN FALLÓ"
        log "💡 Revisa los logs en: $LOG_FILE"
        exit 1
    fi
}

# Mostrar ayuda si se solicita
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Sistema OCR FGJCDMX - Script de Restauración"
    echo ""
    echo "Uso: $0 [archivo_backup]"
    echo ""
    echo "Parámetros:"
    echo "  archivo_backup   Nombre del archivo de backup a restaurar (opcional)"
    echo "                   Si no se especifica, se mostrará una lista interactiva"
    echo ""
    echo "Opciones:"
    echo "  --help, -h       Mostrar esta ayuda"
    echo "  --list, -l       Solo listar backups disponibles"
    echo ""
    echo "Ejemplos:"
    echo "  $0                                    # Selección interactiva"
    echo "  $0 sistema_ocr_backup_20251024.sql   # Restaurar backup específico"
    echo ""
    echo "⚠️  ADVERTENCIA: La restauración reemplazará TODOS los datos actuales"
    echo "    Se creará un backup de seguridad automáticamente antes de restaurar"
    echo ""
    exit 0
fi

# Opción para listar backups
if [[ "$1" == "--list" || "$1" == "-l" ]]; then
    list_available_backups
    exit 0
fi

# Ejecutar función principal
main "$1"