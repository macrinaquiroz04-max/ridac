#!/bin/bash
# ============================================================================
# Script de Backup de Base de Datos - Sistema OCR FGJCDMX
# Desarrollado por: Eduardo Lozada Quiroz, ISC
# Cliente: Unidad de Análisis y Contexto (UAyC)
# Fecha: 29 de Octubre de 2025
# ============================================================================

# Configuración
CONTAINER_NAME="sistema_ocr_db"
DB_NAME="sistema_ocr"
DB_USER="postgres"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sistema_ocr_backup_${DATE}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Backup Sistema OCR - FGJCDMX${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Crear directorio de backups si no existe
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}Creando directorio de backups...${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Verificar que el contenedor está corriendo
echo -e "${YELLOW}Verificando contenedor Docker...${NC}"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: El contenedor $CONTAINER_NAME no está corriendo${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Contenedor encontrado${NC}"

# Crear backup
echo -e "${YELLOW}Creando backup de la base de datos...${NC}"
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup creado exitosamente${NC}"
    
    # Mostrar tamaño
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}  Tamaño: $BACKUP_SIZE${NC}"
    echo -e "${GREEN}  Ubicación: $BACKUP_FILE${NC}"
    
    # Comprimir backup
    echo -e "${YELLOW}Comprimiendo backup...${NC}"
    gzip -k "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        echo -e "${GREEN}✓ Backup comprimido exitosamente${NC}"
        echo -e "${GREEN}  Tamaño comprimido: $COMPRESSED_SIZE${NC}"
        echo -e "${GREEN}  Ubicación: $COMPRESSED_FILE${NC}"
    else
        echo -e "${YELLOW}⚠ No se pudo comprimir el backup${NC}"
    fi
    
    # Mostrar resumen
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   Backup completado exitosamente${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "Archivos generados:"
    echo -e "  - SQL: ${BACKUP_FILE}"
    echo -e "  - Comprimido: ${COMPRESSED_FILE}"
    echo ""
    echo -e "${YELLOW}Para restaurar este backup:${NC}"
    echo -e "  ./restore-backup.sh ${BACKUP_FILE}"
    echo ""
    
    # Limpiar backups antiguos (mantener últimos 10)
    echo -e "${YELLOW}Limpiando backups antiguos (manteniendo últimos 10)...${NC}"
    cd "$BACKUP_DIR"
    ls -t sistema_ocr_backup_*.sql 2>/dev/null | tail -n +11 | xargs -r rm
    ls -t sistema_ocr_backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm
    echo -e "${GREEN}✓ Limpieza completada${NC}"
    
else
    echo -e "${RED}Error: No se pudo crear el backup${NC}"
    exit 1
fi

exit 0
