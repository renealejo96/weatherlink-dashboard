# Script para mover Docker Desktop al disco D:
# EJECUTA ESTE SCRIPT COMO ADMINISTRADOR

Write-Host "=== MOVIENDO DOCKER DESKTOP AL DISCO D: ===" -ForegroundColor Cyan
Write-Host ""

# Verificar si Docker esta corriendo
$dockerRunning = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerRunning) {
    Write-Host "[X] Docker Desktop esta corriendo. Por favor:" -ForegroundColor Red
    Write-Host "   1. Click derecho en el icono de Docker en la bandeja" -ForegroundColor Yellow
    Write-Host "   2. Selecciona 'Quit Docker Desktop'" -ForegroundColor Yellow
    Write-Host "   3. Vuelve a ejecutar este script" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presiona Enter para salir"
    exit
}

# Crear directorio en D:
$destinoDocker = "D:\Docker"
if (-not (Test-Path $destinoDocker)) {
    Write-Host "[+] Creando directorio $destinoDocker..." -ForegroundColor Green
    New-Item -ItemType Directory -Path $destinoDocker -Force | Out-Null
}

# Directorio de WSL en C:
$wslDir = "$env:LOCALAPPDATA\Docker\wsl"
if (-not (Test-Path $wslDir)) {
    Write-Host "[!] No se encontro $wslDir" -ForegroundColor Yellow
    Write-Host "   Docker puede estar instalado en otra ubicacion" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Presiona Enter para ver ubicaciones alternativas..." -ForegroundColor Cyan
    Read-Host
    
    # Buscar ubicaciones alternativas
    $posibles = @(
        "$env:USERPROFILE\AppData\Local\Docker",
        "$env:ProgramData\Docker",
        "C:\ProgramData\DockerDesktop"
    )
    
    foreach ($path in $posibles) {
        if (Test-Path $path) {
            Write-Host "[OK] Encontrado: $path" -ForegroundColor Green
        }
    }
    exit
}

Write-Host "[*] Ubicacion actual de Docker: $wslDir" -ForegroundColor Cyan
Write-Host ""

# Exportar distribuciones WSL
Write-Host "[+] Exportando distribuciones WSL..." -ForegroundColor Green
Write-Host "   Esto puede tomar varios minutos..." -ForegroundColor Yellow

$exportDir = "$destinoDocker\export"
New-Item -ItemType Directory -Path $exportDir -Force | Out-Null

# Listar distribuciones
$distros = wsl --list --quiet
foreach ($distro in $distros) {
    if ($distro -match "docker") {
        $distro = $distro.Trim()
        Write-Host "   Exportando $distro..." -ForegroundColor Cyan
        wsl --export $distro "$exportDir\$distro.tar"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   [OK] $distro exportado" -ForegroundColor Green
            
            # Des-registrar la distribucion antigua
            Write-Host "   [-] Des-registrando $distro del disco C..." -ForegroundColor Yellow
            wsl --unregister $distro
            
            # Importar en nueva ubicacion
            Write-Host "   [+] Importando $distro al disco D..." -ForegroundColor Cyan
            wsl --import $distro "$destinoDocker\$distro" "$exportDir\$distro.tar" --version 2
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   [OK] $distro movido exitosamente" -ForegroundColor Green
            } else {
                Write-Host "   [X] Error al importar $distro" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "[+] Limpiando archivos temporales..." -ForegroundColor Green
Remove-Item -Path $exportDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[OK] PROCESO COMPLETADO!" -ForegroundColor Green
Write-Host ""
Write-Host "Ahora puedes:" -ForegroundColor Cyan
Write-Host "   1. Iniciar Docker Desktop" -ForegroundColor Yellow
Write-Host "   2. Verificar que funciona correctamente" -ForegroundColor Yellow
Write-Host "   3. Ejecutar: docker system df" -ForegroundColor Yellow
Write-Host ""
Write-Host "Espacio liberado en C: y ahora Docker usa D:\Docker" -ForegroundColor Green
Write-Host ""
Read-Host "Presiona Enter para salir"
