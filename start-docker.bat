@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Inicio con Docker                    ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker no está instalado o no está en el PATH
    echo.
    echo Por favor instala Docker Desktop desde:
    echo https://www.docker.com/products/docker-desktop
    echo.
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
    echo Por favor inicia Docker Desktop y espera a que esté listo
    echo Luego ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Docker Desktop está corriendo
echo.

REM Verificar si existe .env, si no copiar de .env.example
if not exist .env (
    echo ⚠️  Archivo .env no encontrado
    if exist .env.example (
        echo 📋 Copiando .env.example a .env
        copy .env.example .env
        echo.
        echo ⚠️  IMPORTANTE: Edita el archivo .env y cambia las contraseñas
        echo antes de usar en producción
        echo.
        pause
    ) else (
        echo ❌ Archivo .env.example no encontrado
        pause
        exit /b 1
    )
)

echo 🚀 Iniciando contenedores Docker...
echo.

REM Verificar si los contenedores ya están corriendo
docker-compose ps --services --filter "status=running" >nul 2>&1
set RUNNING_COUNT=0
for /f %%i in ('docker-compose ps --services --filter "status=running" 2^>nul') do set /a RUNNING_COUNT+=1

if %RUNNING_COUNT% GTR 0 (
    echo ✅ Contenedores ya están corriendo
    echo.
    echo 📊 Estado actual:
    docker-compose ps
    echo.
    echo 💡 Si necesitas reiniciar:
    echo    docker-compose restart
    echo.
    echo 💡 Si necesitas reconstruir:
    echo    docker-compose down
    echo    docker-compose up -d --build
    echo.
    goto :mostrar_info
)

echo 🔄 Intentando iniciar contenedores (sin rebuild)...
docker-compose up -d 2>nul

if errorlevel 1 (
    echo ⚠️  Los contenedores no están listos, intentando construir...
    echo.
    
    REM Intentar build solo si es necesario
    docker-compose up -d --build 2>nul
    
    if errorlevel 1 (
        echo.
        echo ❌ Error al iniciar contenedores
        echo.
        echo ⚠️  POSIBLES CAUSAS:
        echo    1. Docker Hub está temporalmente no disponible (error 503)
        echo    2. Problemas de conexión a internet
        echo    3. Imágenes base no disponibles
        echo.
        echo 💡 SOLUCIONES:
        echo    1. Usa: .\start-docker-offline.bat (modo offline)
        echo    2. Espera unos minutos y vuelve a intentar
        echo    3. Ver logs: docker-compose logs
        echo.
        pause
        exit /b 1
    )
)

:mostrar_info
echo.
echo ✅ Contenedores iniciados correctamente
echo.

REM Esperar a que los servicios estén listos
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
echo    PgAdmin:      http://localhost:5050
echo.
echo 📊 PgAdmin credenciales:
echo    Email:    admin@fiscalia.gob.mx
echo    Password: admin123
echo.
echo 🔧 Comandos útiles:
echo.
echo    Ver estado:        docker-compose ps
echo    Ver logs:          docker-compose logs -f
echo    Detener sistema:   docker-compose down
echo    Reiniciar:         docker-compose restart
echo.
echo 📝 Para ver los logs en tiempo real, ejecuta:
echo    docker-compose logs -f
echo.

REM Preguntar si quiere abrir el navegador
choice /C SN /M "¿Deseas abrir el sistema en el navegador?"
if errorlevel 2 goto :fin
if errorlevel 1 (
    start http://localhost
)

:fin
echo.
echo Presiona cualquier tecla para salir...
pause >nul
