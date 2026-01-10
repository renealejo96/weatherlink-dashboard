# 📚 Guía: Subir Proyecto a GitHub

## Paso 1: Configurar Git (primera vez)

Abre un **nuevo terminal PowerShell** (para que reconozca Git) y ejecuta:

```powershell
# Configurar tu nombre (se mostrará en los commits)
git config --global user.name "Tu Nombre"

# Configurar tu email
git config --global user.email "tu-email@ejemplo.com"

# Verificar configuración
git config --list
```

## Paso 2: Inicializar Repositorio Local

```powershell
# Ir al directorio del proyecto
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Inicializar Git
git init

# Agregar todos los archivos
git add .

# Ver qué archivos se agregaron
git status

# Hacer el primer commit
git commit -m "Initial commit - WeatherLink Dashboard con Docker"
```

## Paso 3: Crear Repositorio en GitHub

1. Ve a https://github.com/new
2. **Nombre del repositorio**: `weatherlink-dashboard` (o el que prefieras)
3. **Descripción**: Dashboard meteorológico WeatherLink con Docker
4. **Visibilidad**: 
   - ✅ **Private** (recomendado porque tiene credenciales en .env)
   - ⚠️ Public (asegúrate de que .env esté en .gitignore)
5. **NO** marques ninguna opción de inicialización (README, .gitignore, license)
6. Click en **"Create repository"**

## Paso 4: Conectar y Subir a GitHub

GitHub te mostrará instrucciones. Copia la URL de tu repositorio y ejecuta:

```powershell
# Renombrar rama a main
git branch -M main

# Conectar con GitHub (reemplaza con TU URL)
git remote add origin https://github.com/TU-USUARIO/weatherlink-dashboard.git

# Subir al repositorio
git push -u origin main
```

### Si usas autenticación de 2 factores o token:

GitHub ya no permite passwords simples. Necesitas un **Personal Access Token**:

1. Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click en "Generate new token (classic)"
3. Nombre: "VPS Deploy"
4. Scopes: marca `repo` (acceso completo a repositorios)
5. Click en "Generate token"
6. **Copia el token** (solo se muestra una vez)

Cuando hagas `git push`, usa:
- **Username**: tu-usuario-github
- **Password**: el token que copiaste

### Opción SSH (más segura, sin password):

```powershell
# Generar clave SSH
ssh-keygen -t ed25519 -C "tu-email@ejemplo.com"
# Presiona Enter 3 veces (sin passphrase)

# Copiar la clave pública
Get-Content ~/.ssh/id_ed25519.pub | Set-Clipboard

# Pegar en GitHub → Settings → SSH and GPG keys → New SSH key

# Cambiar remote a SSH
git remote set-url origin git@github.com:TU-USUARIO/weatherlink-dashboard.git

# Ahora push sin password
git push -u origin main
```

## Paso 5: Verificar en GitHub

Ve a tu repositorio en GitHub y deberías ver todos los archivos.

⚠️ **IMPORTANTE**: Verifica que el archivo `.env` **NO** aparezca en GitHub (debe estar bloqueado por `.gitignore`)

## 📦 Paso 6: Clonar en el VPS

Una vez subido a GitHub, en tu VPS ejecuta:

```bash
# SSH al VPS
ssh root@tu-ip-vps

# Instalar Git (si no está instalado)
sudo apt update
sudo apt install git -y

# Ir al directorio
cd /var/www

# Clonar repositorio
git clone https://github.com/TU-USUARIO/weatherlink-dashboard.git weatherlink

# Entrar al directorio
cd weatherlink

# Configurar .env (¡importante!)
cp .env.example .env
nano .env
# Pega tus credenciales reales aquí

# Levantar con Docker
docker-compose up -d
```

## 🔄 Actualizar el Código Después

### En tu PC local:
```powershell
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Agregar cambios
git add .

# Commit
git commit -m "Descripción de los cambios"

# Subir a GitHub
git push
```

### En el VPS:
```bash
cd /var/www/weatherlink

# Descargar cambios
git pull

# Reconstruir y reiniciar
docker-compose build
docker-compose up -d
```

## 🎯 Script Rápido de Inicialización

También puedes usar el script automático:

```powershell
# En PowerShell (nuevo terminal)
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Ejecutar script
.\setup-git.ps1
```

## ⚠️ Antes de Hacer Push

Verifica que estos archivos **NO** se suban a GitHub:
- ✅ `.env` está en `.gitignore`
- ✅ `__pycache__/` está en `.gitignore`
- ✅ `.venv/` está en `.gitignore`

Verificar:
```powershell
git status
# NO debe aparecer .env en la lista
```

## 🔐 Seguridad

Si accidentalmente subes el `.env` con credenciales:

1. **Inmediatamente** regenera tus API keys en WeatherLink
2. Elimina el archivo del historial:
```powershell
git rm --cached .env
git commit -m "Remove .env from repository"
git push
```

3. Usa BFG Repo-Cleaner para limpiar el historial completo

---

¡Listo! Ahora tu código estará en GitHub y podrás desplegarlo fácilmente en tu VPS.
