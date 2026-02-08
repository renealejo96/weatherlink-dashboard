##############################################################################
# Script para Subir Código a Hostinger desde Windows
# Uso: .\upload-to-hostinger.ps1
##############################################################################

param(
    [string]$HostingerIP = "",
    [string]$HostingerUser = "root",
    [int]$HostingerPort = 22
)

# Colores
$ColorInfo = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] " -ForegroundColor Gray -NoNewline
    Write-Host $Message -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ " -ForegroundColor $ColorSuccess -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠ " -ForegroundColor $ColorWarning -NoNewline
    Write-Host $Message -ForegroundColor $ColorWarning
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "  ✗ " -ForegroundColor $ColorError -NoNewline
    Write-Host $Message -ForegroundColor $ColorError
}

# Banner
Write-Host "`n╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Upload WeatherLink Dashboard a Hostinger VPS         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Solicitar datos si no se proporcionaron
if (-not $HostingerIP) {
    $HostingerIP = Read-Host "Ingresa la IP de tu VPS Hostinger"
}

if (-not $HostingerIP) {
    Write-Error-Custom "IP del servidor es requerida"
    exit 1
}

$ProjectDir = "D:\todo en vs code\NUEVO DPV\NUEVO DPV"
$RemoteDir = "/var/www/weatherlink"
$TempZip = "$env:TEMP\weatherlink_deploy_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "$ProjectDir\docker-compose.production.yml")) {
    Write-Error-Custom "No se encuentra docker-compose.production.yml en $ProjectDir"
    exit 1
}

# Paso 1: Verificar archivos críticos
Write-Step "Paso 1/6: Verificando archivos críticos..."

$RequiredFiles = @(
    "docker-compose.production.yml",
    "Dockerfile",
    "requirements.txt",
    "app.py",
    "gunicorn_config.py",
    "kafka_producer.py",
    "spark_to_supabase.py",
    "rain_alerts_v2.py",
    "weatherlink_client.py",
    "supabase_api.py",
    "deploy-hostinger.sh"
)

$MissingFiles = @()
foreach ($file in $RequiredFiles) {
    if (Test-Path "$ProjectDir\$file") {
        Write-Success "$file encontrado"
    } else {
        $MissingFiles += $file
        Write-Warning "$file NO encontrado"
    }
}

if ($MissingFiles.Count -gt 0) {
    Write-Error-Custom "Faltan archivos críticos. Deployment puede fallar."
    $continue = Read-Host "¿Continuar de todos modos? (s/n)"
    if ($continue -ne "s") {
        exit 1
    }
}

# Verificar .env
if (-not (Test-Path "$ProjectDir\.env")) {
    Write-Warning "Archivo .env NO encontrado"
    Write-Host "  Deberás crear el archivo .env manualmente en el servidor" -ForegroundColor Yellow
    $continue = Read-Host "¿Continuar? (s/n)"
    if ($continue -ne "s") {
        exit 1
    }
}

# Paso 2: Comprimir archivos
Write-Step "Paso 2/6: Comprimiendo archivos del proyecto..."

$FilesToInclude = @(
    "*.py",
    "*.yml",
    "*.yaml",
    "*.txt",
    "*.md",
    "*.sh",
    "Dockerfile",
    ".dockerignore",
    "templates\*",
    "nginx\nginx.conf",
    "nginx\conf.d\*",
    "sql\*"
)

# Crear lista de exclusión
$ExcludePatterns = @(
    "__pycache__",
    "*.pyc",
    ".git",
    ".venv",
    "venv",
    "logs\*",
    "*.log",
    ".env.example",
    "test_*.py",
    "debug_*.py"
)

try {
    # Cambiar al directorio del proyecto
    Push-Location $ProjectDir
    
    # Crear archivo zip
    $files = Get-ChildItem -Recurse -File | Where-Object {
        $file = $_
        $shouldInclude = $false
        
        foreach ($pattern in $FilesToInclude) {
            if ($file.FullName -like "*$pattern*") {
                $shouldInclude = $true
                break
            }
        }
        
        if ($shouldInclude) {
            foreach ($exclude in $ExcludePatterns) {
                if ($file.FullName -like "*$exclude*") {
                    $shouldInclude = $false
                    break
                }
            }
        }
        
        $shouldInclude
    }
    
    $files | Compress-Archive -DestinationPath $TempZip -Force
    
    Pop-Location
    
    $zipSize = (Get-Item $TempZip).Length / 1MB
    Write-Success "Archivo comprimido: $TempZip ($('{0:N2}' -f $zipSize) MB)"
    
} catch {
    Write-Error-Custom "Error al comprimir archivos: $_"
    exit 1
}

# Paso 3: Copiar .env por separado (si existe)
$EnvFile = "$ProjectDir\.env"
$EnvExists = Test-Path $EnvFile

# Paso 4: Conectividad SSH
Write-Step "Paso 3/6: Verificando conectividad SSH..."

try {
    $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes "${HostingerUser}@${HostingerIP}" -p $HostingerPort "echo OK" 2>&1
    if ($sshTest -like "*OK*") {
        Write-Success "Conexión SSH exitosa"
    } else {
        throw "No se pudo conectar"
    }
} catch {
    Write-Error-Custom "No se pudo conectar al servidor vía SSH"
    Write-Host "  Verifica que:" -ForegroundColor Yellow
    Write-Host "    1. La IP sea correcta: $HostingerIP" -ForegroundColor Yellow
    Write-Host "    2. El puerto SSH esté abierto: $HostingerPort" -ForegroundColor Yellow
    Write-Host "    3. Tienes la clave SSH configurada o acceso con contraseña" -ForegroundColor Yellow
    exit 1
}

# Paso 5: Subir archivos
Write-Step "Paso 4/6: Subiendo archivos al servidor..."

# Crear directorio remoto si no existe
ssh "${HostingerUser}@${HostingerIP}" -p $HostingerPort "mkdir -p $RemoteDir"

# Subir ZIP
Write-Host "  Subiendo código comprimido..." -ForegroundColor Gray
scp -P $HostingerPort $TempZip "${HostingerUser}@${HostingerIP}:$RemoteDir/deploy.zip"

if ($LASTEXITCODE -eq 0) {
    Write-Success "Código subido correctamente"
} else {
    Write-Error-Custom "Error al subir archivos"
    exit 1
}

# Subir .env si existe (separado por seguridad)
if ($EnvExists) {
    Write-Host "  Subiendo archivo .env..." -ForegroundColor Gray
    scp -P $HostingerPort $EnvFile "${HostingerUser}@${HostingerIP}:$RemoteDir/.env"
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Archivo .env subido"
    } else {
        Write-Warning "Error al subir .env. Deberás crearlo manualmente."
    }
}

# Paso 6: Descomprimir en el servidor
Write-Step "Paso 5/6: Descomprimiendo archivos en el servidor..."

$unzipCommand = @"
cd $RemoteDir && \
unzip -o deploy.zip && \
rm deploy.zip && \
chmod +x deploy-hostinger.sh && \
ls -lah
"@

ssh "${HostingerUser}@${HostingerIP}" -p $HostingerPort $unzipCommand

if ($LASTEXITCODE -eq 0) {
    Write-Success "Archivos descomprimidos correctamente"
} else {
    Write-Error-Custom "Error al descomprimir archivos"
}

# Limpiar archivo temporal
Remove-Item $TempZip -Force

# Paso 7: Instrucciones finales
Write-Step "Paso 6/6: Preparando deployment..."

Write-Host "`n╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ARCHIVOS SUBIDOS CORRECTAMENTE                 ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📋 Próximos pasos en el servidor:" -ForegroundColor Cyan
Write-Host "`n1. Conectarse al servidor:" -ForegroundColor White
Write-Host "   ssh ${HostingerUser}@${HostingerIP} -p $HostingerPort`n" -ForegroundColor Gray

Write-Host "2. Ir al directorio del proyecto:" -ForegroundColor White
Write-Host "   cd $RemoteDir`n" -ForegroundColor Gray

if (-not $EnvExists) {
    Write-Host "3. Crear archivo .env con tus variables:" -ForegroundColor White
    Write-Host "   nano .env" -ForegroundColor Gray
    Write-Host "   (Copia el contenido de tu .env local)`n" -ForegroundColor Gray
}

Write-Host "4. Ejecutar el script de deployment:" -ForegroundColor White
Write-Host "   sudo bash deploy-hostinger.sh`n" -ForegroundColor Gray

Write-Host "5. Verificar que todo esté corriendo:" -ForegroundColor White
Write-Host "   docker-compose -f docker-compose.production.yml ps`n" -ForegroundColor Gray

Write-Host "🌐 Una vez desplegado, accede a:" -ForegroundColor Cyan
Write-Host "   http://${HostingerIP}:8080" -ForegroundColor White
Write-Host "   (o el puerto configurado en .env)`n" -ForegroundColor Gray

Write-Success "Upload completado!"
Write-Host "`n"

# Preguntar si quiere conectarse automáticamente
$autoConnect = Read-Host "¿Deseas conectarte al servidor ahora? (s/n)"
if ($autoConnect -eq "s") {
    Write-Host "`nConectando a Hostinger VPS..." -ForegroundColor Cyan
    ssh "${HostingerUser}@${HostingerIP}" -p $HostingerPort -t "cd $RemoteDir; bash"
}
