# Script para reiniciar el servicio de alertas de lluvia
# Asegura que los nuevos cambios (30 minutos de umbral) se apliquen

Write-Host "Reiniciando Sistema de Alertas de Lluvia v2.0" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Detener procesos existentes de rain_alerts_v2
Write-Host "`nBuscando procesos existentes..." -ForegroundColor Yellow
$processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like "*rain_alerts_v2.py*"
}

if ($processes) {
    Write-Host "   Encontrados $($processes.Count) proceso(s) activo(s)" -ForegroundColor Yellow
    foreach ($proc in $processes) {
        Write-Host "   Deteniendo proceso ID: $($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
    }
    Write-Host "   Procesos detenidos" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "   No hay procesos activos de rain_alerts_v2" -ForegroundColor Gray
}

# Verificar que Docker/Redpanda este corriendo
Write-Host "`nVerificando Docker y Kafka/Redpanda..." -ForegroundColor Cyan
$dockerRunning = docker ps --filter "name=redpanda" --format "{{.Names}}" 2>$null

if ($dockerRunning -like "*redpanda*") {
    Write-Host "   Redpanda esta corriendo" -ForegroundColor Green
} else {
    Write-Host "   Redpanda no esta corriendo. Iniciando contenedores..." -ForegroundColor Yellow
    docker-compose up -d
    Start-Sleep -Seconds 5
}

# Iniciar el servicio de alertas de lluvia
Write-Host "`nIniciando rain_alerts_v2.py..." -ForegroundColor Cyan
Write-Host "   Configuracion:" -ForegroundColor Gray
Write-Host "      - Umbral de deteccion: 0.1 mm" -ForegroundColor Gray
Write-Host "      - Timeout sin lluvia: 30 minutos (ACTUALIZADO)" -ForegroundColor Green
Write-Host "      - Kafka topic: weatherlink.raw" -ForegroundColor Gray

# Iniciar en una nueva ventana de PowerShell
$pythonPath = "D:\todo en vs code\NUEVO DPV\.venv\Scripts\python.exe"
$scriptPath = "D:\todo en vs code\NUEVO DPV\NUEVO DPV\rain_alerts_v2.py"

Start-Process -FilePath $pythonPath -ArgumentList $scriptPath -WindowStyle Normal

Write-Host "`n   Servicio iniciado en nueva ventana" -ForegroundColor Green
Write-Host "`nIMPORTANTE: El servicio ahora usa un umbral de 30 minutos" -ForegroundColor Yellow
Write-Host "   Esto significa que un evento se cerrara automaticamente" -ForegroundColor Gray
Write-Host "   despues de 30 minutos sin incremento de lluvia." -ForegroundColor Gray

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "Proceso completado" -ForegroundColor Green
