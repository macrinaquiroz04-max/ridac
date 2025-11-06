@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Consola PostgreSQL                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🗄️  Conectando a PostgreSQL...
echo.
echo Comandos útiles:
echo   \dt          - Listar tablas
echo   \d tabla     - Describir tabla
echo   \du          - Listar usuarios
echo   \l           - Listar bases de datos
echo   \q           - Salir
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

docker-compose exec postgres psql -U postgres -d sistema_ocr

echo.
echo Sesión de PostgreSQL finalizada
pause
