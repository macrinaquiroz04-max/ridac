@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR - Inicio OFFLINE (sin descargar imágenes)       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Este script usa solo imágenes ya descargadas localmente
echo.

REM Verificar Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker no está instalado
    pause
    exit /b 1
)

echo ✅ Docker encontrado
echo.

REM Verificar Docker Desktop
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop no está corriendo
    echo.
    echo Inicia Docker Desktop y ejecuta este script nuevamente
    pause
    exit /b 1
)

echo ✅ Docker Desktop está corriendo
echo.

REM Verificar .env
if not exist .env (
    if exist .env.example (
        echo 📋 Copiando .env.example a .env
        copy .env.example .env
        echo.
    )
)

echo 🚀 Iniciando contenedores (modo OFFLINE)...
echo.

REM Iniciar sin pull ni build
docker-compose up -d --no-build 2>nul

if errorlevel 1 (
    echo.
    echo ❌ No se pudieron iniciar los contenedores
    echo.
    echo ⚠️  POSIBLES CAUSAS:
    echo    - Las imágenes no están descargadas localmente
    echo    - Los contenedores tienen errores de configuración
    echo.
    echo 💡 SOLUCIÓN:
    echo    1. Espera a que Docker Hub esté disponible
    echo    2. Ejecuta: .\start-docker.bat
    echo    3. O descarga manualmente: docker-compose pull
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Contenedores iniciados correctamente (modo OFFLINE)
echo.

REM Esperar servicios
echo ⏳ Esperando a que los servicios estén listos...
timeout /t 10 /nobreak >nul

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    SISTEMA LISTO                               ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🌐 URLs de acceso:
echo.
echo    Frontend:     http://localhost
echo    API Backend:  http://localhost/api
echo    API Docs:     http://localhost/api/docs
echo    PgAdmin:      http://localhost:5050
echo.
echo 📊 PgAdmin credenciales:
echo    Email:    admin@fiscalia.gob.mx
echo    Password: admin123
echo.
echo 🔧 Comandos útiles:
echo.
echo    Ver estado:   docker-compose ps
echo    Ver logs:     docker-compose logs -f
echo    Detener:      docker-compose down
echo.

choice /C SN /M "¿Abrir el sistema en el navegador?"
if errorlevel 2 goto :fin
if errorlevel 1 (
    start http://localhost
)

:fin
echo.
pause
