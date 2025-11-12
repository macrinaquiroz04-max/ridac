#!/bin/bash
# Script de instalación del watchdog como servicio systemd

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║   🛡️  INSTALANDO WATCHDOG AUTOMÁTICO                              ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "scripts/watchdog_restart.sh" ]; then
    echo "❌ Error: Ejecuta este script desde la raíz del proyecto sistemaocr"
    exit 1
fi

# Crear directorios de logs si no existen
mkdir -p logs/login_errors logs/auth_errors logs/ocr_errors
echo "✅ Directorios de logs creados"

# Copiar service file a systemd
echo ""
echo "📋 Instalando servicio systemd..."
sudo cp scripts/sistemaocr-watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Servicio copiado a /etc/systemd/system/"

# Habilitar servicio
echo ""
echo "🔄 Habilitando servicio para inicio automático..."
sudo systemctl enable sistemaocr-watchdog.service
echo "✅ Servicio habilitado"

# Iniciar servicio
echo ""
echo "🚀 Iniciando watchdog..."
sudo systemctl start sistemaocr-watchdog.service

# Esperar un segundo
sleep 2

# Verificar estado
echo ""
echo "📊 Estado del servicio:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo systemctl status sistemaocr-watchdog.service --no-pager -l

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║   ✅ WATCHDOG INSTALADO Y ACTIVO                                  ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔍 Comandos útiles:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Ver logs del watchdog:"
echo "  tail -f logs/watchdog.log"
echo ""
echo "  Ver acciones de reinicio:"
echo "  tail -f logs/watchdog_actions.log"
echo ""
echo "  Ver estado del servicio:"
echo "  sudo systemctl status sistemaocr-watchdog"
echo ""
echo "  Ver logs en tiempo real:"
echo "  sudo journalctl -u sistemaocr-watchdog -f"
echo ""
echo "  Detener watchdog:"
echo "  sudo systemctl stop sistemaocr-watchdog"
echo ""
echo "  Reiniciar watchdog:"
echo "  sudo systemctl restart sistemaocr-watchdog"
echo ""
echo "  Deshabilitar watchdog:"
echo "  sudo systemctl disable sistemaocr-watchdog"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚙️  Configuración actual:"
echo "  - Chequea /health cada 30 segundos"
echo "  - Umbral de errores: 3 fallos"
echo "  - Reinicia: backend"
echo "  - Logs en: logs/watchdog.log"
echo ""
echo "🎯 El watchdog está ACTIVO y vigilando 24/7"
echo "   Si hay errores, se reiniciará automáticamente"
echo "   Todos los errores se registran en logs/"
echo ""
