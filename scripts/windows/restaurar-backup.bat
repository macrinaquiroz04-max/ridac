@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Restaurar Backup                     ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Verificar que existe la carpeta de backups
if not exist backups (
    echo ❌ No existe la carpeta de backups
    pause
    exit /b 1
)

echo 📋 Backups disponibles:
echo.
dir /B backups\*.sql
echo.

set /p BACKUP_FILE="Ingresa el nombre del archivo de backup (sin ruta): "

if not exist "backups\%BACKUP_FILE%" (
    echo ❌ Archivo no encontrado: backups\%BACKUP_FILE%
    pause
    exit /b 1
)

echo.
echo ⚠️  ADVERTENCIA: Esto sobrescribirá la base de datos actual
echo.
choice /C SN /M "¿Estás seguro de continuar?"
if errorlevel 2 goto :cancelar
if errorlevel 1 goto :restaurar

:restaurar
echo.
echo 🔄 Restaurando backup...
echo.

REM Restaurar el backup
type "backups\%BACKUP_FILE%" | docker-compose exec -T postgres psql -U postgres -d sistema_ocr

if errorlevel 1 (
    echo ❌ Error al restaurar backup
    pause
    exit /b 1
)

echo.
echo ✅ Backup restaurado exitosamente
echo.
goto :fin

:cancelar
echo.
echo ❌ Operación cancelada
echo.

:fin
pause
