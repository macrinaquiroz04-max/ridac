@echo off
chcp 65001 >nul
color 0A
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║   ██████╗ ███████╗██╗   ██╗███████╗████████╗███████╗███╗   ███╗  ║
echo ║  ██╔════╝ ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔════╝████╗ ████║  ║
echo ║  ╚█████╗  ███████╗ ╚████╔╝ ███████╗   ██║   █████╗  ██╔████╔██║  ║
echo ║   ╚═══██╗ ╚════██║  ╚██╔╝  ╚════██║   ██║   ██╔══╝  ██║╚██╔╝██║  ║
echo ║  ██████╔╝ ███████║   ██║   ███████║   ██║   ███████╗██║ ╚═╝ ██║  ║
echo ║  ╚═════╝  ╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝  ║
echo ║                                                                   ║
echo ║          SISTEMA OCR - FISCALÍA GENERAL CDMX                     ║
echo ║                  INICIO RÁPIDO                                   ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo.
echo  📋 INSTRUCCIONES RÁPIDAS:
echo  ═════════════════════════════════════════════════════════════════
echo.
echo  1️⃣  Ejecuta: start-docker.bat
echo      (Inicia todos los servicios del sistema)
echo.
echo  2️⃣  Accede desde tu navegador:
echo      👉 http://fgjcdmx
echo      👉 http://localhost
echo.
echo  3️⃣  Verifica estado: ver-estado.bat
echo      (Muestra el estado de todos los contenedores)
echo.
echo  4️⃣  Ver logs: ver-logs.bat
echo      (Muestra los registros en tiempo real)
echo.
echo  5️⃣  Detener sistema: stop-docker.bat
echo      (Apaga todos los servicios)
echo.
echo  ═════════════════════════════════════════════════════════════════
echo.
echo  🔐 CREDENCIALES POR DEFECTO:
echo  ═════════════════════════════════════════════════════════════════
echo.
echo  📊 PgAdmin (http://localhost:5050)
echo     Email: admin@fiscalia.gob.mx
echo     Password: admin123
echo.
echo  💾 PostgreSQL
echo     Usuario: postgres
echo     Password: 1234
echo     Puerto: 5432
echo.
echo  ═════════════════════════════════════════════════════════════════
echo.
echo.
choice /C 12345X /N /M "  ¿Qué deseas hacer? [1]Iniciar [2]Estado [3]Logs [4]Detener [5]Ayuda [X]Salir: "

if errorlevel 6 goto FIN
if errorlevel 5 goto AYUDA
if errorlevel 4 goto DETENER
if errorlevel 3 goto LOGS
if errorlevel 2 goto ESTADO
if errorlevel 1 goto INICIAR

:INICIAR
cls
echo.
echo 🚀 Iniciando el sistema...
echo.
call start-docker.bat
goto FIN

:ESTADO
cls
echo.
echo 📊 Verificando estado del sistema...
echo.
call ver-estado.bat
goto MENU

:LOGS
cls
echo.
echo 📋 Mostrando logs del sistema...
echo.
call ver-logs.bat
goto FIN

:DETENER
cls
echo.
echo 🛑 Deteniendo el sistema...
echo.
call stop-docker.bat
goto FIN

:AYUDA
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                    AYUDA Y DOCUMENTACIÓN                          ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo 📚 ARCHIVOS DE AYUDA DISPONIBLES:
echo ═════════════════════════════════════════════════════════════════
echo.
echo  LEEME_PRIMERO.md              - Guía de inicio rápido
echo  README_DOCKER.md              - Documentación de Docker
echo  GUIA_DESPLIEGUE_FISCALIA.md   - Guía de despliegue
echo  DOCKER_GUIA_INSTALACION.md    - Instalación de Docker
echo.
echo ═════════════════════════════════════════════════════════════════
echo.
echo 🔧 SCRIPTS DISPONIBLES:
echo ═════════════════════════════════════════════════════════════════
echo.
echo  start-docker.bat              - Iniciar el sistema
echo  stop-docker.bat               - Detener el sistema
echo  ver-estado.bat                - Ver estado de servicios
echo  ver-logs.bat                  - Ver logs en tiempo real
echo  backup-database.bat           - Hacer backup de la BD
echo  restaurar-backup.bat          - Restaurar backup
echo  configurar-dominio-fgjcdmx.bat - Configurar dominio local
echo.
echo ═════════════════════════════════════════════════════════════════
echo.
pause
goto MENU

:MENU
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                  SISTEMA OCR - MENÚ PRINCIPAL                     ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
choice /C 12345X /N /M "  ¿Qué deseas hacer? [1]Iniciar [2]Estado [3]Logs [4]Detener [5]Ayuda [X]Salir: "
if errorlevel 6 goto FIN
if errorlevel 5 goto AYUDA
if errorlevel 4 goto DETENER
if errorlevel 3 goto LOGS
if errorlevel 2 goto ESTADO
if errorlevel 1 goto INICIAR

:FIN
echo.
echo 👋 ¡Hasta luego!
echo.
timeout /t 2 >nul
exit
