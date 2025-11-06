@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR - Inicio Inteligente (Auto-detecta necesidad)   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker no está instalado
    pause
    exit /b 1
)
echo ✅ Docker encontrado
echo.

REM Verificar si Docker Desktop está corriendo
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
        copy .env.example .env >nul
    )
)

echo 🔍 Detectando imágenes necesarias...
echo.

REM Verificar si las imágenes necesarias existen localmente
set MISSING_IMAGES=0

REM Verificar cada imagen
docker images -q postgres:15-alpine >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Falta: postgres:15-alpine
    set /a MISSING_IMAGES+=1
) else (
    echo ✅ Existe: postgres:15-alpine
)

docker images -q nginx:alpine >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Falta: nginx:alpine
    set /a MISSING_IMAGES+=1
) else (
    echo ✅ Existe: nginx:alpine
)

docker images -q dpage/pgadmin4:latest >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Falta: dpage/pgadmin4:latest
    set /a MISSING_IMAGES+=1
) else (
    echo ✅ Existe: dpage/pgadmin4:latest
)

docker images -q python:3.11-slim >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Falta: python:3.11-slim (para build)
    set /a MISSING_IMAGES+=1
) else (
    echo ✅ Existe: python:3.11-slim
)

echo.

REM Decidir estrategia según imágenes disponibles
if %MISSING_IMAGES% EQU 0 (
    echo ═══════════════════════════════════════════════════════════════
    echo 🎯 TODAS LAS IMÁGENES DISPONIBLES LOCALMENTE
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo ✅ Iniciando en MODO OFFLINE (sin descargar nada)
    echo.
    
    REM Verificar si contenedores ya están corriendo
    docker-compose ps --services --filter "status=running" 2>nul | findstr "." >nul
    if errorlevel 1 (
        echo 🚀 Iniciando contenedores...
        docker-compose up -d --no-build
    ) else (
        echo ✅ Contenedores ya están corriendo
        docker-compose ps
    )
    
) else (
    echo ═══════════════════════════════════════════════════════════════
    echo ⚠️  FALTAN %MISSING_IMAGES% IMAGEN(ES)
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo 🌐 Se necesita INTERNET para descargar imágenes faltantes
    echo.
    
    REM Verificar conectividad a internet
    echo 🔍 Verificando conectividad a Docker Hub...
    curl -s --max-time 5 https://hub.docker.com >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ❌ NO HAY CONEXIÓN A INTERNET
        echo.
        echo ⚠️  No se pueden descargar las imágenes faltantes
        echo.
        echo 💡 OPCIONES:
        echo    1. Conecta a internet y vuelve a ejecutar este script
        echo    2. Copia las imágenes desde otra PC con:
        echo       docker save postgres:15-alpine -o postgres.tar
        echo       docker load -i postgres.tar
        echo.
        pause
        exit /b 1
    )
    
    echo ✅ Conexión a Docker Hub detectada
    echo.
    echo 📥 Descargando imágenes faltantes...
    echo.
    
    REM Descargar solo las que faltan
    docker images -q postgres:15-alpine >nul 2>&1
    if errorlevel 1 (
        echo 📦 Descargando postgres:15-alpine...
        docker pull postgres:15-alpine
    )
    
    docker images -q nginx:alpine >nul 2>&1
    if errorlevel 1 (
        echo 📦 Descargando nginx:alpine...
        docker pull nginx:alpine
    )
    
    docker images -q dpage/pgadmin4:latest >nul 2>&1
    if errorlevel 1 (
        echo 📦 Descargando dpage/pgadmin4:latest...
        docker pull dpage/pgadmin4:latest
    )
    
    docker images -q python:3.11-slim >nul 2>&1
    if errorlevel 1 (
        echo 📦 Descargando python:3.11-slim...
        docker pull python:3.11-slim
    )
    
    echo.
    echo ✅ Imágenes descargadas
    echo.
    echo 🔨 Construyendo imagen del backend...
    docker-compose build backend
    
    echo.
    echo 🚀 Iniciando contenedores...
    docker-compose up -d
)

if errorlevel 1 (
    echo.
    echo ❌ Error al iniciar contenedores
    echo.
    echo Ver logs con: docker-compose logs
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo ✅ SISTEMA INICIADO CORRECTAMENTE
echo ═══════════════════════════════════════════════════════════════
echo.

REM Esperar servicios
echo ⏳ Esperando a que los servicios estén listos...
timeout /t 5 /nobreak >nul

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    SISTEMA LISTO                               ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🌐 URLs de acceso:
echo.
echo    Frontend:     http://localhost
echo    API Backend:  http://localhost/api
echo    API Docs:     http://localhost/docs
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

REM Mostrar modo usado
if %MISSING_IMAGES% EQU 0 (
    echo 💡 Modo usado: OFFLINE (sin internet)
) else (
    echo 💡 Modo usado: ONLINE (descargó %MISSING_IMAGES% imagen/es)
)
echo.

choice /C SN /M "¿Abrir el sistema en el navegador?"
if errorlevel 2 goto :fin
if errorlevel 1 (
    start http://localhost
)

:fin
echo.
pause
