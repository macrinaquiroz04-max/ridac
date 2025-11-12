@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║          Diagnóstico Docker - Sistema OCR Fiscalía            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🔍 Verificando instalación de Docker...
echo.

docker --version 2>nul
if errorlevel 1 (
    echo ❌ Docker no está instalado
    goto :fin
) else (
    echo ✅ Docker instalado
)

echo.
echo 🔍 Verificando estado de Docker Desktop...
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop no está corriendo
    echo.
    echo 💡 Inicia Docker Desktop y ejecuta este script nuevamente
    goto :fin
) else (
    echo ✅ Docker Desktop está corriendo
)

echo.
echo 🔍 Verificando imágenes descargadas localmente...
echo.

docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | findstr /C:"postgres" /C:"python" /C:"nginx" /C:"pgadmin"

echo.
echo 🔍 Verificando estado de contenedores...
echo.

docker-compose ps

echo.
echo 🔍 Verificando conectividad a Docker Hub...
echo.

curl -s -o nul -w "%%{http_code}" https://hub.docker.com >nul 2>&1
if errorlevel 1 (
    echo ⚠️  No se puede conectar a Docker Hub (puede estar caído o sin internet)
) else (
    echo ✅ Conectividad a Docker Hub OK
)

echo.
echo 🔍 Verificando espacio en disco...
echo.

docker system df

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    RECOMENDACIONES                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

docker images -q | find /c /v "" > %TEMP%\count.txt
set /p IMAGE_COUNT=<%TEMP%\count.txt
del %TEMP%\count.txt

if %IMAGE_COUNT% LSS 4 (
    echo ⚠️  Tienes pocas imágenes descargadas (%IMAGE_COUNT%)
    echo 💡 Ejecuta cuando Docker Hub esté disponible:
    echo    docker-compose pull
    echo.
) else (
    echo ✅ Tienes %IMAGE_COUNT% imágenes descargadas
    echo.
)

docker-compose ps 2>nul | findstr "Up" >nul
if errorlevel 1 (
    echo ⚠️  Los contenedores no están corriendo
    echo 💡 Para iniciar:
    echo    .\start-docker.bat           (con internet)
    echo    .\start-docker-offline.bat   (sin internet)
    echo.
) else (
    echo ✅ Los contenedores están corriendo
    echo.
)

:fin
echo.
pause
