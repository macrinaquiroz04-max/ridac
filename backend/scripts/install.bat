@echo off
chcp 65001 >nul
echo ========================================
echo  INSTALACION SISTEMA OCR - FGJCDMX
echo ========================================
echo.

REM Verificar Python
echo [1/10] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ ERROR: Python no instalado
    echo Descarga Python 3.11 desde: https://www.python.org/downloads/
    pause
    exit /b 1
) else (
    python --version
    echo ✓ OK: Python instalado
)
echo.

REM Verificar PostgreSQL
echo [2/10] Verificando PostgreSQL...
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ ERROR: PostgreSQL no instalado
    echo Descarga PostgreSQL 15 desde: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
) else (
    psql --version
    echo ✓ OK: PostgreSQL instalado
)
echo.

REM Crear carpetas del sistema
echo [3/10] Creando estructura de carpetas...
if not exist "C:\FGJCDMX" mkdir "C:\FGJCDMX"
if not exist "C:\FGJCDMX\documentos" mkdir "C:\FGJCDMX\documentos"
if not exist "C:\FGJCDMX\exportaciones" mkdir "C:\FGJCDMX\exportaciones"
if not exist "C:\FGJCDMX\temp" mkdir "C:\FGJCDMX\temp"
if not exist "C:\FGJCDMX\logs" mkdir "C:\FGJCDMX\logs"
echo ✓ OK: Carpetas creadas
echo.

REM Probar permisos de escritura
echo [4/10] Probando permisos de escritura...
echo test > "C:\FGJCDMX\temp\test_write.txt" 2>nul
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se puede escribir en C:\FGJCDMX
    echo Ejecuta este script como Administrador
    pause
    exit /b 1
) else (
    del "C:\FGJCDMX\temp\test_write.txt" 2>nul
    echo ✓ OK: Permisos de escritura correctos
)
echo.

REM Crear entorno virtual
echo [5/10] Creando entorno virtual Python...
cd /d "%~dp0.."
if exist "venv" (
    echo Entorno virtual ya existe, eliminando...
    rmdir /s /q venv
)
python -m venv venv
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se pudo crear entorno virtual
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo ✓ OK: Entorno virtual creado
echo.

REM Instalar dependencias Python
echo [6/10] Instalando dependencias Python...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se pudieron instalar dependencias
    pause
    exit /b 1
)
echo ✓ OK: Dependencias instaladas
echo.

REM Verificar Tesseract
echo [7/10] Verificando Tesseract OCR...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠ ADVERTENCIA: Tesseract no instalado o no esta en PATH
    echo.
    echo Instrucciones para instalar Tesseract:
    echo 1. Descarga desde: https://github.com/UB-Mannheim/tesseract/wiki
    echo 2. Instala en: C:\Program Files\Tesseract-OCR
    echo 3. Agrega al PATH: C:\Program Files\Tesseract-OCR
    echo 4. Reinicia esta terminal
    echo.
    set /p CONTINUAR="¿Continuar sin Tesseract? (S/N): "
    if /i "%CONTINUAR%" neq "S" (
        echo Instalacion cancelada
        pause
        exit /b 1
    )
) else (
    tesseract --version 2>&1 | findstr /i "tesseract"
    echo ✓ OK: Tesseract instalado
)
echo.

REM Configurar PostgreSQL
echo [8/10] Configurando base de datos...
echo.
echo Ingresa los datos de PostgreSQL:
set /p DB_HOST="Host (default: localhost): "
if "%DB_HOST%"=="" set DB_HOST=localhost

set /p DB_PORT="Puerto (default: 5432): "
if "%DB_PORT%"=="" set DB_PORT=5432

set /p DB_USER="Usuario (default: postgres): "
if "%DB_USER%"=="" set DB_USER=postgres

set /p DB_PASSWORD="Password: "
if "%DB_PASSWORD%"=="" set DB_PASSWORD=1234

set DB_NAME=sistema_ocr

echo.
echo Probando conexion a PostgreSQL...
set PGPASSWORD=%DB_PASSWORD%
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "SELECT 1;" >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se pudo conectar a PostgreSQL
    echo Verifica que PostgreSQL este corriendo y las credenciales sean correctas
    pause
    exit /b 1
)
echo ✓ OK: Conexion exitosa
echo.

REM Crear base de datos
echo Creando base de datos...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "DROP DATABASE IF EXISTS %DB_NAME%;" 2>nul
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "CREATE DATABASE %DB_NAME% WITH ENCODING 'UTF8' LC_COLLATE='es_MX.UTF-8' LC_CTYPE='es_MX.UTF-8';" 2>nul
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se pudo crear la base de datos
    echo Intentando sin locale...
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "CREATE DATABASE %DB_NAME% WITH ENCODING 'UTF8';"
    if %errorlevel% neq 0 (
        echo ✗ ERROR: No se pudo crear la base de datos
        pause
        exit /b 1
    )
)
echo ✓ OK: Base de datos creada
echo.

REM Ejecutar script SQL
echo Creando tablas...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f scripts\schema.sql >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ ERROR: No se pudo ejecutar el script SQL
    echo Intentando con output visible...
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f scripts\schema.sql
    pause
    exit /b 1
)
echo ✓ OK: Tablas creadas
echo.

REM Verificar que se crearon las tablas
echo Verificando tablas...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\dt" 2>&1 | findstr "usuarios" >nul
if %errorlevel% neq 0 (
    echo ✗ ERROR: Las tablas no se crearon correctamente
    pause
    exit /b 1
)
echo ✓ OK: Tablas verificadas
echo.

REM Verificar usuario admin
echo Verificando usuario admin...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT username FROM usuarios WHERE username='admin';" 2>&1 | findstr "admin" >nul
if %errorlevel% neq 0 (
    echo ✗ ERROR: Usuario admin no fue creado
    pause
    exit /b 1
)
echo ✓ OK: Usuario admin creado
echo.

REM Crear archivo .env
echo [9/10] Creando archivo de configuracion...
(
echo # Base de Datos
echo DB_HOST=%DB_HOST%
echo DB_PORT=%DB_PORT%
echo DB_NAME=%DB_NAME%
echo DB_USER=%DB_USER%
echo DB_PASSWORD=%DB_PASSWORD%
echo.
echo # Seguridad
echo JWT_SECRET_KEY=%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%
echo JWT_ALGORITHM=HS256
echo ACCESS_TOKEN_EXPIRE_MINUTES=15
echo REFRESH_TOKEN_EXPIRE_DAYS=7
echo.
echo # Rutas de almacenamiento
echo UPLOAD_PATH=C:/FGJCDMX/documentos
echo EXPORT_PATH=C:/FGJCDMX/exportaciones
echo TEMP_PATH=C:/FGJCDMX/temp
echo LOG_PATH=C:/FGJCDMX/logs
echo.
echo # Configuracion OCR
echo OCR_ENABLE_TESSERACT=true
echo OCR_ENABLE_EASYOCR=false
echo OCR_ENABLE_PADDLEOCR=false
echo OCR_ENABLE_TROCR=false
echo OCR_MAX_WORKERS=2
echo.
echo # Servidor
echo SERVER_HOST=0.0.0.0
echo SERVER_PORT=8001
) > .env

echo ✓ OK: Archivo .env creado
echo.

REM Ejecutar pruebas de sistema
echo [10/10] Ejecutando pruebas del sistema...
echo.
python tests\test_connections.py
if %errorlevel% neq 0 (
    echo.
    echo ⚠ ADVERTENCIA: Algunas pruebas fallaron
    echo El sistema puede no funcionar correctamente
    echo Revisa los errores arriba
    echo.
    set /p CONTINUAR="¿Continuar de todas formas? (S/N): "
    if /i "%CONTINUAR%" neq "S" (
        echo Instalacion cancelada
        pause
        exit /b 1
    )
)
echo.

echo ========================================
echo  INSTALACION COMPLETADA
echo ========================================
echo.
echo Sistema instalado correctamente en:
echo   C:\FGJCDMX\
echo.
echo Base de datos: %DB_NAME%
echo Usuario admin: admin
echo Password:      admin123
echo.
echo IMPORTANTE: Cambia la contraseña del admin despues del primer login
echo.
echo Para iniciar el sistema:
echo   1. Ejecuta: start.bat
echo   2. Abre navegador en: http://localhost:8001
echo   3. Pagina de pruebas: http://localhost:8001/test.html
echo.
echo ========================================
pause
