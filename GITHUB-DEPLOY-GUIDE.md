# 🚀 Guía de Deployment a Hostinger vía GitHub

**Tu servidor:** ssh root@72.60.121.172

---

## ✅ PASOS COMPLETOS - Sin Errores

### **FASE 1: Preparar y Subir Código a GitHub**

#### Paso 1: Commit de todos los cambios

**En tu PC (PowerShell):**
```powershell
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Ver archivos modificados
git status

# Agregar TODOS los archivos (nuevos y modificados)
git add .

# Crear commit con mensaje descriptivo
git commit -m "✨ Preparado para deployment en producción - Incluye fix timezone, sistema alertas lluvia, docker-compose prod"

# Verificar que se hizo el commit
git log -1
```

#### Paso 2: Push a GitHub

```powershell
# Subir cambios a GitHub
git push origin main

# Verificar que se subió correctamente
git status
```

**Deberías ver:** `Your branch is up to date with 'origin/main'`

---

### **FASE 2: Deployment en Servidor Hostinger**

#### Paso 3: Conectar al servidor

```powershell
ssh root@72.60.121.172
```

#### Paso 4: Crear BACKUP antes de tocar nada ⚠️ **CRÍTICO**

```bash
# Ver qué tienes corriendo actualmente
docker ps

# Crear backup con timestamp
mkdir -p ~/backups
cd /var/www/weatherlink  # O donde esté tu app actual
tar -czf ~/backups/weatherlink_backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# Verificar que se creó el backup
ls -lh ~/backups/
```

**NO continúes sin este backup

**

#### Paso 5: Obtener última versión desde GitHub

```bash
# Ir al directorio de tu aplicación
cd /var/www/weatherlink

# Descargar últimos cambios
git pull origin main

# Verificar que se descargaron los archivos
ls -la
```

**Deberías ver:**
- `docker-compose.production.yml`
- `deploy-hostinger.sh`
- `.env.production.example`
- Todos los archivos Python actualizados

#### Paso 6: Configurar archivo .env para producción

```bash
# Si ya tienes un .env, hacer backup
cp .env .env.backup 2>/dev/null || true

# Opción A: Si NO tienes .env, crear desde ejemplo
cp .env.production.example .env

# Editar con tus valores reales
nano .env
```

**Variables OBLIGATORIAS a configurar:**
```bash
# 1. WeatherLink API (copiar de tu .env local en Windows)
FINCA1_API_KEY=tu_api_key_real
FINCA1_API_SECRET=tu_api_secret_real
FINCA1_STATION_ID=tu_station_id_real

FINCA2_API_KEY=...
FINCA2_API_SECRET=...
FINCA2_STATION_ID=...

FINCA3_API_KEY=...
FINCA3_API_SECRET=...
FINCA3_STATION_ID=...

# 2. Supabase (copiar de tu .env local)
SUPABASE_URL=https://tu_proyecto.supabase.co
SUPABASE_KEY=tu_service_role_key_real

# 3. Flask SECRET_KEY (GENERAR UNA NUEVA para producción)
openssl rand -hex 32
# Copiar el resultado y pegarlo aquí:
SECRET_KEY=resultado_del_comando_anterior

# 4. Entorno
FLASK_DEBUG=0
FLASK_ENV=production

# 5. Puertos (ajustar si ya tienes algo corriendo en 8080)
HOST_PORT=8080
```

**Guardar:** `Ctrl+O`, Enter, `Ctrl+X`

**Verificar que guardaste correctamente:**
```bash
# Ver que tiene contenido
cat .env | grep SUPABASE_URL
cat .env | grep SECRET_KEY
cat .env | grep FINCA1_API_KEY
```

#### Paso 7: Ejecutar Deployment Automático

```bash
# Dar permisos de ejecución al script
chmod +x deploy-hostinger.sh

# EJECUTAR DEPLOYMENT
sudo bash deploy-hostinger.sh
```

**El script hará automáticamente:**
1. ✅ Crea backup adicional con timestamp
2. ✅ Detiene servicios actuales si existen
3. ✅ Limpia recursos Docker antiguos
4. ✅ Verifica archivos de configuración
5. ✅ Construye 7 imágenes Docker (tarda 3-5 min)
6. ✅ Inicia todos los contenedores
7. ✅ Verifica health checks
8. ✅ Prueba que la app responda

**Salida esperada al final:**
```
╔════════════════════════════════════════════════════════╗
║          DEPLOYMENT COMPLETADO EXITOSAMENTE            ║
╚════════════════════════════════════════════════════════╝

📊 Resumen del Deployment:
  • Backup:             /var/backups/weatherlink/20260207_203000/
  • Directorio:         /var/www/weatherlink
  • Puerto App:         8080

✓ Aplicación respondiendo correctamente en puerto 8080
```

#### Paso 8: Verificación Post-Deployment

```bash
# 1. Ver que los 7 contenedores estén corriendo
docker ps

# Deberías ver:
# - redpanda_prod
# - redpanda_console_prod
# - kafka_producer_prod
# - spark_streaming_prod
# - rain_alerts_prod
# - weatherlink_app_prod
# - nginx_prod (opcional)

# 2. Ver logs de la aplicación principal
docker logs weatherlink_app_prod --tail 50

# 3. Ver logs en tiempo real (para debugging)
docker logs -f weatherlink_app_prod
# (Ctrl+C para salir)

# 4. Probar desde el servidor
curl http://localhost:8080

# 5. Ver estadísticas de contenedores
docker stats --no-stream
```

---

### **FASE 3: Configuración Firewall (IMPORTANTE)**

```bash
# Ver estado actual
sudo ufw status

# Si está inactivo, activarlo (CUIDADO: hacer esto PRIMERO)
# IMPORTANTE: Permitir SSH ANTES de habilitar firewall
sudo ufw allow 22/tcp

# Permitir puerto de la aplicación
sudo ufw allow 8080/tcp

# Permitir Redpanda Console (solo si lo necesitas accesible)
sudo ufw allow 19644/tcp

# AHORA sí activar (si estaba inactivo)
sudo ufw enable

# Verificar reglas
sudo ufw status numbered
```

**Reglas mínimas que debes tener:**
```
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
8080/tcp                   ALLOW       Anywhere
```

---

### **FASE 4: Probar desde tu Navegador**

**Desde tu PC, abre:**
```
http://72.60.121.172:8080
```

**Deberías ver:**
- ✅ Las 3 estaciones con datos actuales
- ✅ Selector de estaciones funciona
- ✅ Gráficos se cargan
- ✅ Botón "Exportar a Excel" con timezone correcto
- ✅ Eventos de lluvia en `/rain/events`

---

## ❌ Errores Comunes y Soluciones

### Error: "Port 8080 already in use"

```bash
# Ver qué está usando el puerto 8080
sudo lsof -i :8080

# Matar proceso si es necesario
sudo kill -9 PID

# O cambiar puerto en .env
nano .env
# Cambiar: HOST_PORT=8081
```

### Error: "Cannot connect to Docker daemon"

```bash
# Iniciar Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verificar estado
docker ps
```

### Error: Contenedor reiniciando constantemente

```bash
# Ver por qué falla
docker logs weatherlink_app_prod

# Revisar .env (causa más común)
cat .env

# Verificar que SECRET_KEY no tiene comillas
# Verificar que todas las API keys están correctamente
```

### Error: "No module named 'xyz'"

```bash
# Reconstruir imagen sin cache
cd /var/www/weatherlink
docker-compose -f docker-compose.production.yml build --no-cache weatherlink

# Reiniciar contenedor
docker-compose -f docker-compose.production.yml up -d weatherlink
```

---

## 🔄 Actualizaciones Futuras

**Cuando hagas cambios en el código:**

### Paso 1: En tu PC

```powershell
cd "D:\todo en vs code\NUEVO DPV\NUEVO DPV"

# Hacer cambios en el código...

# Commit
git add .
git commit -m "Descripción de los cambios"
git push origin main
```

### Paso 2: En el servidor

```bash
ssh root@72.60.121.172

cd /var/www/weatherlink

# Backup rápido
tar -czf ~/backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# Descargar cambios
git pull origin main

# Reconstruir y reiniciar
docker-compose -f docker-compose.production.yml up -d --build

# Ver logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## 🆘 Rollback (Si algo sale mal)

```bash
# 1. Detener todo
cd /var/www/weatherlink
docker-compose -f docker-compose.production.yml down

# 2. Restaurar código anterior
rm -rf *
tar -xzf ~/backups/weatherlink_backup_FECHA.tar.gz

# 3. Reiniciar
docker-compose up -d  # O docker-compose.production.yml si lo tenías

# 4. Verificar
docker ps
curl http://localhost:8080
```

---

## 📋 Checklist Final

Antes de confirmar que deployment está OK:

- [ ] 7 contenedores corriendo (`docker ps`)
- [ ] App carga en `http://72.60.121.172:8080`
- [ ] Las 3 estaciones muestran datos
- [ ] Exportar Excel funciona (timezone Ecuador correcto)
- [ ] Eventos de lluvia `/rain/events` accesible
- [ ] Firewall configurado (UFW)
- [ ] Backup creado y verificado
- [ ] .env tiene SECRET_KEY única
- [ ] Logs sin errores críticos (`docker logs weatherlink_app_prod`)

---

## 🎯 Comandos Útiles Diarios

```bash
# Ver estado
cd /var/www/weatherlink
docker-compose -f docker-compose.production.yml ps

# Ver logs
docker-compose -f docker-compose.production.yml logs -f weatherlink

# Reiniciar app
docker-compose -f docker-compose.production.yml restart weatherlink

# Ver uso de recursos
docker stats

# Limpiar espacio
docker system prune -f
```

---

## 🚀 ¡Listo para Deployment!

**Resumen del flujo:**
1. ✅ `git add .` + `git commit` + `git push` (en Windows)
2. ✅ `ssh root@72.60.121.172` (conectar al servidor)
3. ✅ Crear backup actual
4. ✅ `git pull origin main` (descargar cambios)
5. ✅ Configurar `.env` con valores reales
6. ✅ `sudo bash deploy-hostinger.sh` (deployment automático)
7. ✅ Verificar en navegador: `http://72.60.121.172:8080`

**Tiempo estimado:** 15-20 minutos

---

*Última actualización: Febrero 7, 2026*
