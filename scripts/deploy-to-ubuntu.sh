#!/bin/bash

# ============================================================================
# Script de Despliegue Automatizado para Servidor Ubuntu
# Sistema OCR FGJCDMX
# Desarrollador: Eduardo Lozada Quiroz, ISC
# ============================================================================

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables de configuración
PROJECT_NAME="sistemaocr"
INSTALL_DIR="/opt/${PROJECT_NAME}"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/tmp/deploy-$(date +%Y%m%d_%H%M%S).log"

# Funciones de ayuda
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# Verificar si ejecuta como root
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        error "Este script debe ejecutarse como root o con sudo"
        exit 1
    fi
}

# Verificar requisitos del sistema
check_requirements() {
    log "🔍 Verificando requisitos del sistema..."
    
    # Verificar Ubuntu
    if ! grep -q "Ubuntu" /etc/os-release; then
        error "Este script está diseñado para Ubuntu"
        exit 1
    fi
    
    # Verificar RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 8 ]; then
        warning "RAM insuficiente: ${TOTAL_RAM}GB (Recomendado: 8GB+)"
    else
        log "✅ RAM: ${TOTAL_RAM}GB"
    fi
    
    # Verificar espacio en disco
    DISK_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$DISK_SPACE" -lt 50 ]; then
        warning "Espacio en disco bajo: ${DISK_SPACE}GB (Recomendado: 100GB+)"
    else
        log "✅ Espacio en disco: ${DISK_SPACE}GB"
    fi
}

# Instalar Docker
install_docker() {
    if command -v docker &> /dev/null; then
        log "✅ Docker ya está instalado"
        docker --version | tee -a "$LOG_FILE"
    else
        log "📦 Instalando Docker..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sh /tmp/get-docker.sh
        usermod -aG docker $SUDO_USER
        log "✅ Docker instalado correctamente"
    fi
}

# Instalar Docker Compose
install_docker_compose() {
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        log "✅ Docker Compose ya está instalado"
    else
        log "📦 Instalando Docker Compose..."
        apt install -y docker-compose
        log "✅ Docker Compose instalado correctamente"
    fi
}

# Instalar herramientas adicionales
install_tools() {
    log "📦 Instalando herramientas adicionales..."
    apt update
    apt install -y git curl wget htop net-tools rsync nano vim
    log "✅ Herramientas instaladas"
}

# Configurar directorio del proyecto
setup_project_directory() {
    log "📁 Configurando directorio del proyecto..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        error "Directorio $INSTALL_DIR no existe."
        info "Opciones:"
        info "1. Transferir proyecto con rsync desde tu máquina:"
        info "   rsync -avz /ruta/local/sistemaocr/ usuario@servidor:$INSTALL_DIR/"
        info "2. Clonar desde Git:"
        info "   git clone <tu-repo> $INSTALL_DIR"
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR"
    log "✅ Directorio configurado: $INSTALL_DIR"
}

# Configurar variables de entorno
setup_environment() {
    log "🔧 Configurando variables de entorno..."
    
    if [ ! -f "$INSTALL_DIR/.env.prod" ]; then
        warning "Archivo .env.prod no existe, creando uno de ejemplo..."
        cat > "$INSTALL_DIR/.env.prod" << 'EOF'
# Base de Datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=sistema_ocr
DB_USER=postgres
DB_PASSWORD=CAMBIAR_ESTO_PASSWORD_SEGURO

# JWT Secret
JWT_SECRET_KEY=CAMBIAR_ESTO_SECRET_MUY_LARGO_Y_SEGURO

# Configuración del servidor
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
TZ=America/Mexico_City

# Producción
ENVIRONMENT=production
DEBUG=False
EOF
        chmod 600 "$INSTALL_DIR/.env.prod"
        warning "⚠️  IMPORTANTE: Edita $INSTALL_DIR/.env.prod con valores seguros"
        info "nano $INSTALL_DIR/.env.prod"
        exit 1
    fi
    
    log "✅ Variables de entorno configuradas"
}

# Construir imágenes Docker
build_images() {
    log "🏗️  Construyendo imágenes Docker..."
    cd "$INSTALL_DIR"
    docker compose -f "$COMPOSE_FILE" build --no-cache
    log "✅ Imágenes construidas correctamente"
}

# Configurar firewall
setup_firewall() {
    log "🛡️  Configurando firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw --force enable
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow ssh
        ufw allow 80/tcp
        ufw allow 443/tcp
        log "✅ Firewall configurado"
        ufw status
    else
        warning "UFW no está instalado, saltando configuración de firewall"
    fi
}

# Crear servicio systemd
create_systemd_service() {
    log "⚙️  Creando servicio systemd..."
    
    cat > /etc/systemd/system/sistema-ocr.service << EOF
[Unit]
Description=Sistema OCR FGJCDMX
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose -f $COMPOSE_FILE up -d
ExecStop=/usr/bin/docker compose -f $COMPOSE_FILE down
User=root

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable sistema-ocr.service
    log "✅ Servicio systemd creado y habilitado"
}

# Configurar backup automático
setup_automatic_backup() {
    log "💾 Configurando backup automático..."
    
    # Crear script de backup
    cat > "$INSTALL_DIR/backup-auto.sh" << 'EOF'
#!/bin/bash
cd /opt/sistemaocr
./backup-database.sh
find backups/ -name "*.sql.gz" -mtime +7 -delete
EOF
    
    chmod +x "$INSTALL_DIR/backup-auto.sh"
    
    # Agregar a crontab
    CRON_JOB="0 2 * * * $INSTALL_DIR/backup-auto.sh >> /var/log/sistema-ocr-backup.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "$INSTALL_DIR/backup-auto.sh"; echo "$CRON_JOB") | crontab -
    
    log "✅ Backup automático configurado (diario a las 2 AM)"
}

# Iniciar servicios
start_services() {
    log "🚀 Iniciando servicios..."
    cd "$INSTALL_DIR"
    docker compose -f "$COMPOSE_FILE" up -d
    
    # Esperar a que los servicios estén listos
    log "⏳ Esperando a que los servicios estén listos..."
    sleep 10
    
    docker compose -f "$COMPOSE_FILE" ps
    log "✅ Servicios iniciados"
}

# Restaurar base de datos
restore_database() {
    log "💾 Buscando backups de base de datos..."
    
    LATEST_BACKUP=$(ls -t "$INSTALL_DIR/backups/"*.sql.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        info "Backup encontrado: $LATEST_BACKUP"
        read -p "¿Deseas restaurar este backup? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            log "🔄 Restaurando base de datos..."
            gunzip -c "$LATEST_BACKUP" | docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr
            
            # Crear función para IDs secuenciales
            log "🔧 Creando función de IDs secuenciales..."
            docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d sistema_ocr < backend/scripts/reutilizar_ids.sql
            
            log "✅ Base de datos restaurada"
        fi
    else
        warning "No se encontraron backups en $INSTALL_DIR/backups/"
        info "El sistema se iniciará con base de datos vacía"
    fi
}

# Verificar instalación
verify_installation() {
    log "🧪 Verificando instalación..."
    
    # Verificar servicios Docker
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log "✅ Servicios Docker ejecutándose"
    else
        error "Servicios Docker no están ejecutándose correctamente"
        docker compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
    
    # Verificar health check
    sleep 5
    if curl -s http://localhost/health | grep -q "healthy"; then
        log "✅ Health check exitoso"
    else
        warning "Health check falló, verifica los logs"
    fi
}

# Mostrar resumen
show_summary() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ DESPLIEGUE COMPLETADO EXITOSAMENTE"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Información del sistema:"
    echo "   - Directorio: $INSTALL_DIR"
    echo "   - Servicio: sistema-ocr.service"
    echo "   - Log de despliegue: $LOG_FILE"
    echo ""
    echo "🌐 URLs de acceso:"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "   - Frontend:     http://$LOCAL_IP/"
    echo "   - API Docs:     http://$LOCAL_IP/docs"
    echo "   - Health Check: http://$LOCAL_IP/health"
    echo "   - PgAdmin:      http://$LOCAL_IP:5050"
    echo ""
    echo "🔧 Comandos útiles:"
    echo "   - Ver estado:   systemctl status sistema-ocr"
    echo "   - Reiniciar:    systemctl restart sistema-ocr"
    echo "   - Ver logs:     docker compose -f $COMPOSE_FILE logs -f"
    echo "   - Detener:      systemctl stop sistema-ocr"
    echo ""
    echo "📝 Tareas pendientes:"
    echo "   1. Editar $INSTALL_DIR/.env.prod con valores seguros"
    echo "   2. Configurar SSL con Let's Encrypt (opcional)"
    echo "   3. Cambiar contraseña del usuario eduardo"
    echo "   4. Configurar dominio DNS (opcional)"
    echo ""
    echo "📖 Documentación completa: $INSTALL_DIR/GUIA_DESPLIEGUE_UBUNTU.md"
    echo "════════════════════════════════════════════════════════════════"
}

# Función principal
main() {
    clear
    echo "════════════════════════════════════════════════════════════════"
    echo "🏛️  SISTEMA OCR FGJCDMX - DESPLIEGUE AUTOMATIZADO"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    check_root
    check_requirements
    
    log "🚀 Iniciando despliegue..."
    
    install_docker
    install_docker_compose
    install_tools
    setup_project_directory
    setup_environment
    setup_firewall
    build_images
    create_systemd_service
    setup_automatic_backup
    start_services
    restore_database
    verify_installation
    
    show_summary
    
    log "✅ Despliegue completado exitosamente"
}

# Ejecutar script principal
main "$@"
