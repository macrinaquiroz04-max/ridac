@echo off
chcp 65001 >nul
echo ========================================
echo  INICIANDO SISTEMA OCR - FGJCDMX
echo ========================================
echo.

cd /d "%~dp0.."

REM Verificar entorno virtual
if not exist "venv" (
    echo ✗ ERROR: Entorno virtual no existe
    echo Ejecuta install.bat primero
    pause
    exit /b 1
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Verificar archivo .env
if not exist ".env" (
    echo ✗ ERROR: Archivo .env no existe
    echo Ejecuta install.bat primero
    pause
    exit /b 1
)

REM Pruebas rápidas antes de iniciar
echo [1/3] Ejecutando pruebas rapidas...
python -c "from app.database import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); db.close(); print('✓ OK: Base de datos accesible')" 2>nul
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se puede conectar a la base de datos
    echo Verifica que PostgreSQL este corriendo
    echo.
    set /p CONTINUAR="¿Intentar iniciar de todas formas? (S/N): "
    if /i "%CONTINUAR%" neq "S" (
        pause
        exit /b 1
    )
)
echo.

echo [2/3] Verificando archivos del sistema...
if not exist "C:\FGJCDMX\documentos" (
    echo ✗ ERROR: Carpeta de documentos no existe
    echo Creando carpeta...
    mkdir "C:\FGJCDMX\documentos"
)
echo ✓ OK: Sistema de archivos listo
echo.

REM Iniciar backend FastAPI
echo [3/3] Iniciando servidor...
echo.
echo ========================================
echo  SISTEMA INICIADO
echo ========================================
echo.
echo Frontend:     http://localhost:8001
echo API Docs:     http://localhost:8001/docs
echo Pruebas:      http://localhost:8001/test.html
echo.
echo Usuario:      admin
echo Password:     admin123
echo.
echo Presiona Ctrl+C para detener el servidor
echo ========================================
echo.

python main.py

echo.
echo Sistema detenido.
pause
