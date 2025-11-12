# Monitor de Backend - Sistema OCR
# Versión PowerShell mejorada

$Host.UI.RawUI.WindowTitle = "Monitor Backend - Sistema OCR"
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "Green"
Clear-Host

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   MONITOR DE ESTADO DEL BACKEND" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Presiona Ctrl+C para detener el monitor" -ForegroundColor Yellow
Write-Host ""

function Get-BackendStatus {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   ESTADO DEL BACKEND - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # [1] Estado del contenedor
    Write-Host "[1] Estado del Contenedor:" -ForegroundColor Yellow
    try {
        $containers = docker ps --filter "name=sistema_ocr_backend" --format "{{.Names}}`t{{.Status}}" 2>$null
        if ($containers) {
            Write-Host $containers -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Contenedor no encontrado o detenido" -ForegroundColor Red
        }
    } catch {
        Write-Host "[ERROR] No se pudo obtener estado de Docker" -ForegroundColor Red
    }
    Write-Host ""

    # [2] Health Check
    Write-Host "[2] Health Check:" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "[OK] Backend respondiendo" -ForegroundColor Green
        Write-Host "    Estado: $($response.status)" -ForegroundColor Cyan
        Write-Host "    Versión: $($response.version)" -ForegroundColor Cyan
        Write-Host "    Procesos activos: $($response.procesos_activos)" -ForegroundColor Cyan
        Write-Host "    Último heartbeat: $($response.ultimo_heartbeat_segundos)s" -ForegroundColor Cyan
        if ($response.note) {
            Write-Host "    Nota: $($response.note)" -ForegroundColor Magenta
        }
    } catch {
        Write-Host "[ERROR] Backend NO responde" -ForegroundColor Red
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor DarkRed
    }
    Write-Host ""

    # [3] Procesos OCR Activos
    Write-Host "[3] Procesos OCR:" -ForegroundColor Yellow
    try {
        # Intentar leer token del localStorage simulado
        $tokenPath = "$env:TEMP\sistemaocr_token.txt"
        
        if (Test-Path $tokenPath) {
            $token = Get-Content $tokenPath -Raw
            $headers = @{
                'Authorization' = "Bearer $token"
            }
            
            $response = Invoke-RestMethod -Uri "http://localhost:8000/api/admin/estado-procesamiento" -Headers $headers -TimeoutSec 5 -ErrorAction Stop
            
            Write-Host "    Sistema activo: $($response.sistema_activo)" -ForegroundColor $(if ($response.sistema_activo) { "Green" } else { "Red" })
            Write-Host "    Último heartbeat: $($response.ultimo_heartbeat_segundos)s" -ForegroundColor Cyan
            Write-Host "    Total procesos: $($response.total_procesos)" -ForegroundColor Cyan
            Write-Host "    Procesos activos: $($response.procesos_activos)" -ForegroundColor Cyan
            
            if ($response.procesos -and ($response.procesos | Get-Member -MemberType NoteProperty).Count -gt 0) {
                Write-Host ""
                Write-Host "    Detalle de procesos:" -ForegroundColor Magenta
                foreach ($key in $response.procesos.PSObject.Properties.Name) {
                    $proceso = $response.procesos.$key
                    Write-Host "      Tomo $key : $($proceso.estado) - $($proceso.progreso)% - Página $($proceso.pagina_actual)/$($proceso.total_paginas)" -ForegroundColor White
                }
            } else {
                Write-Host "    No hay procesos en curso" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "[INFO] No hay token guardado" -ForegroundColor Yellow
            Write-Host "    Para ver procesos, inicia sesión en http://localhost/" -ForegroundColor DarkYellow
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Host "[WARN] Token inválido o expirado" -ForegroundColor Yellow
        } else {
            Write-Host "[ERROR] No se pudo obtener estado de procesos" -ForegroundColor Red
            Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor DarkRed
        }
    }
    Write-Host ""

    # [4] Uso de Recursos
    Write-Host "[4] Uso de Recursos:" -ForegroundColor Yellow
    try {
        $stats = docker stats sistema_ocr_backend --no-stream --format "{{.CPUPerc}}`t{{.MemUsage}}`t{{.NetIO}}" 2>$null
        if ($stats) {
            $parts = $stats -split "`t"
            Write-Host "    CPU: $($parts[0])" -ForegroundColor Cyan
            Write-Host "    RAM: $($parts[1])" -ForegroundColor Cyan
            Write-Host "    RED: $($parts[2])" -ForegroundColor Cyan
        } else {
            Write-Host "[ERROR] No se pudo obtener estadísticas" -ForegroundColor Red
        }
    } catch {
        Write-Host "[ERROR] Error al obtener estadísticas de Docker" -ForegroundColor Red
    }
    Write-Host ""

    # [5] Últimas líneas del log
    Write-Host "[5] Últimas Líneas del Log:" -ForegroundColor Yellow
    try {
        $logs = docker logs --tail 5 sistema_ocr_backend 2>$null
        if ($logs) {
            $logs | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        } else {
            Write-Host "[ERROR] No se pudieron obtener logs" -ForegroundColor Red
        }
    } catch {
        Write-Host "[ERROR] Error al obtener logs" -ForegroundColor Red
    }
    Write-Host ""

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Actualizando en 10 segundos..." -ForegroundColor DarkGreen
    Write-Host "Presiona Ctrl+C para detener" -ForegroundColor DarkYellow
    Write-Host "========================================" -ForegroundColor Cyan
}

# Loop principal
try {
    while ($true) {
        Get-BackendStatus
        Start-Sleep -Seconds 10
    }
} catch {
    Write-Host ""
    Write-Host "Monitor detenido." -ForegroundColor Yellow
    Write-Host ""
}
