#!/bin/bash
echo "🔍 VERIFICANDO ESTADO DEL SISTEMA DESPUÉS DE SUSPENSIÓN..."
echo "=========================================================="

# Verificar IP
echo "📡 IP actual:"
ip addr show enp0s8 | grep "inet " | awk '{print $2}'

# Verificar Docker
echo "🐳 Estado de Docker:"
sudo docker compose ps

# Verificar servicios
echo "🌐 Probando servicios:"
echo "  - Nginx:"
curl -s -o /dev/null -w "%{http_code}" http://172.22.134.61
echo ""
echo "  - Backend:"
curl -s -o /dev/null -w "%{http_code}" http://172.22.134.61/health
echo ""

echo "✅ Verificación completada"
echo "Tus compañeros pueden acceder en: http://fgj-ocr.local"