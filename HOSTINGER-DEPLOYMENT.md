# 🚀 Despliegue en Producción - Hostinger VPS con Docker

**Guía completa para desplegar WeatherLink Dashboard en Hostinger VPS usando Docker**

---

## 📋 Pre-requisitos

### En tu VPS de Hostinger:
- ✅ Ubuntu 20.04/22.04 o Debian
- ✅ Acceso SSH (usuario root o sudo)
- ✅ Al menos 2GB RAM, 2 CPU cores
- ✅ 20GB espacio en disco
- ✅ Docker y Docker Compose instalados

### En tu PC Local:
- ✅ Git instalado
- ✅ Acceso SSH al VPS
- ✅ Variables de entorno configuradas (archivo `.env`)

---

## 🔐 Paso 1: Backup de la Aplicación Actual (IMPORTANTE)

**Antes de hacer cualquier cambio, respalda lo que tienes corriendo:**

```bash
# Conectar a Hostinger VPS
ssh tu-usuario@tu-ip-hostinger

# Crear directorio de backup
mkdir -p ~/backups/weatherlink_$(date +%Y%m%d_%H%M%S)

# Si ya tienes una app corriendo, hacer backup
cd /ruta/de/tu/app/actual
tar -czf ~/backups/weatherlink_$(date +%Y%m%d_%H%M%S)/app_backup.tar.gz .

# Si estás usando Docker, guardar contenedores actuales
docker ps -a > ~/backups/weatherlink_$(date +%Y%m%d_%H%M%S)/containers_list.txt
docker images > ~/backups/weatherlink_$(date +%Y%m%d_%H%M%S)/images_list.txt

# Backup de datos (si aplica)
docker exec tu-contenedor-actual tar -czf /tmp/data_backup.tar.gz /app/logs 2>/dev/null || true
docker cp tu-contenedor-actual:/tmp/data_backup.tar.gz ~/backups/weatherlink_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
```

---

## 📦 Paso 2: Preparar el Código para Producción

### 2.1. Crear archivo `.env.production` en tu PC

**Copia tu `.env` actual y ajusta para producción:**

```bash
# API Keys de WeatherLink (MANTENER LAS MISMAS)
FINCA1_API_KEY=tu_api_key_finca1
FINCA1_API_SECRET=tu_api_secret_finca1
FINCA1_STATION_ID=tu_station_id_finca1

FINCA2_API_KEY=tu_api_key_finca2
FINCA2_API_SECRET=tu_api_secret_finca2
FINCA2_STATION_ID=tu_station_id_finca2

FINCA3_API_KEY=tu_api_key_finca3
FINCA3_API_SECRET=tu_api_secret_finca3
FINCA3_STATION_ID=tu_station_id_finca3

# Supabase (MANTENER LAS MISMAS)
SUPABASE_URL=tu_supabase_url
SUPABASE_KEY=tu_supabase_key

# Kafka (Cambiar a nombres de producción)
KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
KAFKA_TOPIC_RAW=weatherlink.raw
KAFKA_TOPIC_PROCESSED=weatherlink.processed

# Flask (IMPORTANTE: Cambiar SECRET_KEY en producción)
SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production

# Puertos (Ajustar si ya tienes algo en estos puertos)
HOST_PORT=8080
REDPANDA_PORT=19092
REDPANDA_ADMIN_PORT=19644
NGINX_PORT=80
NGINX_SSL_PORT=443
```

### 2.2. Preparar archivos para producción

Hemos creado archivos específicos para producción:

✅ **Archivos creados:**
- `docker-compose.production.yml` - Configuración Docker para producción
- `.env.production.example` - Template de variables de entorno
- `upload-to-hostinger.ps1` - Script de Windows para subir código
- `deploy-hostinger.sh` - Script de deployment en el servidor

---

## 🚀 Paso 3: Deployment Automatizado (RECOMENDADO)

### 3.1. Desde Windows (tu PC)

**Ejecuta el script de upload:**

```powershell
# Abre PowerShell en el directorio del proyecto
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Ejecuta el script (te pedirá la IP de Hostinger)
.\upload-to-hostinger.ps1

# O especifica la IP directamente:
.\upload-to-hostinger.ps1 -HostingerIP "123.45.67.89" -HostingerUser "root"
```

**El script hará:**
1. ✅ Verificar archivos necesarios
2. ✅ Comprimir el proyecto
3. ✅ Subir archivos al servidor via SCP
4. ✅ Descomprimir en el servidor
5. ✅ Preparar para deployment

### 3.2. En el servidor Hostinger

**Después del upload, conéctate al servidor:**

```bash
ssh root@tu-ip-hostinger
cd /var/www/weatherlink
```

**Ejecuta el script de deployment:**

```bash
# Dar permisos de ejecución
chmod +x deploy-hostinger.sh

# Ejecutar deployment
sudo bash deploy-hostinger.sh
```

**El script hará:**
1. ✅ Backup automático de la app existente
2. ✅ Detener servicios actuales
3. ✅ Limpiar recursos Docker antiguos
4. ✅ Construir nuevas imágenes
5. ✅ Iniciar todos los servicios
6. ✅ Verificar que la app responda

---

## 📝 Paso 4: Deployment Manual (Alternativa)

Si prefieres hacerlo manualmente paso a paso:

### 4.1. Preparar el .env en producción

```bash
# Copiar template
cp .env.production.example .env

# Editar con tus valores
nano .env
```

**Variables críticas a configurar:**
```bash
# Generar SECRET_KEY segura
openssl rand -hex 32

# Pegar en .env
SECRET_KEY=tu_clave_generada_de_64_caracteres

# Configurar tus API keys (copiar de tu .env local)
FINCA1_API_KEY=...
FINCA2_API_KEY=...
FINCA3_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

### 4.2. Iniciar servicios

```bash
cd /var/www/weatherlink

# Construir imágenes
docker-compose -f docker-compose.production.yml build

# Iniciar servicios
docker-compose -f docker-compose.production.yml up -d

# Ver logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## 🔍 Paso 5: Verificación Post-Deployment

### 5.1. Verificar contenedores

```bash
# Ver estado de todos los contenedores
docker-compose -f docker-compose.production.yml ps

# Deberías ver 7 contenedores corriendo:
# ✓ redpanda_prod
# ✓ redpanda_console_prod
# ✓ kafka_producer_prod
# ✓ spark_streaming_prod
# ✓ rain_alerts_prod
# ✓ weatherlink_app_prod
# ✓ nginx_prod (si está configurado)
```

### 5.2. Verificar logs

```bash
# Ver logs de la aplicación principal
docker logs weatherlink_app_prod --tail 50

# Ver logs de todos los servicios
docker-compose -f docker-compose.production.yml logs --tail 100

# Seguir logs en tiempo real
docker-compose -f docker-compose.production.yml logs -f
```

### 5.3. Probar la aplicación

```bash
# Desde el servidor
curl http://localhost:8080

# Ver IP del servidor
hostname -I
```

**Desde tu navegador:**
```
http://TU_IP_HOSTINGER:8080
```

---

## 🔧 Paso 6: Configuración Adicional

### 6.1. Configurar Firewall (UFW)

```bash
# Instalar UFW si no está
sudo apt install ufw -y

# Permitir SSH (IMPORTANTE: antes de habilitar)
sudo ufw allow 22/tcp

# Permitir puerto de la aplicación
sudo ufw allow 8080/tcp

# Si usas Nginx para SSL
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Permitir Redpanda Console (opcional, para debugging)
sudo ufw allow 19644/tcp

# Habilitar firewall
sudo ufw enable

# Ver estado
sudo ufw status
```

### 6.2. Configurar Nginx con SSL (Opcional pero Recomendado)

```bash
# Instalar Certbot para Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado SSL
sudo certbot --nginx -d tu-dominio.com

# Certbot renovará automáticamente los certificados
```

### 6.3. Configurar Auto-start (Systemd)

Para que Docker se inicie automáticamente al reiniciar el servidor:

```bash
# Habilitar Docker al inicio
sudo systemctl enable docker

# Habilitar inicio automático de contenedores
# (Los contenedores con restart: unless-stopped ya lo harán automáticamente)
```

### 6.4. Monitoreo con Redpanda Console

Accede a Redpanda Console para monitorear Kafka:
```
http://TU_IP_HOSTINGER:19644
```

---

## 📊 Paso 7: Comandos Útiles de Mantenimiento

### Ver Estado de Servicios

```bash
cd /var/www/weatherlink

# Estado de contenedores
docker-compose -f docker-compose.production.yml ps

# Uso de recursos
docker stats

# Ver logs
docker-compose -f docker-compose.production.yml logs -f [servicio]
# Ejemplos:
# docker-compose -f docker-compose.production.yml logs -f weatherlink
# docker-compose -f docker-compose.production.yml logs -f kafka-producer
```

### Reiniciar Servicios

```bash
# Reiniciar todos los servicios
docker-compose -f docker-compose.production.yml restart

# Reiniciar un servicio específico
docker-compose -f docker-compose.production.yml restart weatherlink

# Re-desplegar con cambios
docker-compose -f docker-compose.production.yml up -d --build
```

### Detener/Arrancar Servicios

```bash
# Detener todos
docker-compose -f docker-compose.production.yml down

# Detener sin eliminar volúmenes (mantener datos)
docker-compose -f docker-compose.production.yml stop

# Arrancar servicios detenidos
docker-compose -f docker-compose.production.yml start

# Arrancar desde cero
docker-compose -f docker-compose.production.yml up -d
```

### Limpiar Recursos

```bash
# Limpiar contenedores detenidos
docker container prune -f

# Limpiar imágenes sin usar
docker image prune -a -f

# Limpiar todo (cuidado: eliminará volúmenes)
docker system prune -a --volumes -f

# Ver espacio usado
docker system df
```

---

## 🔥 Troubleshooting

### Problema: Contenedor no inicia

```bash
# Ver logs del contenedor
docker logs nombre_contenedor

# Ver últimas 100 líneas
docker logs --tail 100 nombre_contenedor

# Seguir logs en tiempo real
docker logs -f nombre_contenedor
```

### Problema: Puerto ya en uso

```bash
# Ver qué está usando el puerto 8080
sudo lsof -i :8080

# O con netstat
sudo netstat -tulpn | grep 8080

# Matar proceso si es necesario
sudo kill -9 PID
```

### Problema: Sin espacio en disco

```bash
# Ver espacio disponible
df -h

# Ver tamaño de Docker
docker system df

# Limpiar Docker
docker system prune -a -f

# Limpiar logs antiguos
sudo find /var/lib/docker/containers/ -name "*.log" -type f -delete
```

### Problema: Contenedor reiniciando constantemente

```bash
# Ver por qué falla
docker-compose -f docker-compose.production.yml logs nombre_servicio

# Entrar al contenedor (si está corriendo)
docker exec -it nombre_contenedor bash

# Ver health check
docker inspect nombre_contenedor | grep -A 10 Health
```

### Problema: No puedo acceder a la app

1. **Verificar firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 8080/tcp
   ```

2. **Verificar que el contenedor está corriendo:**
   ```bash
   docker ps | grep weatherlink
   ```

3. **Verificar puerto correcto:**
   ```bash
   docker port weatherlink_app_prod
   ```

4. **Probar desde el servidor:**
   ```bash
   curl http://localhost:8080
   ```

---

## 🔄 Actualizar la Aplicación en Producción

### Método 1: Usando scripts (Recomendado)

**Desde tu PC Windows:**
```powershell
# 1. Subir código actualizado
.\upload-to-hostinger.ps1 -HostingerIP "TU_IP"

# 2. Conectarse al servidor
ssh root@TU_IP
```

**En el servidor:**
```bash
# 3. Ejecutar deployment
cd /var/www/weatherlink
sudo bash deploy-hostinger.sh
```

### Método 2: Manual

```bash
# 1. Conectar al servidor
ssh root@TU_IP

# 2. Ir al directorio
cd /var/www/weatherlink

# 3. Hacer backup
tar -czf ~/backup_$(date +%Y%m%d).tar.gz .

# 4. Actualizar código (ejemplo: pull de git)
git pull origin main

# 5. Reconstruir y reiniciar
docker-compose -f docker-compose.production.yml up -d --build

# 6. Verificar logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## 📦 Rollback (Volver a Versión Anterior)

Si algo sale mal después de una actualización:

```bash
# 1. Detener servicios actuales
docker-compose -f docker-compose.production.yml down

# 2. Restaurar backup
cd /var/www/weatherlink
rm -rf *
tar -xzf ~/backup_FECHA.tar.gz

# 3. Reiniciar servicios
docker-compose -f docker-compose.production.yml up -d

# 4. Verificar
docker-compose -f docker-compose.production.yml ps
```

---

## 🔐 Seguridad en Producción

### Recomendaciones de Seguridad

1. **Cambiar SECRET_KEY:**
   ```bash
   openssl rand -hex 32
   # Actualizar en .env
   ```

2. **No exponer puertos innecesarios:**
   - Cerrar Redpanda Console (19644) al público
   - Solo dejar 80/443 (Nginx) y 22 (SSH)

3. **Usar HTTPS con SSL:**
   - Configurar Nginx como proxy reverso
   - Obtener certificado con Let's Encrypt

4. **Configurar fail2ban:**
   ```bash
   sudo apt install fail2ban -y
   sudo systemctl enable fail2ban
   ```

5. **Actualizar sistema regularmente:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

6. **Monitorear logs:**
   ```bash
   # Configurar logrotate para logs de Docker
   sudo nano /etc/logrotate.d/docker-containers
   ```

---

## 📞 Soporte y Recursos

### Documentación Adicional
- [Docker Deployment](DOCKER-DEPLOYMENT.md) - Guía general de Docker
- [README.md](README.md) - Documentación del proyecto
- [RAIN-ALERTS.md](RAIN-ALERTS.md) - Sistema de alertas de lluvia

### Comandos de Ayuda Rápida

```bash
# Ver este documento en markdown renderizado
cat HOSTINGER-DEPLOYMENT.md

# Accesos rápidos
alias dp='docker-compose -f docker-compose.production.yml'
alias dpl='docker-compose -f docker-compose.production.yml logs -f'
alias dps='docker-compose -f docker-compose.production.yml ps'

# Usar
dp restart weatherlink
dpl weatherlink
dps
```

### Checklist Post-Deployment

- [ ] Todos los contenedores están corriendo
- [ ] La aplicación responde en el puerto 8080
- [ ] Logs no muestran errores críticos
- [ ] Firewall configurado correctamente
- [ ] Backup creado
- [ ] .env con SECRET_KEY única
- [ ] SSL configurado (si aplica)
- [ ] Monitoreo configurado
- [ ] Acceso a Supabase funcionando
- [ ] Eventos de lluvia registrándose

---

## 🎉 ¡Listo!

Tu aplicación WeatherLink Dashboard está ahora en producción en Hostinger VPS 🚀

**URLs de acceso:**
- Dashboard: `http://TU_IP:8080`
- Eventos de lluvia: `http://TU_IP:8080/rain/events`
- Redpanda Console: `http://TU_IP:19644`

**Para cualquier problema, revisa los logs:**
```bash
cd /var/www/weatherlink
docker-compose -f docker-compose.production.yml logs -f
```

---

*Última actualización: Febrero 2026*


