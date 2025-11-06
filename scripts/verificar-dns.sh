#!/bin/bash

# Script para verificar y mantener la configuración DNS del Sistema OCR
# Se ejecuta al inicio para asegurar que todo esté configurado

HOSTS_FILE="/etc/hosts"
BACKUP_FILE="/etc/hosts.backup.$(date +%Y%m%d)"

# Crear backup si no existe
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$HOSTS_FILE" "$BACKUP_FILE"
fi

# Verificar si la entrada existe
if ! grep -q "172.22.134.61.*fgj-ocr.local" "$HOSTS_FILE"; then
    echo "Agregando entrada DNS para fgj-ocr.local..."
    echo "172.22.134.61 fgj-ocr.local fgj-ocr" >> "$HOSTS_FILE"
    echo "Entrada DNS agregada correctamente"
else
    echo "Entrada DNS ya existe en /etc/hosts"
fi

# Verificar configuración de red
if ! ip addr show enp0s8 | grep -q "172.22.134.61"; then
    echo "Configurando IP 172.22.134.61..."
    ip addr add 172.22.134.61/24 dev enp0s8 2>/dev/null || echo "IP ya configurada"
fi

echo "Configuración DNS verificada y actualizada"