@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Estado del Sistema                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar si Docker está corriendo
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Desktop no está corriendo
    echo.
    echo Por favor inicia Docker Desktop primero
    pause
    exit /b 1
)

echo ✅ Docker Desktop está corriendo
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📊 Estado de Contenedores
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
docker-compose ps

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 💾 Uso de Recursos
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
docker stats --no-stream

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📦 Volúmenes
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
docker volume ls | findstr fj1

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🔍 Verificar Servicios
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Verificar PostgreSQL
docker-compose exec -T postgres pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo ❌ PostgreSQL: NO disponible
) else (
    echo ✅ PostgreSQL: Disponible
)

REM Verificar Backend
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ❌ Backend: NO disponible
) else (
    echo ✅ Backend: Disponible
)

REM Verificar Frontend
curl -s http://localhost >nul 2>&1
if errorlevel 1 (
    echo ❌ Frontend: NO disponible
) else (
    echo ✅ Frontend: Disponible
)

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
