@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║   Sistema OCR Fiscalía - Backup Base de Datos                 ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Crear carpeta de backups si no existe
if not exist backups mkdir backups

REM Generar nombre de archivo con fecha y hora
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_FILE=backups\sistema_ocr_backup_%TIMESTAMP%.sql

echo 📦 Creando backup de la base de datos...
echo.
echo Archivo: %BACKUP_FILE%
echo.

REM Ejecutar backup
docker-compose exec -T postgres pg_dump -U postgres sistema_ocr > %BACKUP_FILE%

if errorlevel 1 (
    echo ❌ Error al crear backup
    pause
    exit /b 1
)

echo.
echo ✅ Backup creado exitosamente
echo.
echo 📁 Ubicación: %BACKUP_FILE%
echo.

REM Mostrar tamaño del archivo
for %%A in (%BACKUP_FILE%) do echo Tamaño: %%~zA bytes
echo.

REM Listar backups existentes
echo 📋 Backups disponibles:
echo.
dir /B backups\*.sql
echo.

pause
