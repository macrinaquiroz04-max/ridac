@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Detener Docker                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🛑 Deteniendo contenedores...
docker-compose down

echo.
echo ✅ Sistema detenido correctamente
echo.
echo 📝 Nota: Los datos están seguros en los volúmenes Docker
echo.
echo Para iniciar nuevamente, ejecuta: start-docker.bat
echo.
pause
