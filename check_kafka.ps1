#!/usr/bin/env pwsh
# Script para verificar el estado de Kafka y el flujo de datos

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "📊 VERIFICACIÓN DE KAFKA Y FLUJO DE DATOS" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# 1. Ver logs del productor
Write-Host "🔹 1. LOGS DEL PRODUCTOR KAFKA (últimas 10 líneas)" -ForegroundColor Yellow
Write-Host "-" -ForegroundColor Gray -NoNewline; Write-Host ("-" * 79) -ForegroundColor Gray
docker logs kafka_producer --tail 10
Write-Host ""

# 2. Listar topics
Write-Host "🔹 2. TOPICS DISPONIBLES EN KAFKA" -ForegroundColor Yellow
Write-Host "-" -ForegroundColor Gray -NoNewline; Write-Host ("-" * 79) -ForegroundColor Gray
docker exec redpanda rpk topic list
Write-Host ""

# 3. Ver último mensaje
Write-Host "🔹 3. ÚLTIMO MENSAJE EN EL TOPIC 'weatherlink.raw'" -ForegroundColor Yellow
Write-Host "-" -ForegroundColor Gray -NoNewline; Write-Host ("-" * 79) -ForegroundColor Gray
$message = docker exec redpanda rpk topic consume weatherlink.raw --num 1 --offset -1 2>$null
if ($message) {
    $message | ConvertFrom-Json | ConvertTo-Json -Depth 10
} else {
    Write-Host "⚠️  No hay mensajes aún" -ForegroundColor Yellow
}
Write-Host ""

# 4. Estadísticas del topic
Write-Host "🔹 4. ESTADÍSTICAS DEL TOPIC" -ForegroundColor Yellow
Write-Host "-" -ForegroundColor Gray -NoNewline; Write-Host ("-" * 79) -ForegroundColor Gray
docker exec redpanda rpk topic describe weatherlink.raw
Write-Host ""

# 5. Estado de contenedores
Write-Host "🔹 5. ESTADO DE CONTENEDORES" -ForegroundColor Yellow
Write-Host "-" -ForegroundColor Gray -NoNewline; Write-Host ("-" * 79) -ForegroundColor Gray
docker ps --format "table {{.Names}}\t{{.Status}}" --filter name=kafka_producer --filter name=redpanda --filter name=spark_streaming
Write-Host ""

# 6. Resumen
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "📋 RESUMEN" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Verificar si hay mensajes con ✔
$successLogs = docker logs kafka_producer --tail 5 | Select-String "✔"
if ($successLogs) {
    Write-Host "✅ Kafka Producer está enviando datos correctamente" -ForegroundColor Green
    Write-Host "   Últimos envíos:" -ForegroundColor Gray
    foreach ($log in $successLogs) {
        Write-Host "   $log" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ Kafka Producer no está enviando datos" -ForegroundColor Red
}
Write-Host ""

# Verificar errores
$errorLogs = docker logs kafka_producer --tail 10 | Select-String "⚠|Error"
if ($errorLogs) {
    Write-Host "⚠️  Se encontraron algunos errores:" -ForegroundColor Yellow
    foreach ($log in $errorLogs) {
        Write-Host "   $log" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Sin errores en los últimos logs" -ForegroundColor Green
}
Write-Host ""

Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "COMANDOS UTILES:" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan -NoNewline; Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Ver logs en tiempo real:" -ForegroundColor Gray
Write-Host "  docker logs -f kafka_producer" -ForegroundColor White
Write-Host ""
Write-Host "  # Consumir mensajes en tiempo real:" -ForegroundColor Gray
Write-Host "  docker exec redpanda rpk topic consume weatherlink.raw" -ForegroundColor White
Write-Host ""
Write-Host "  # Ver este resumen de nuevo:" -ForegroundColor Gray
Write-Host "  .\check_kafka.ps1" -ForegroundColor White
Write-Host ""
