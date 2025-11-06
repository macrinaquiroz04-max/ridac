#!/bin/bash

# Script de Administración de Auditoría - Sistema OCR FGJCDMX
# Permite consultar logs de auditoría de forma fácil

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Función para mostrar auditoría de un usuario
ver_auditoria_usuario() {
    local username="$1"
    local dias="${2:-7}"
    
    log "🔍 Consultando auditoría del usuario: $username (últimos $dias días)"
    
    docker exec -it sistema_ocr_backend python auditoria_query.py usuario "$username" "$dias"
}

# Función para mostrar estadísticas generales
ver_estadisticas() {
    local dias="${1:-7}"
    
    log "📊 Consultando estadísticas de auditoría (últimos $dias días)"
    
    docker exec -it sistema_ocr_backend python auditoria_query.py estadisticas "$dias"
}

# Función para mostrar eventos críticos
ver_eventos_criticos() {
    local dias="${1:-7}"
    
    log "🚨 Consultando eventos críticos (últimos $dias días)"
    
    docker exec -it sistema_ocr_backend python auditoria_query.py criticos "$dias"
}

# Función para consultar por IP
ver_por_ip() {
    local ip="$1"
    local dias="${2:-30}"
    
    log "🌐 Consultando eventos desde IP: $ip (últimos $dias días)"
    
    docker exec -it sistema_ocr_backend python auditoria_query.py ip "$ip" "$dias"
}

# Función para ver todos los eventos recientes
ver_todos_eventos() {
    local dias="${1:-3}"
    
    log "📋 Consultando todos los eventos recientes (últimos $dias días)"
    
    docker exec -it sistema_ocr_backend python auditoria_query.py todos "$dias"
}

# Función para consulta directa en base de datos
consulta_directa() {
    local query="$1"
    
    log "🔧 Ejecutando consulta directa en base de datos"
    
    docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr -c "$query"
}

# Función para mostrar resumen de actividad
resumen_actividad() {
    local dias="${1:-7}"
    
    log "📈 Resumen de actividad del sistema (últimos $dias días)"
    
    echo "
SELECT 
    DATE(created_at) as fecha,
    COUNT(*) as total_eventos,
    COUNT(DISTINCT usuario_id) as usuarios_activos,
    COUNT(DISTINCT accion) as tipos_acciones
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '$dias days'
GROUP BY DATE(created_at)
ORDER BY fecha DESC;
" | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
}

# Función para mostrar usuarios más activos
usuarios_mas_activos() {
    local dias="${1:-7}"
    
    log "👥 Usuarios más activos (últimos $dias días)"
    
    echo "
SELECT 
    u.username,
    u.nombre_completo,
    COUNT(a.id) as total_eventos,
    MAX(a.created_at) as ultima_actividad
FROM usuarios u
JOIN auditoria a ON u.id = a.usuario_id
WHERE a.created_at >= NOW() - INTERVAL '$dias days'
GROUP BY u.id, u.username, u.nombre_completo
ORDER BY total_eventos DESC
LIMIT 10;
" | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
}

# Función para mostrar acciones más comunes
acciones_mas_comunes() {
    local dias="${1:-7}"
    
    log "🎯 Acciones más comunes (últimos $dias días)"
    
    echo "
SELECT 
    accion,
    COUNT(*) as total,
    COUNT(DISTINCT usuario_id) as usuarios_distintos,
    MAX(created_at) as ultima_vez
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '$dias days'
GROUP BY accion
ORDER BY total DESC;
" | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
}

# Función para mostrar eventos por hora
eventos_por_hora() {
    local dias="${1:-1}"
    
    log "⏰ Distribución de eventos por hora (últimos $dias días)"
    
    echo "
SELECT 
    EXTRACT(HOUR FROM created_at) as hora,
    COUNT(*) as eventos
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '$dias days'
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY hora;
" | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
}

# Función principal
main() {
    log "════════════════════════════════════════════════════════════════"
    log "🔍 SISTEMA DE AUDITORÍA - OCR FGJCDMX"
    log "════════════════════════════════════════════════════════════════"
    
    # Verificar que Docker está corriendo
    if ! docker ps | grep -q "sistema_ocr_backend"; then
        log "❌ El sistema no está corriendo"
        exit 1
    fi
    
    case "$1" in
        usuario)
            if [ -z "$2" ]; then
                log "❌ Debe especificar un username"
                log "💡 Uso: $0 usuario <username> [dias]"
                exit 1
            fi
            ver_auditoria_usuario "$2" "$3"
            ;;
        
        estadisticas)
            ver_estadisticas "$2"
            ;;
        
        criticos)
            ver_eventos_criticos "$2"
            ;;
        
        ip)
            if [ -z "$2" ]; then
                log "❌ Debe especificar una dirección IP"
                log "💡 Uso: $0 ip <direccion_ip> [dias]"
                exit 1
            fi
            ver_por_ip "$2" "$3"
            ;;
        
        todos)
            ver_todos_eventos "$2"
            ;;
        
        resumen)
            resumen_actividad "$2"
            ;;
        
        activos)
            usuarios_mas_activos "$2"
            ;;
        
        acciones)
            acciones_mas_comunes "$2"
            ;;
        
        horas)
            eventos_por_hora "$2"
            ;;
        
        consulta)
            if [ -z "$2" ]; then
                log "❌ Debe especificar una consulta SQL"
                log "💡 Uso: $0 consulta 'SELECT * FROM auditoria LIMIT 5;'"
                exit 1
            fi
            consulta_directa "$2"
            ;;
        
        --help|-h|"")
            echo "
🔍 Sistema de Auditoría - OCR FGJCDMX

Uso: $0 <comando> [opciones]

📋 Comandos de Consulta:
  usuario <username> [dias]    Ver auditoría de un usuario específico
  estadisticas [dias]          Ver estadísticas generales de auditoría
  criticos [dias]              Ver eventos críticos del sistema
  ip <direccion_ip> [dias]     Ver eventos desde una dirección IP
  todos [dias]                 Ver todos los eventos recientes

📊 Comandos de Análisis:
  resumen [dias]               Resumen diario de actividad
  activos [dias]               Usuarios más activos
  acciones [dias]              Acciones más comunes
  horas [dias]                 Distribución por horas

🔧 Comandos Avanzados:
  consulta 'SQL'               Ejecutar consulta SQL directa

📝 Ejemplos:
  $0 usuario eduardo 7         # Auditoría de eduardo últimos 7 días
  $0 estadisticas 30           # Estadísticas últimos 30 días
  $0 criticos 7                # Eventos críticos últimos 7 días
  $0 ip 192.168.1.100 15       # Eventos desde IP específica
  $0 resumen 14                # Resumen últimas 2 semanas
  $0 activos 7                 # Usuarios más activos última semana
  $0 acciones 30               # Acciones más comunes último mes
  $0 horas 1                   # Distribución por horas último día

🌐 Acceso Web: http://fgj-ocr.local/
📊 Base de datos: PostgreSQL en contenedor Docker
            "
            ;;
        
        *)
            log "❌ Comando desconocido: $1"
            log "💡 Use '$0 --help' para ver los comandos disponibles"
            exit 1
            ;;
    esac
    
    log "════════════════════════════════════════════════════════════════"
    log "✅ Consulta completada"
    log "🔗 Sistema disponible en: http://fgj-ocr.local/"
    log "════════════════════════════════════════════════════════════════"
}

# Ejecutar función principal
main "$@"