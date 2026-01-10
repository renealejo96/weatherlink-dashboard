# Script de configuración e inicialización de Git
# Ejecutar este script después de reiniciar el terminal

# Configurar Git (cambiar con tus datos)
Write-Host "Configurando Git..." -ForegroundColor Green
git config --global user.name "renealejo96"
git config --global user.email "renesc.1996@gmail.com"

# Navegar al directorio del proyecto
Set-Location "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Inicializar repositorio Git
Write-Host "`nInicializando repositorio Git..." -ForegroundColor Green
git init

# Agregar todos los archivos (excepto los del .gitignore)
Write-Host "`nAgregando archivos al staging area..." -ForegroundColor Green
git add .

# Ver el estado
Write-Host "`nEstado del repositorio:" -ForegroundColor Yellow
git status

# Hacer el primer commit
Write-Host "`nCreando primer commit..." -ForegroundColor Green
git commit -m "Initial commit - WeatherLink Dashboard con Docker"

Write-Host "`n✅ Repositorio Git inicializado correctamente!" -ForegroundColor Green
Write-Host "`nPróximos pasos:" -ForegroundColor Cyan
Write-Host "1. Crea un repositorio en GitHub (https://github.com/new)" -ForegroundColor White
Write-Host "2. Ejecuta estos comandos (reemplaza con tu URL):" -ForegroundColor White
Write-Host "   git branch -M main" -ForegroundColor Yellow
Write-Host "   git remote add origin https://github.com/tu-usuario/tu-repo.git" -ForegroundColor Yellow
Write-Host "   git push -u origin main" -ForegroundColor Yellow
