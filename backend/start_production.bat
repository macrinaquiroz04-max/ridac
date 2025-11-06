@echo off
echo ================================
echo  INICIANDO SERVIDOR DE PRODUCCION
echo  Sistema de Analisis Juridico
echo ================================
echo.
echo Servidor: http://localhost:8000
echo Dashboard: ../frontend/dashboard-usuario.html
echo.
echo Presiona Ctrl+C para detener
echo.

cd /d "%~dp0"
python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False, log_level='info')"

pause
