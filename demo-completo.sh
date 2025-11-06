#!/bin/bash

# ========================================
# Script Demo Completo
# Sistema OCR Fiscalía - Ubuntu Server
# ========================================

PROJECT_DIR="/opt/fgjcdmx"
COMPOSE_FILE="docker-compose.ubuntu.yml"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_demo() {
    echo -e "${PURPLE}[DEMO]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[PASO]${NC} $1"
}

wait_user() {
    echo
    read -p "Presiona Enter para continuar..." -r
    echo
}

# Verificar directorio
check_directory() {
    if [[ ! -f "$PROJECT_DIR/$COMPOSE_FILE" ]]; then
        log_info "Cambiando al directorio del proyecto: $PROJECT_DIR"
        cd "$PROJECT_DIR" || {
            echo "Error: No se pudo acceder a $PROJECT_DIR"
            exit 1
        }
    else
        cd "$PROJECT_DIR"
    fi
}

# Función principal del demo
main() {
    clear
    echo
    echo "=================================================================="
    echo "  🎭 DEMO COMPLETO - Sistema OCR Fiscalía"
    echo "  Demostración de todas las funcionalidades"
    echo "=================================================================="
    echo
    
    check_directory
    
    log_info "Este demo te mostrará todas las funcionalidades del sistema"
    wait_user
    
    # 1. MOSTRAR INFORMACIÓN DEL SISTEMA
    clear
    echo -e "${PURPLE}📊 1. INFORMACIÓN DEL SISTEMA${NC}"
    echo "=================================================================="
    
    log_step "Mostrando información completa del sistema..."
    ./sistema-ocr.sh info
    wait_user
    
    # 2. VERIFICAR ESTADO DE SERVICIOS
    clear
    echo -e "${PURPLE}🔍 2. VERIFICACIÓN COMPLETA${NC}"
    echo "=================================================================="
    
    log_step "Ejecutando verificación completa del sistema..."
    ./verificar-sistema.sh
    wait_user
    
    # 3. MOSTRAR USUARIOS DISPONIBLES
    clear
    echo -e "${PURPLE}👥 3. USUARIOS DEL SISTEMA${NC}"
    echo "=================================================================="
    
    log_step "Consultando usuarios disponibles en la base de datos..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        u.id,
        u.username,
        u.email,
        u.nombre_completo,
        r.nombre as rol,
        CASE WHEN u.activo THEN 'Activo' ELSE 'Inactivo' END as estado
    FROM usuarios u
    LEFT JOIN roles r ON u.rol_id = r.id
    ORDER BY u.id;"
    
    echo
    log_demo "Usuarios disponibles para hacer login:"
    echo "   👤 admin / admin123 (Administrador completo)"
    echo "   👤 eduardo / lalo1998c33 (Administrador - Eduardo)"
    echo "   👤 director / director123 (Director con permisos)"
    echo "   👤 analista / analista123 (Analista básico)"
    wait_user
    
    # 4. MOSTRAR CARPETAS Y DATOS
    clear
    echo -e "${PURPLE}📁 4. CARPETAS Y DATOS DE EJEMPLO${NC}"
    echo "=================================================================="
    
    log_step "Consultando carpetas de investigación..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        numero_expediente,
        nombre,
        anio,
        estado,
        (SELECT COUNT(*) FROM tomos WHERE carpeta_id = c.id) as total_tomos
    FROM carpetas c
    ORDER BY numero_expediente;"
    
    echo
    log_step "Consultando tomos disponibles..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        c.numero_expediente,
        t.numero_tomo,
        t.nombre_archivo,
        t.numero_paginas,
        t.estado
    FROM tomos t
    JOIN carpetas c ON t.carpeta_id = c.id
    ORDER BY c.numero_expediente, t.numero_tomo;"
    
    wait_user
    
    # 5. DEMOSTRAR ANÁLISIS JURÍDICO
    clear
    echo -e "${PURPLE}⚖️ 5. ANÁLISIS JURÍDICO AUTOMATIZADO${NC}"
    echo "=================================================================="
    
    log_step "Mostrando diligencias extraídas automáticamente..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        c.numero_expediente,
        d.tipo_diligencia,
        d.fecha_diligencia,
        d.responsable,
        d.numero_oficio
    FROM diligencias d
    JOIN carpetas c ON d.carpeta_id = c.id
    ORDER BY d.fecha_diligencia;"
    
    echo
    log_step "Mostrando personas identificadas..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        c.numero_expediente,
        p.nombre_completo,
        p.rol,
        SUBSTRING(p.direccion, 1, 50) || '...' as direccion_corta,
        p.telefono
    FROM personas_identificadas p
    JOIN carpetas c ON p.carpeta_id = c.id
    ORDER BY c.numero_expediente, p.rol;"
    
    wait_user
    
    # 6. MOSTRAR CONTENIDO OCR
    clear
    echo -e "${PURPLE}🔍 6. CONTENIDO EXTRAÍDO POR OCR${NC}"
    echo "=================================================================="
    
    log_step "Mostrando muestra del contenido extraído por OCR..."
    echo
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        c.numero_expediente,
        t.numero_tomo,
        ocr.numero_pagina,
        SUBSTRING(ocr.texto_extraido, 1, 100) || '...' as muestra_texto,
        ROUND(ocr.confianza, 1) || '%' as confianza
    FROM contenido_ocr ocr
    JOIN tomos t ON ocr.tomo_id = t.id
    JOIN carpetas c ON t.carpeta_id = c.id
    ORDER BY c.numero_expediente, t.numero_tomo, ocr.numero_pagina
    LIMIT 5;"
    
    wait_user
    
    # 7. DEMOSTRAR API
    clear
    echo -e "${PURPLE}🔌 7. DEMOSTRACIÓN DE API${NC}"
    echo "=================================================================="
    
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    log_step "Probando endpoint de salud de la API..."
    echo
    curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
    echo
    
    log_step "Intentando login via API..."
    echo
    LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=admin&password=admin123")
    
    if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
        log_success "Login exitoso via API"
        echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"
        
        # Extraer token
        ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        
        echo
        log_step "Probando endpoint protegido con token..."
        echo
        curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "http://localhost:8000/api/usuarios/me" | jq . 2>/dev/null || curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "http://localhost:8000/api/usuarios/me"
    else
        echo "❌ Error en login API"
        echo "$LOGIN_RESPONSE"
    fi
    
    echo
    log_demo "URLs de acceso al sistema:"
    echo "   🌐 Frontend: http://$SERVER_IP"
    echo "   📚 API Docs: http://$SERVER_IP/api/docs"
    echo "   🗄️ PgAdmin: http://$SERVER_IP:5050"
    
    wait_user
    
    # 8. DEMOSTRAR FUNCIONES DE GESTIÓN
    clear
    echo -e "${PURPLE}🛠️ 8. FUNCIONES DE GESTIÓN${NC}"
    echo "=================================================================="
    
    log_step "Mostrando comandos de gestión disponibles..."
    echo
    ./sistema-ocr.sh help
    
    echo
    log_step "Creando backup de demostración..."
    echo
    ./sistema-ocr.sh backup
    
    echo
    log_step "Listando backups disponibles..."
    echo
    ls -la /opt/fgjcdmx/backups/
    
    wait_user
    
    # 9. MOSTRAR MONITOREO
    clear
    echo -e "${PURPLE}📊 9. MONITOREO Y ESTADÍSTICAS${NC}"
    echo "=================================================================="
    
    log_step "Mostrando estadísticas del sistema..."
    echo
    
    echo "💾 Uso de memoria:"
    free -h
    echo
    
    echo "💽 Uso de disco:"
    df -h /opt/fgjcdmx
    echo
    
    echo "🐳 Estado de contenedores Docker:"
    docker compose -f "$COMPOSE_FILE" ps
    echo
    
    echo "📈 Estadísticas de base de datos:"
    docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr -c "
    SELECT 
        'Usuarios' as tabla, COUNT(*) as registros FROM usuarios
    UNION ALL
    SELECT 'Carpetas', COUNT(*) FROM carpetas
    UNION ALL
    SELECT 'Tomos', COUNT(*) FROM tomos
    UNION ALL
    SELECT 'Contenido OCR', COUNT(*) FROM contenido_ocr
    UNION ALL
    SELECT 'Diligencias', COUNT(*) FROM diligencias
    UNION ALL
    SELECT 'Personas', COUNT(*) FROM personas_identificadas;"
    
    wait_user
    
    # 10. CONFIGURACIÓN AVANZADA
    clear
    echo -e "${PURPLE}⚙️ 10. CONFIGURACIÓN AVANZADA${NC}"
    echo "=================================================================="
    
    log_step "Mostrando configuración actual del sistema..."
    echo
    
    echo "🔧 Variables de entorno principales:"
    echo "   DB_HOST: $(grep DB_HOST .env | cut -d'=' -f2)"
    echo "   DB_NAME: $(grep DB_NAME .env | cut -d'=' -f2)"
    echo "   UVICORN_WORKERS: $(grep UVICORN_WORKERS .env | cut -d'=' -f2)"
    echo "   OCR_MAX_WORKERS: $(grep OCR_MAX_WORKERS .env | cut -d'=' -f2)"
    echo
    
    echo "📁 Estructura de directorios:"
    tree /opt/fgjcdmx -L 2 2>/dev/null || ls -la /opt/fgjcdmx/
    echo
    
    echo "🐳 Configuración de Docker Compose:"
    echo "   Archivo: docker-compose.ubuntu.yml"
    echo "   Servicios: $(docker compose -f "$COMPOSE_FILE" config --services | tr '\n' ' ')"
    
    wait_user
    
    # RESUMEN FINAL
    clear
    echo "=================================================================="
    echo "  🎉 DEMO COMPLETADO"
    echo "=================================================================="
    echo
    echo -e "${GREEN}✅ Has visto todas las funcionalidades principales:${NC}"
    echo
    echo "1. 📊 Información completa del sistema"
    echo "2. 🔍 Verificación automática de servicios"
    echo "3. 👥 Gestión de usuarios y roles"
    echo "4. 📁 Organización de carpetas y tomos"
    echo "5. ⚖️ Análisis jurídico automatizado"
    echo "6. 🔍 Extracción OCR de documentos"
    echo "7. 🔌 API REST completa"
    echo "8. 🛠️ Herramientas de gestión"
    echo "9. 📊 Monitoreo y estadísticas"
    echo "10. ⚙️ Configuración avanzada"
    echo
    echo -e "${CYAN}🌐 Acceso al sistema:${NC}"
    echo "   Frontend: http://$SERVER_IP"
    echo "   API Docs: http://$SERVER_IP/api/docs"
    echo "   PgAdmin:  http://$SERVER_IP:5050"
    echo
    echo -e "${CYAN}👤 Usuarios de prueba:${NC}"
    echo "   admin / admin123 (Administrador)"
    echo "   eduardo / lalo1998c33 (Eduardo admin)"
    echo "   director / director123 (Director)"
    echo "   analista / analista123 (Analista)"
    echo
    echo -e "${YELLOW}📚 Documentación:${NC}"
    echo "   INSTALACION_UBUNTU_SERVER.md"
    echo "   COMANDOS_RAPIDOS.md"
    echo "   RESUMEN_UBUNTU_SERVER.md"
    echo
    echo -e "${PURPLE}🚀 ¡El sistema está listo para usar en producción!${NC}"
    echo "=================================================================="
    echo
}

# Ejecutar función principal
main "$@"