@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Ver Logs                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo Selecciona qué logs quieres ver:
echo.
echo 1. Todos los servicios
echo 2. Backend (FastAPI)
echo 3. PostgreSQL
echo 4. Nginx
echo.
choice /C 1234 /M "Opción"

if errorlevel 4 goto :nginx
if errorlevel 3 goto :postgres
if errorlevel 2 goto :backend
if errorlevel 1 goto :all

:all
echo.
echo 📋 Mostrando logs de TODOS los servicios...
echo.
docker-compose logs -f
goto :fin

:backend
echo.
echo 📋 Mostrando logs del BACKEND...
echo.
docker-compose logs -f backend
goto :fin

:postgres
echo.
echo 📋 Mostrando logs de POSTGRESQL...
echo.
docker-compose logs -f postgres
goto :fin

:nginx
echo.
echo 📋 Mostrando logs de NGINX...
echo.
docker-compose logs -f nginx
goto :fin

:fin
