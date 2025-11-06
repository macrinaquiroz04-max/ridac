#!/bin/bash
# ============================================================================
# Script de Restauración de Base de Datos - Sistema OCR FGJCDMX
# Desarrollado por: Eduardo Lozada Quiroz, ISC
# Cliente: Unidad de Análisis y Contexto (UAyC)
# Fecha: 29 de Octubre de 2025
# ============================================================================

# Configuración
CONTAINER_NAME="sistema_ocr_db"
DB_NAME="sistema_ocr"
DB_USER="postgres"

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Restaurar Backup - Sistema OCR${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Verificar que se proporcionó un archivo
if [ -z "$1" ]; then
    echo -e "${RED}Error: Debe proporcionar un archivo de backup${NC}"
    echo -e "${YELLOW}Uso: $0 <archivo_backup.sql>${NC}"
    echo ""
    echo -e "${YELLOW}Backups disponibles:${NC}"
    ls -lh backups/sistema_ocr_backup_*.sql 2>/dev/null | tail -5
    exit 1
fi

BACKUP_FILE="$1"

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    # Si es un archivo .gz, intentar descomprimir
    if [ -f "${BACKUP_FILE}.gz" ]; then
        echo -e "${YELLOW}Descomprimiendo backup...${NC}"
        gunzip -k "${BACKUP_FILE}.gz"
    else
        echo -e "${RED}Error: El archivo $BACKUP_FILE no existe${NC}"
        exit 1
    fi
fi

# Verificar que el contenedor está corriendo
echo -e "${YELLOW}Verificando contenedor Docker...${NC}"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: El contenedor $CONTAINER_NAME no está corriendo${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Contenedor encontrado${NC}"

# Confirmación
echo -e "${RED}⚠ ADVERTENCIA: Esta acción eliminará todos los datos actuales${NC}"
echo -e "${YELLOW}¿Está seguro de que desea restaurar el backup?${NC}"
echo -e "${YELLOW}Archivo: $BACKUP_FILE${NC}"
read -p "Escriba 'SI' para confirmar: " confirmacion

if [ "$confirmacion" != "SI" ]; then
    echo -e "${YELLOW}Operación cancelada${NC}"
    exit 0
fi

# Crear backup de seguridad antes de restaurar
echo -e "${YELLOW}Creando backup de seguridad...${NC}"
SAFETY_BACKUP="./backups/pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$SAFETY_BACKUP"
echo -e "${GREEN}✓ Backup de seguridad creado: $SAFETY_BACKUP${NC}"

# Restaurar backup
echo -e "${YELLOW}Restaurando base de datos...${NC}"
cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Base de datos restaurada exitosamente${NC}"
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   Restauración completada${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "Backup restaurado desde: ${BACKUP_FILE}"
    echo -e "Backup de seguridad guardado en: ${SAFETY_BACKUP}"
    echo ""
else
    echo -e "${RED}Error: No se pudo restaurar el backup${NC}"
    echo -e "${YELLOW}El backup de seguridad está disponible en: ${SAFETY_BACKUP}${NC}"
    exit 1
fi

exit 0
