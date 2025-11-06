#!/bin/bash

# Script para migrar la tabla permisos_sistema a la nueva estructura
# Convierte de modelo clave-valor a columnas específicas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Función para hacer backup antes de la migración
create_migration_backup() {
    log "🛡️ Creando backup antes de la migración..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$PROJECT_DIR/backups/pre_migration_permisos_${timestamp}.sql"
    
    if docker exec sistema_ocr_db pg_dump -U postgres -d sistema_ocr > "$backup_file" 2>/dev/null; then
        log "✅ Backup de migración creado: $(basename "$backup_file")"
        return 0
    else
        log "❌ Error al crear backup de migración"
        return 1
    fi
}

# Función para migrar la tabla permisos_sistema
migrate_permisos_sistema() {
    log "🔄 Iniciando migración de tabla permisos_sistema..."
    
    # Crear backup antes de migrar
    if ! create_migration_backup; then
        log "❌ No se pudo crear backup. Abortando migración."
        return 1
    fi
    
    # Script SQL para la migración
    local migration_sql="
-- Crear tabla temporal para backup de datos actuales
CREATE TABLE permisos_sistema_backup AS 
SELECT usuario_id, permiso, valor 
FROM permisos_sistema;

-- Eliminar tabla actual
DROP TABLE permisos_sistema CASCADE;

-- Recrear tabla con nueva estructura
CREATE TABLE permisos_sistema (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    gestionar_usuarios BOOLEAN DEFAULT FALSE,
    gestionar_roles BOOLEAN DEFAULT FALSE,
    gestionar_carpetas BOOLEAN DEFAULT FALSE,
    procesar_ocr BOOLEAN DEFAULT FALSE,
    ver_auditoria BOOLEAN DEFAULT FALSE,
    configurar_sistema BOOLEAN DEFAULT FALSE,
    exportar_datos BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuario_permisos UNIQUE (usuario_id),
    CONSTRAINT permisos_sistema_usuario_id_fkey 
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Migrar datos desde backup usando mapeo de permisos
INSERT INTO permisos_sistema (
    usuario_id, 
    gestionar_usuarios, 
    gestionar_roles, 
    gestionar_carpetas, 
    procesar_ocr, 
    ver_auditoria, 
    configurar_sistema, 
    exportar_datos
)
SELECT DISTINCT 
    usuario_id,
    COALESCE(MAX(CASE WHEN permiso IN ('admin_usuarios', 'gestionar_usuarios') THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso = 'gestionar_permisos' THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso = 'gestionar_carpetas' THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso = 'procesar_ocr' THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso = 'ver_auditoria' THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso IN ('admin_sistema', 'configurar_sistema') THEN valor END), FALSE),
    COALESCE(MAX(CASE WHEN permiso = 'exportar_datos' THEN valor END), FALSE)
FROM permisos_sistema_backup
GROUP BY usuario_id;

-- Asegurar que usuarios sin permisos tengan una entrada
INSERT INTO permisos_sistema (usuario_id)
SELECT id FROM usuarios 
WHERE id NOT IN (SELECT usuario_id FROM permisos_sistema)
ON CONFLICT (usuario_id) DO NOTHING;

-- Limpiar tabla temporal
DROP TABLE permisos_sistema_backup;

-- Verificar migración
SELECT 'Migración completada. Total usuarios con permisos:', COUNT(*) 
FROM permisos_sistema;
"
    
    log "📋 Ejecutando migración SQL..."
    
    # Ejecutar migración
    if echo "$migration_sql" | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr; then
        log "✅ Migración de permisos_sistema completada exitosamente"
        
        # Verificar resultado
        log "📊 Verificando resultado de migración..."
        docker exec sistema_ocr_db psql -U postgres -d sistema_ocr -c "SELECT COUNT(*) as usuarios_con_permisos FROM permisos_sistema;"
        docker exec sistema_ocr_db psql -U postgres -d sistema_ocr -c "SELECT usuario_id, gestionar_usuarios, procesar_ocr FROM permisos_sistema LIMIT 3;"
        
        return 0
    else
        log "❌ Error durante la migración"
        return 1
    fi
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🏛️  MIGRACIÓN DE PERMISOS - SISTEMA OCR FGJCDMX"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar que Docker está corriendo
    if ! docker ps | grep -q "sistema_ocr_db"; then
        log "❌ La base de datos no está corriendo"
        exit 1
    fi
    
    # Ejecutar migración
    if migrate_permisos_sistema; then
        log "════════════════════════════════════════════════════════════════"
        log "✅ MIGRACIÓN COMPLETADA EXITOSAMENTE"
        log "🔄 Reiniciando backend para aplicar cambios..."
        
        # Reiniciar backend para que use la nueva estructura
        cd "$PROJECT_DIR"
        docker compose restart backend
        
        log "✅ Backend reiniciado"
        log "🔗 Sistema disponible en: http://fgj-ocr.local/"
        log "════════════════════════════════════════════════════════════════"
    else
        log "❌ MIGRACIÓN FALLÓ"
        log "💡 Los datos se pueden restaurar desde el backup creado"
        exit 1
    fi
}

# Ejecutar función principal
main "$@"