# Guía de Despliegue - WeatherLink Dashboard en VPS Hostinger

## 📋 Requisitos Previos
- VPS con Ubuntu 20.04/22.04 o Debian
- Acceso SSH root o sudo
- Dominio apuntando a la IP del VPS (opcional pero recomendado)

## 🚀 Paso 1: Conectarse al VPS
```bash
ssh root@tu-ip-del-vps
# o
ssh tu-usuario@tu-ip-del-vps
```

## 📦 Paso 2: Instalar Dependencias del Sistema
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3 y herramientas necesarias
sudo apt install python3 python3-pip python3-venv nginx git -y

# Crear usuario para la aplicación (opcional, más seguro)
sudo useradd -m -s /bin/bash weatherlink
```

## 📁 Paso 3: Configurar el Directorio de la Aplicación
```bash
# Crear directorio
sudo mkdir -p /var/www/weatherlink
sudo chown -R www-data:www-data /var/www/weatherlink

# Cambiar al directorio
cd /var/www/weatherlink
```

## 📤 Paso 4: Subir la Aplicación al VPS

### Opción A: Usando Git (Recomendado)
```bash
# Si tienes tu código en GitHub/GitLab
sudo -u www-data git clone https://github.com/tu-usuario/tu-repo.git .
```

### Opción B: Usando SCP desde tu PC local
Desde tu computadora Windows (PowerShell):
```powershell
# Comprimir tu proyecto
Compress-Archive -Path "D:\todo en vs code\NUEVO DPV\NUEVO DPV\*" -DestinationPath weatherlink.zip

# Subir al VPS
scp weatherlink.zip root@tu-ip-del-vps:/var/www/weatherlink/

# En el VPS, descomprimir
sudo apt install unzip -y
cd /var/www/weatherlink
sudo unzip weatherlink.zip
sudo rm weatherlink.zip
sudo chown -R www-data:www-data /var/www/weatherlink
```

### Opción C: Usando FileZilla o WinSCP
1. Conectar via SFTP a tu VPS
2. Subir todos los archivos a `/var/www/weatherlink/`

## 🐍 Paso 5: Crear Entorno Virtual e Instalar Dependencias
```bash
cd /var/www/weatherlink

# Crear entorno virtual
sudo -u www-data python3 -m venv venv

# Activar entorno virtual
sudo -u www-data venv/bin/pip install --upgrade pip

# Instalar dependencias
sudo -u www-data venv/bin/pip install -r requirements.txt
```

## 🔐 Paso 6: Configurar Variables de Entorno
```bash
# Copiar el archivo de ejemplo
sudo -u www-data cp .env.example .env

# Editar el archivo .env con tus credenciales
sudo nano .env
```

Pega tus credenciales reales (las que tienes en tu .env local):
```env
FINCA1_API_KEY=ljhgrfizwlad3hose74hycpa0jn1t4rz
FINCA1_API_SECRET=t9yutftlg7eddypqv9kocdpmtu9mwyhy
FINCA1_STATION_ID=167591

FINCA2_API_KEY=hrd0nyzmwv5esftiktab7nsgazmi6zp8
FINCA2_API_SECRET=ezvvdmdxxqeraoiltf8ulwn55tglktxm
FINCA2_STATION_ID=209314

FINCA3_API_KEY=mczqougmw56ggwopbodwsvy20oyn38sh
FINCA3_API_SECRET=frvgyvxki0vel9vbkeydnnvbhixyt5ji
FINCA3_STATION_ID=219603

# Generar un SECRET_KEY seguro
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
```

Guardar con `Ctrl+X`, luego `Y`, luego `Enter`

## 📝 Paso 7: Crear Directorios de Logs
```bash
sudo mkdir -p /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/gunicorn
```

## ⚙️ Paso 8: Configurar Systemd Service
```bash
# Copiar el archivo de servicio
sudo cp /var/www/weatherlink/weatherlink.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar el servicio para que inicie al arrancar
sudo systemctl enable weatherlink

# Iniciar el servicio
sudo systemctl start weatherlink

# Verificar el estado
sudo systemctl status weatherlink
```

## 🌐 Paso 9: Configurar Nginx
```bash
# Copiar configuración de Nginx
sudo cp /var/www/weatherlink/nginx_weatherlink.conf /etc/nginx/sites-available/weatherlink

# Editar el archivo para cambiar el dominio
sudo nano /etc/nginx/sites-available/weatherlink
# Cambiar "tu-dominio.com" por tu dominio real o IP

# Crear enlace simbólico
sudo ln -s /etc/nginx/sites-available/weatherlink /etc/nginx/sites-enabled/

# Eliminar configuración por defecto (opcional)
sudo rm /etc/nginx/sites-enabled/default

# Verificar configuración
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

## 🔒 Paso 10: Configurar SSL con Let's Encrypt (Opcional pero Recomendado)
```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado SSL
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com

# El certificado se renovará automáticamente
```

## 🔥 Paso 11: Configurar Firewall
```bash
# Si usas UFW
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

## ✅ Paso 12: Verificar que Todo Funciona
```bash
# Ver logs de Gunicorn
sudo journalctl -u weatherlink -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/weatherlink_error.log

# Verificar estado del servicio
sudo systemctl status weatherlink
```

Ahora abre tu navegador y ve a:
- `http://tu-dominio.com` (o `http://tu-ip-del-vps`)
- Si configuraste SSL: `https://tu-dominio.com`

## 🔄 Comandos Útiles de Mantenimiento

### Actualizar la Aplicación
```bash
cd /var/www/weatherlink
sudo -u www-data git pull  # Si usas Git
sudo systemctl restart weatherlink
```

### Ver Logs
```bash
# Logs de la aplicación
sudo journalctl -u weatherlink -n 100 --no-pager

# Logs en tiempo real
sudo journalctl -u weatherlink -f

# Logs de Gunicorn
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Logs de Nginx
sudo tail -f /var/log/nginx/weatherlink_error.log
sudo tail -f /var/log/nginx/weatherlink_access.log
```

### Reiniciar Servicios
```bash
# Reiniciar la aplicación
sudo systemctl restart weatherlink

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver estado
sudo systemctl status weatherlink
sudo systemctl status nginx
```

### Actualizar Dependencias
```bash
cd /var/www/weatherlink
sudo -u www-data venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl restart weatherlink
```

## 🐛 Solución de Problemas

### La aplicación no inicia
```bash
# Ver logs detallados
sudo journalctl -u weatherlink -n 50

# Verificar que el puerto 8000 no esté en uso
sudo netstat -tulpn | grep 8000

# Verificar permisos
ls -la /var/www/weatherlink
```

### Error 502 Bad Gateway
```bash
# Verificar que Gunicorn esté corriendo
sudo systemctl status weatherlink

# Verificar configuración de Nginx
sudo nginx -t
```

### La aplicación es lenta
```bash
# Ajustar número de workers en gunicorn_config.py
sudo nano /var/www/weatherlink/gunicorn_config.py
# Cambiar el número de workers

sudo systemctl restart weatherlink
```

## 📊 Monitoreo

### Verificar uso de recursos
```bash
# Ver procesos de Python
ps aux | grep gunicorn

# Ver uso de memoria
free -h

# Ver uso de CPU
top
```

## 🔐 Seguridad Adicional (Recomendado)

### Cambiar puerto SSH (opcional)
```bash
sudo nano /etc/ssh/sshd_config
# Cambiar Port 22 a otro puerto
sudo systemctl restart sshd
```

### Configurar Fail2Ban
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 📱 Acceso desde Cualquier Dispositivo

Una vez desplegado, podrás acceder a tu dashboard desde:
- Cualquier computadora: `https://tu-dominio.com`
- Tablet o móvil: `https://tu-dominio.com`
- Cualquier red WiFi o datos móviles

## 💡 Consejos Finales

1. **Hacer backups regulares** de tu archivo `.env` y base de datos si la añades
2. **Monitorear logs** regularmente para detectar problemas
3. **Actualizar el sistema** periódicamente: `sudo apt update && sudo apt upgrade`
4. **Usar un dominio** en lugar de IP para mejor accesibilidad
5. **Configurar SSL** siempre para seguridad (es gratis con Let's Encrypt)

---

## 🆘 ¿Necesitas Ayuda?

Si encuentras algún problema:
1. Revisa los logs: `sudo journalctl -u weatherlink -n 100`
2. Verifica que todos los servicios estén corriendo
3. Asegúrate de que las variables de entorno estén configuradas correctamente
4. Verifica que el firewall permita el tráfico HTTP/HTTPS

---

¡Tu aplicación WeatherLink Dashboard ya está en producción! 🎉
