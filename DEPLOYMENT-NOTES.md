# Notas de Despliegue - Actualización de Producción

**Fecha**: 8 de Febrero de 2026  
**Versión**: Sistema de Eventos de Lluvia v2.0 + Tabla de Acumulados

---

## 📦 Cambios Incluidos en esta Actualización

### 1. **Sistema de Eventos de Lluvia Mejorado**
- ✅ Umbral de cierre de eventos aumentado de 15 a 30 minutos
- ✅ Corrección de función `close_rain_event()` para guardar correctamente:
  - `event_end` (hora de fin del evento)
  - `duration_minutes` (duración calculada)
  - `rain_at_end` (valor final de lluvia)
  - `is_active` (estado del evento)

### 2. **Nueva Tabla de Lluvia Acumulada**
- ✅ Vista por semana (formato YY-WW: 26-07 = semana 7 de 2026)
- ✅ Vista por día (últimos 14 días)
- ✅ Día actual resaltado con badge "HOY"
- ✅ Actualización automática cada 15 segundos con datos de Kafka
- ✅ Nuevo endpoint API: `/api/rain/accumulated`

### 3. **Archivos Modificados**
- `app.py` - Nuevo endpoint para lluvia acumulada
- `rain_alerts_v2.py` - Umbral de 30 minutos y correcciones
- `sql/rain_events_table.sql` - Función SQL actualizada
- `templates/rain_events.html` - Nueva tabla de acumulados

### 4. **Archivos Nuevos (Utilitarios)**
- `close_old_rain_events.py` - Script para cerrar eventos antiguos manualmente
- `restart_rain_alerts.ps1` - Script para reiniciar servicio de alertas
- `update_rain_function.py` - Script para actualizar función SQL
- `TESTING-LOCAL.md` - Guía de pruebas locales

---

## 🚀 Pasos para Desplegar en Hostinger

### Paso 1: Conectarse al Servidor
```bash
ssh usuario@tu-servidor-hostinger.com
cd /ruta/a/weatherlink-dashboard
```

### Paso 2: Hacer Pull de los Cambios
```bash
git pull origin main
```

**Nota**: Te pedirá usuario y Personal Access Token (PAT) de GitHub:
- Usuario: `renealejo96`
- Contraseña: `[tu Personal Access Token generado]`

### Paso 3: Actualizar Función SQL en Supabase

**IMPORTANTE**: Esto debe hacerse manualmente en el dashboard de Supabase:

1. Ve a: https://supabase.com/dashboard
2. Selecciona tu proyecto
3. Ve a **SQL Editor**
4. Ejecuta el siguiente SQL:

```sql
CREATE OR REPLACE FUNCTION close_inactive_rain_events()
RETURNS void AS $$
BEGIN
    -- Cerrar eventos que no han tenido actualización en 30 minutos
    UPDATE rain_events
    SET is_active = false,
        event_end = updated_at,
        duration_minutes = EXTRACT(EPOCH FROM (updated_at - event_start))/60
    WHERE is_active = true
      AND updated_at < NOW() - INTERVAL '30 minutes';
END;
$$ LANGUAGE plpgsql;
```

### Paso 4: Reconstruir Contenedores Docker
```bash
docker-compose down
docker-compose up -d --build
```

### Paso 5: Verificar que Todo Funcione
```bash
# Ver logs de los servicios
docker logs -f rain_alerts
docker logs -f weatherlink_app

# Verificar que todos los contenedores estén corriendo
docker ps
```

### Paso 6: Cerrar Eventos Antiguos (Si es necesario)
Si hay eventos que quedaron abiertos:
```bash
python3 close_old_rain_events.py
```

---

## ✅ Verificación en Producción

### URLs a Verificar:
1. **Dashboard de Eventos**: https://tu-dominio.com/rain/events
   - Verificar que aparezca la nueva tabla de acumulados
   - Verificar pestañas "Por Semana" y "Por Día"
   - Verificar que el día actual esté resaltado

2. **API de Acumulados**: https://tu-dominio.com/api/rain/accumulated
   - Debe devolver JSON con datos agrupados

3. **API de Eventos Activos**: https://tu-dominio.com/api/rain/events/active
   - No debería haber eventos activos si no está lloviendo

### Verificar en Logs:
```bash
docker logs rain_alerts --tail 50
```

Debe mostrar:
```
⏱️  Timeout sin lluvia: 30 minutos  <-- IMPORTANTE: Debe decir 30!
```

---

## 🔧 Solución de Problemas

### Si los eventos siguen apareciendo como activos:
1. Verificar que la función SQL se actualizó en Supabase
2. Ejecutar script: `python3 close_old_rain_events.py`
3. Esperar 30 minutos desde la última actualización del evento

### Si la tabla de acumulados no aparece:
1. Verificar que `weatherlink_app` se reconstruyó: `docker-compose up -d --build weatherlink`
2. Verificar logs: `docker logs weatherlink_app --tail 50`
3. Probar API directamente: `curl http://localhost:8000/api/rain/accumulated`

### Si hay problemas con Docker:
```bash
# Reconstruir todo desde cero
docker-compose down -v
docker-compose up -d --build
```

---

## 📝 Notas Adicionales

- Los eventos ahora se cierran automáticamente después de **30 minutos** sin incremento de lluvia
- La tabla de acumulados se actualiza cada **15 segundos** automáticamente
- El formato de semana es **YY-WW** (ejemplo: 26-07 para semana 7 de 2026)
- El día actual siempre está resaltado en amarillo con badge "HOY"

---

## 📞 Contacto
Si hay problemas durante el despliegue, revisar:
- Logs de Docker: `docker logs <nombre-contenedor>`
- Estado de servicios: `docker ps`
- Conectividad a Supabase: Verificar variables de entorno en `.env`
