# Guía de Pruebas en Local

## 🌐 URLs Disponibles

### 1. **Dashboard de Eventos de Lluvia** (Principal)
```
http://localhost:8081/rain/events
```
Aquí verás:
- Eventos de lluvia ACTIVOS en tiempo real
- Historial completo de eventos
- Filtros por estación
- Se actualiza automáticamente cada 15 segundos

### 2. **Dashboard Principal**
```
http://localhost:8081/
```
Vista general de las estaciones meteorológicas

### 3. **Comparar Estaciones**
```
http://localhost:8081/compare
```

### 4. **API REST - Eventos Activos**
```
http://localhost:8081/api/rain/events/active
```
JSON con eventos de lluvia activos

### 5. **API REST - Historial**
```
http://localhost:8081/api/rain/events/history?limit=20
http://localhost:8081/api/rain/events/history?station_key=finca1&limit=10
```
JSON con historial de eventos

### 6. **Redpanda Console** (Kafka UI)
```
http://localhost:8082
```
Para ver mensajes en Kafka en tiempo real

---

## 🧪 Métodos de Prueba

### Opción 1: Ver en el Navegador (RECOMENDADO)
1. Abre: http://localhost:8081/rain/events
2. Verifica que aparezca el dashboard
3. Si hay lluvia activa, verás las tarjetas moradas animadas
4. El historial se actualiza automáticamente
5. Verifica que los eventos finalizados muestren:
   - ✅ Hora de inicio
   - ✅ Hora de fin
   - ✅ Duración correcta
   - ✅ Estado "Finalizado" (no "Activo")

### Opción 2: Ver Logs en Tiempo Real
```powershell
# Ver logs del sistema de alertas
docker logs -f rain_alerts

# Ver solo nuevos mensajes
docker logs -f --tail 50 rain_alerts
```

Deberías ver:
```
🌧️  SISTEMA DE ALERTAS DE LLUVIA v2.0
⏱️  Timeout sin lluvia: 30 minutos   <-- DEBE DECIR 30!
⏰ Esperando eventos de lluvia...
```

### Opción 3: Consultar API Directamente
```powershell
# Ver eventos activos
Invoke-RestMethod -Uri "http://localhost:8081/api/rain/events/active" | ConvertTo-Json -Depth 5

# Ver historial
Invoke-RestMethod -Uri "http://localhost:8081/api/rain/events/history?limit=10" | ConvertTo-Json -Depth 5
```

### Opción 4: Ver Base de Datos (Supabase)
1. Ve a: https://supabase.com/dashboard
2. Selecciona tu proyecto
3. Ve a "Table Editor"
4. Abre la tabla `rain_events`
5. Verifica las columnas:
   - `is_active` debe ser `false` para eventos terminados
   - `event_end` debe tener fecha/hora
   - `duration_minutes` debe tener un valor calculado

---

## 🔍 Verificar que los Cambios Funcionan

### 1. Verificar Umbral de 30 Minutos
```powershell
# Ver configuración activa
docker logs rain_alerts | Select-String "Timeout"
```
Debe mostrar: `⏱️  Timeout sin lluvia: 30 minutos`

### 2. Simular Evento de Lluvia (Para Testing)
Si quieres forzar una prueba:
```powershell
# Ver mensajes en Kafka
# Abre: http://localhost:8082
# Ve a Topics → weatherlink.raw → Messages
```

### 3. Verificar Cierre de Eventos
Los eventos ahora se cerrarán automáticamente después de:
- **30 minutos** sin incremento de lluvia
- Cuando se detecte que dejó de llover

---

## 📊 Verificar Estado de Servicios

```powershell
# Ver que todos los contenedores estén corriendo
docker ps

# Verificar logs de cada servicio
docker logs rain_alerts --tail 30
docker logs kafka_producer --tail 30
docker logs spark_streaming --tail 30
docker logs weatherlink_app --tail 30

# Reiniciar un servicio específico si es necesario
docker restart rain_alerts
```

---

## 🐛 Troubleshooting

### Si no ves eventos en el dashboard:
1. Verifica que Supabase esté configurado (archivo .env)
2. Revisa logs: `docker logs weatherlink_app --tail 50`
3. Verifica la conexión a Supabase

### Si los eventos siguen mostrándose como activos:
1. Ejecuta el SQL en Supabase (ver instrucciones principales)
2. Espera 30 minutos desde la última actualización
3. O manualmente actualiza en Supabase:
```sql
UPDATE rain_events 
SET is_active = false, 
    event_end = updated_at,
    duration_minutes = EXTRACT(EPOCH FROM (updated_at - event_start))/60
WHERE is_active = true 
  AND updated_at < NOW() - INTERVAL '30 minutes';
```

### Si Docker no responde:
```powershell
# Reiniciar todo
docker-compose down
docker-compose up -d

# Reconstruir si hay cambios en el código
docker-compose up -d --build
```

---

## 📝 Logs Importantes a Buscar

### Cuando INICIA un evento de lluvia:
```
🌧️  ¡LLUVIA DETECTADA en PYGANFLOR!
   Incremento: 0.15 mm
   ✅ Evento registrado en base de datos (ID: 123)
```

### Cuando CONTINÚA lloviendo:
```
🌧️  Lluvia continúa en PYGANFLOR
   Acumulado desde inicio: 2.50 mm
   Duración: 15.3 minutos
```

### Cuando TERMINA un evento (después de 30 min sin lluvia):
```
✅ Fin de lluvia en PYGANFLOR
   Total caído: 3.20 mm
   Duración: 45.2 min
   Evento de lluvia cerrado para finca1
   Duración total: 45 minutos
```
