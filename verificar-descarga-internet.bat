@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║    Verificación: ¿Docker descarga de Internet?                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🔍 ANÁLISIS DE COMPORTAMIENTO DE DOCKER
echo ═══════════════════════════════════════════════════════════════
echo.

echo 📦 1. IMÁGENES LOCALES DISPONIBLES:
echo ─────────────────────────────────────────────────────────────────
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}"
echo.

echo 📋 2. VERIFICANDO docker-compose.yml:
echo ─────────────────────────────────────────────────────────────────
echo.
echo ¿Tiene pull_policy configurado?
findstr /C:"pull_policy" docker-compose.yml >nul 2>&1
if %errorlevel%==0 (
    echo ✅ SÍ - Tiene pull_policy configurado:
    findstr /C:"pull_policy" docker-compose.yml
) else (
    echo ⚠️  NO - No tiene pull_policy configurado
    echo    Comportamiento por defecto: Docker intentará descargar si falta
)
echo.

echo 🌐 3. COMPORTAMIENTO ACTUAL:
echo ─────────────────────────────────────────────────────────────────
echo.
echo Cuando ejecutas start-docker.bat:
echo.
echo   Paso 1: docker-compose up -d (sin --build)
echo           ↓
echo           ¿Las imágenes ya existen localmente?
echo           ├─ SÍ  → ✅ Usa imágenes locales (NO descarga)
echo           └─ NO  → ⚠️  Intenta descargar de Docker Hub
echo.
echo   Paso 2: Si falla, docker-compose up -d --build
echo           ↓
echo           Construye imagen backend (fj1-backend)
echo           ├─ FROM python:3.11-slim
echo           └─ ⚠️  Si python:3.11-slim no existe local, DESCARGA
echo.

echo 🎯 4. VERIFICACIÓN DE IMÁGENES BASE:
echo ─────────────────────────────────────────────────────────────────
echo.
echo Backend necesita: python:3.11-slim
docker images python:3.11-slim --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>nul
if errorlevel 1 (
    echo ❌ python:3.11-slim NO está descargada
    echo    Si haces rebuild, SE DESCARGARÁ de internet
) else (
    echo ✅ python:3.11-slim está disponible localmente
)
echo.

echo Postgres necesita: postgres:15-alpine
docker images postgres:15-alpine --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>nul
if errorlevel 1 (
    echo ❌ postgres:15-alpine NO está descargada
) else (
    echo ✅ postgres:15-alpine está disponible localmente
)
echo.

echo Nginx necesita: nginx:alpine
docker images nginx:alpine --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>nul
if errorlevel 1 (
    echo ❌ nginx:alpine NO está descargada
) else (
    echo ✅ nginx:alpine está disponible localmente
)
echo.

echo PgAdmin necesita: dpage/pgadmin4:latest
docker images dpage/pgadmin4:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>nul
if errorlevel 1 (
    echo ❌ dpage/pgadmin4:latest NO está descargada
) else (
    echo ✅ dpage/pgadmin4:latest está disponible localmente
)
echo.

echo ═══════════════════════════════════════════════════════════════
echo 💡 CONCLUSIÓN:
echo ═══════════════════════════════════════════════════════════════
echo.

docker images postgres:15-alpine >nul 2>&1
set POSTGRES_LOCAL=%errorlevel%

docker images nginx:alpine >nul 2>&1
set NGINX_LOCAL=%errorlevel%

docker images dpage/pgadmin4:latest >nul 2>&1
set PGADMIN_LOCAL=%errorlevel%

docker images fj1-backend >nul 2>&1
set BACKEND_LOCAL=%errorlevel%

if %POSTGRES_LOCAL%==0 if %NGINX_LOCAL%==0 if %PGADMIN_LOCAL%==0 if %BACKEND_LOCAL%==0 (
    echo ✅ TODAS las imágenes están locales
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  start-docker.bat NO DESCARGA de internet                  ║
    echo ║  (usa imágenes cacheadas localmente)                       ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo ⚠️  EXCEPCIONES que causarían descarga:
    echo    - Ejecutar: docker-compose pull
    echo    - Ejecutar: docker-compose build --pull
    echo    - Eliminar imágenes: docker rmi ^<imagen^>
    echo    - docker-compose.yml con pull_policy: always
) else (
    echo ⚠️  FALTAN algunas imágenes localmente
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  start-docker.bat PODRÍA DESCARGAR de internet            ║
    echo ║  (si intenta reconstruir o falta alguna imagen)           ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo 💡 SOLUCIÓN para trabajar 100%% offline:
    echo    1. Usa: start-docker-offline.bat
    echo    2. O agrega a docker-compose.yml:
    echo       pull_policy: never
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo 🔧 RECOMENDACIÓN:
echo ═══════════════════════════════════════════════════════════════
echo.
echo Para GARANTIZAR que NUNCA descargue de internet:
echo.
echo 1. Agrega en cada servicio de docker-compose.yml:
echo    pull_policy: never
echo.
echo 2. O usa el script: start-docker-offline.bat
echo.
echo 3. O ejecuta siempre con: docker-compose up -d --no-pull
echo.

pause
