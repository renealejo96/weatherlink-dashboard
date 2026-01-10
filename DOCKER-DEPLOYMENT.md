# 🐳 Guía de Despliegue con Docker - WeatherLink Dashboard

## 📋 Requisitos Previos
- VPS con Ubuntu 20.04/22.04 o Debian
- Acceso SSH root o sudo
- Dominio o subdominio apuntando a la IP del VPS (opcional)
- Docker y Docker Compose instalados

## 🚀 Paso 1: Conectarse al VPS
```bash
ssh root@tu-ip-del-vps
```

## 📦 Paso 2: Instalar Docker y Docker Compose

### Instalar Docker
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Agregar la clave GPG oficial de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Agregar el repositorio de Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Verificar instalación
sudo docker --version
```

### Instalar Docker Compose
```bash
# Descargar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker-compose --version
```

### Configurar usuario para Docker (opcional)
```bash
# Agregar usuario actual al grupo docker
sudo usermod -aG docker $USER

# Aplicar cambios (o cerrar sesión y volver a entrar)
newgrp docker
```

## 📁 Paso 3: Preparar el Directorio de la Aplicación
```bash
# Crear directorio
sudo mkdir -p /var/www/weatherlink
cd /var/www/weatherlink
```

## 📤 Paso 4: Subir la Aplicación al VPS

### Opción A: Usando Git (Recomendado)
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/tu-repo.git .

# O si ya tienes Git configurado
git init
git remote add origin https://github.com/tu-usuario/tu-repo.git
git pull origin main
```

### Opción B: Usando SCP desde tu PC local
Desde tu computadora Windows (PowerShell):
```powershell
# Comprimir tu proyecto (excluir venv y pycache)
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"
tar -czf weatherlink.tar.gz --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' .

# Subir al VPS
scp weatherlink.tar.gz root@tu-ip-del-vps:/var/www/weatherlink/

# En el VPS, descomprimir
cd /var/www/weatherlink
tar -xzf weatherlink.tar.gz
rm weatherlink.tar.gz
```

### Opción C: Usando rsync (más eficiente)
Desde tu PC local (PowerShell con WSL o Git Bash):
```bash
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  "D:\todo en vs code\NUEVO DPV\NUEVO DPV/" \
  root@tu-ip-del-vps:/var/www/weatherlink/
```

## 🔐 Paso 5: Configurar Variables de Entorno
```bash
cd /var/www/weatherlink

# Copiar el archivo de ejemplo
cp .env.example .env

# Editar el archivo .env
nano .env
```

Pega tus credenciales reales:
```env
# Finca 1 - PYGANFLOR
FINCA1_API_KEY=ljhgrfizwlad3hose74hycpa0jn1t4rz
FINCA1_API_SECRET=t9yutftlg7eddypqv9kocdpmtu9mwyhy
FINCA1_STATION_ID=167591

# Finca 2 - Urcuquí
FINCA2_API_KEY=hrd0nyzmwv5esftiktab7nsgazmi6zp8
FINCA2_API_SECRET=ezvvdmdxxqeraoiltf8ulwn55tglktxm
FINCA2_STATION_ID=209314

# Finca 3 - Malchinguí
FINCA3_API_KEY=mczqougmw56ggwopbodwsvy20oyn38sh
FINCA3_API_SECRET=frvgyvxki0vel9vbkeydnnvbhixyt5ji
FINCA3_STATION_ID=219603

# Secret Key para Flask (generado)
SECRET_KEY=tu_secret_key_super_seguro_aqui
```

Guardar con `Ctrl+X`, luego `Y`, luego `Enter`

## 🎨 Paso 6: Configurar Nginx para tu Dominio/Subdominio
```bash
# Editar configuración de Nginx
nano nginx/conf.d/weatherlink.conf
```

Cambiar `server_name _;` por tu dominio o subdominio:
```nginx
server_name weather.tudominio.com;
```

## 📁 Paso 7: Crear Directorios Necesarios
```bash
cd /var/www/weatherlink

# Crear directorios para logs y SSL
mkdir -p logs nginx/logs nginx/ssl

# Establecer permisos
chmod -R 755 nginx
```

## 🐳 Paso 8: Construir y Levantar los Contenedores
```bash
cd /var/www/weatherlink

# Construir la imagen
docker-compose build

# Levantar los contenedores en background
docker-compose up -d

# Ver los logs
docker-compose logs -f
```

## ✅ Paso 9: Verificar que Todo Funciona
```bash
# Ver estado de los contenedores
docker-compose ps

# Debería mostrar:
# NAME                  STATUS    PORTS
# weatherlink_app       Up        127.0.0.1:8000->8000/tcp
# weatherlink_nginx     Up        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp

# Ver logs en tiempo real
docker-compose logs -f weatherlink

# Probar la aplicación
curl http://localhost
```

Ahora abre tu navegador y ve a:
- `http://tu-dominio.com`
- `http://tu-ip-del-vps`

## 🔒 Paso 10: Configurar SSL con Let's Encrypt (Recomendado)

### Método 1: Usando Certbot en el host (más fácil)
```bash
# Instalar certbot
sudo apt install certbot -y

# Detener temporalmente Nginx
docker-compose stop nginx

# Obtener certificados
sudo certbot certonly --standalone -d weather.tudominio.com

# Los certificados estarán en:
# /etc/letsencrypt/live/weather.tudominio.com/

# Copiar certificados al directorio de nginx
sudo cp /etc/letsencrypt/live/weather.tudominio.com/fullchain.pem /var/www/weatherlink/nginx/ssl/
sudo cp /etc/letsencrypt/live/weather.tudominio.com/privkey.pem /var/www/weatherlink/nginx/ssl/

# Dar permisos
sudo chmod 644 /var/www/weatherlink/nginx/ssl/*.pem

# Editar nginx/conf.d/weatherlink.conf y descomentar la sección HTTPS
nano nginx/conf.d/weatherlink.conf

# Reiniciar contenedores
docker-compose up -d

# Configurar renovación automática
echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/weather.tudominio.com/*.pem /var/www/weatherlink/nginx/ssl/ && docker-compose -f /var/www/weatherlink/docker-compose.yml restart nginx" | sudo crontab -
```

### Método 2: Usando Nginx Proxy Manager (más visual)
```bash
# Instalar Nginx Proxy Manager en otro puerto
cd /opt
sudo mkdir npm && cd npm

# Crear docker-compose.yml para NPM
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  npm:
    image: 'jc21/nginx-proxy-manager:latest'
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
EOF

# Levantar NPM
sudo docker-compose up -d

# Acceder a http://tu-ip:81
# Usuario: admin@example.com
# Password: changeme
```

## 🔄 Comandos Útiles de Docker

### Gestión de Contenedores
```bash
cd /var/www/weatherlink

# Ver contenedores corriendo
docker-compose ps

# Ver logs
docker-compose logs -f
docker-compose logs -f weatherlink  # Solo app
docker-compose logs -f nginx        # Solo nginx

# Reiniciar servicios
docker-compose restart
docker-compose restart weatherlink
docker-compose restart nginx

# Detener servicios
docker-compose stop

# Iniciar servicios
docker-compose start

# Detener y eliminar contenedores
docker-compose down

# Reconstruir y reiniciar
docker-compose up -d --build
```

### Actualizar la Aplicación
```bash
cd /var/www/weatherlink

# Si usas Git
git pull

# Reconstruir imagen
docker-compose build

# Reiniciar con nueva imagen
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### Acceder al contenedor
```bash
# Entrar al contenedor de la app
docker-compose exec weatherlink bash

# Entrar al contenedor de nginx
docker-compose exec nginx sh
```

### Limpiar recursos de Docker
```bash
# Eliminar contenedores detenidos
docker container prune -f

# Eliminar imágenes no usadas
docker image prune -a -f

# Eliminar volúmenes no usados
docker volume prune -f

# Limpiar todo (cuidado!)
docker system prune -a -f
```

## 🔥 Configurar Firewall
```bash
# Si usas UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status
```

## 📊 Monitoreo

### Ver uso de recursos
```bash
# Ver estadísticas de contenedores
docker stats

# Ver logs del sistema
journalctl -f

# Ver espacio en disco
df -h
docker system df
```

### Healthcheck
```bash
# Verificar salud de los contenedores
docker-compose ps

# El healthcheck está configurado en docker-compose.yml
# Se ejecuta cada 30 segundos
```

## 🔄 Backup y Restauración

### Crear Backup
```bash
# Backup de .env y configuraciones
cd /var/www
tar -czf weatherlink-backup-$(date +%Y%m%d).tar.gz \
  weatherlink/.env \
  weatherlink/nginx/conf.d/ \
  weatherlink/nginx/ssl/

# Mover a ubicación segura
mv weatherlink-backup-*.tar.gz ~/backups/
```

### Restaurar Backup
```bash
cd /var/www
tar -xzf ~/backups/weatherlink-backup-YYYYMMDD.tar.gz
docker-compose restart
```

## 🎯 Integrar con Otra App Existente

Si ya tienes otra aplicación corriendo en el puerto 80/443:

### Opción 1: Usar diferentes subdominios
```nginx
# App existente: app1.tudominio.com
# WeatherLink: weather.tudominio.com

# En nginx/conf.d/weatherlink.conf
server_name weather.tudominio.com;
```

### Opción 2: Usar paths diferentes
```bash
# Modificar docker-compose.yml para que no exponga puertos 80/443
# Dejar solo el puerto 8000

# En tu Nginx principal del VPS, agregar:
location /weather/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Opción 3: Usar Nginx Proxy Manager o Traefik
```bash
# NPM gestiona automáticamente múltiples apps
# con diferentes dominios y certificados SSL
```

## 🐛 Solución de Problemas

### Los contenedores no inician
```bash
# Ver logs
docker-compose logs

# Verificar sintaxis del docker-compose.yml
docker-compose config

# Verificar puerto 80 no esté ocupado
sudo netstat -tulpn | grep :80
```

### Error 502 Bad Gateway
```bash
# Verificar que weatherlink esté corriendo
docker-compose ps

# Ver logs de la app
docker-compose logs weatherlink

# Reiniciar contenedores
docker-compose restart
```

### Cambios no se reflejan
```bash
# Reconstruir imagen
docker-compose build --no-cache

# Reiniciar
docker-compose up -d
```

### Problemas de permisos
```bash
# Ajustar permisos
sudo chown -R $USER:$USER /var/www/weatherlink
chmod -R 755 /var/www/weatherlink
```

## 🚀 Script de Despliegue Rápido

Crea un archivo `deploy.sh`:
```bash
#!/bin/bash
cd /var/www/weatherlink
git pull
docker-compose build
docker-compose up -d
docker-compose logs -f
```

Hazlo ejecutable:
```bash
chmod +x deploy.sh
./deploy.sh
```

## 📱 Acceso desde Cualquier Dispositivo

Una vez desplegado:
- Web: `https://weather.tudominio.com`
- Móvil: `https://weather.tudominio.com`
- Tablet: `https://weather.tudominio.com`

## 💡 Ventajas de Docker

1. **Aislamiento**: Cada app en su propio contenedor
2. **Portabilidad**: Funciona igual en desarrollo y producción
3. **Fácil actualización**: Solo rebuild y restart
4. **Rollback rápido**: Volver a versión anterior fácilmente
5. **Escalabilidad**: Agregar más workers con un comando
6. **Múltiples apps**: Correr varias apps sin conflictos

---

## 🆘 Necesitas Ayuda?

1. Revisa logs: `docker-compose logs -f`
2. Verifica estado: `docker-compose ps`
3. Revisa configuración: `docker-compose config`
4. Verifica recursos: `docker stats`

---

¡Tu aplicación WeatherLink Dashboard está corriendo en Docker! 🐳🎉
