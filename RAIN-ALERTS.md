# 🌧️ Sistema de Alertas de Lluvia

Sistema de detección y alertas de eventos de lluvia en tiempo real usando Kafka + Spark Streaming.

## 📊 Cómo Funciona

### 1. **Detección de Eventos**

El sistema compara lecturas consecutivas de lluvia para detectar:

- **Inicio de lluvia**: Cuando `rainfall_daily_mm` incrementa ≥ 0.1mm
- **Continuación**: Mientras siga incrementando
- **Fin del evento**: Sin incrementos por 15 minutos

### 2. **Seguimiento del Evento**

Para cada evento de lluvia se registra:

```
- Hora de inicio
- Valor de lluvia al iniciar (baseline)
- Acumulado desde el inicio del evento
- Duración en minutos
- Intensidad máxima
- Estado (activo/cerrado)
```

### 3. **Ejemplo de Funcionamiento**

```
20:00  → 5.0 mm  (Sin evento)
20:05  → 5.3 mm  (+0.3mm) → 🌧️ INICIO DE LLUVIA
                             Baseline: 5.0mm
                             Acumulado evento: 0.3mm
                             
20:10  → 5.8 mm  (+0.5mm) → 🌧️ lluvia continúa
                             Acumulado evento: 0.8mm (5.8 - 5.0)
                             
20:15  → 6.1 mm  (+0.3mm) → 🌧️ lluvia continúa
                             Acumulado evento: 1.1mm (6.1 - 5.0)
                             
20:20  → 6.1 mm  (0mm)    → ⏸️ Sin cambio
20:25  → 6.1 mm  (0mm)    → ⏸️ Sin cambio
20:30  → 6.1 mm  (0mm)    → ⏸️ Sin cambio
20:35  → 6.1 mm  (0mm)    → ✅ FIN EVENTO (15min sin incremento)
                             Total del evento: 1.1mm
                             Duración: 30 minutos
```

## 🗄️ Estructura de Datos

### Tabla: `rain_events`

```sql
CREATE TABLE rain_events (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT,           -- 'finca1', 'finca2', etc.
    station_name TEXT,          -- 'PYGANFLOR', 'Urcuquí', etc.
    event_start TIMESTAMPTZ,    -- Hora de inicio
    event_end TIMESTAMPTZ,      -- Hora de fin (null si activo)
    is_active BOOLEAN,          -- true = lluvia en curso
    rain_at_start NUMERIC,      -- Valor baseline (mm)
    rain_at_end NUMERIC,        -- Valor final (mm)
    rain_accumulated NUMERIC,   -- Diferencia = cuánto llovió en el evento
    max_intensity NUMERIC,      -- Pico de intensidad
    duration_minutes INTEGER    -- Duración total
);
```

### Vista: `active_rain_events`

```sql
-- Muestra solo eventos activos con información en tiempo real
SELECT * FROM active_rain_events;
```

## 🚀 Configuración

### Paso 1: Crear tabla en Supabase

```bash
# Ejecutar en Supabase SQL Editor
psql -h db.qyhfdjorguosygdkmtoz.supabase.co -U postgres -d postgres \
  -f sql/rain_events_table.sql
```

O copiar y pegar el contenido de `sql/rain_events_table.sql` en el editor SQL de Supabase.

### Paso 2: Agregar servicio a docker-compose.yml

```yaml
services:
  # ... otros servicios

  rain-alerts:
    build: .
    container_name: rain_alerts
    command: python rain_alerts_v2.py
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=redpanda:9092
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
    depends_on:
      - redpanda
      - kafka-producer
    networks:
      - default
```

### Paso 3: Iniciar el servicio

```bash
docker-compose up -d rain-alerts
```

### Paso 4: Ver logs en tiempo real

```bash
docker logs -f rain_alerts
```

Verás mensajes como:

```
🌧️  ¡LLUVIA DETECTADA en PYGANFLOR!
   Incremento: 0.25 mm
   Valor anterior: 5.00 mm
   Valor actual: 5.25 mm
   ✅ Evento registrado en base de datos (ID: 42)
```

## 📡 API Endpoints

### 1. Eventos Activos

```bash
GET /api/rain/events/active
```

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "station_key": "finca1",
      "station_name": "PYGANFLOR",
      "event_start": "2026-02-07T20:05:00Z",
      "rain_accumulated": 1.1,
      "duration_minutes": 30
    }
  ]
}
```

### 2. Historial de Eventos

```bash
GET /api/rain/events/history?station_key=finca1&limit=10
```

**Respuesta:**
```json
{
  "success": true,
  "data": [
    {
      "id": 42,
      "station_key": "finca1",
      "event_start": "2026-02-07T20:05:00Z",
      "event_end": "2026-02-07T20:35:00Z",
      "is_active": false,
      "rain_accumulated": 1.1,
      "duration_minutes": 30
    }
  ]
}
```

## ⚙️ Configuración Avanzada

### Ajustar Umbrales

En `rain_alerts_v2.py`:

```python
# Umbral mínimo para detectar lluvia (mm)
RAIN_START_THRESHOLD = 0.1  # Aumentar para ignorar lloviznas

# Tiempo sin incremento para cerrar evento (minutos)
NO_RAIN_TIMEOUT_MINUTES = 15  # Ajustar según necesidad
```

### Agregar Notificaciones

Modificar la función `process_rain_data()` para agregar:

```python
# Detectar inicio
if not state['is_raining'] and rain_increment >= RAIN_START_THRESHOLD:
    # ... código existente ...
    
    # 🔔 AGREGAR NOTIFICACIONES AQUÍ
    send_email_alert(station_name, rain_increment)
    send_whatsapp_alert(station_name, rain_increment)
    send_webhook_alert({
        'event': 'rain_start',
        'station': station_name,
        'increment': rain_increment
    })
```

## 🧪 Testing

### Consultar eventos activos

```bash
curl http://localhost:8080/api/rain/events/active | jq
```

### Ver último evento de una estación

```bash
curl "http://localhost:8080/api/rain/events/history?station_key=finca1&limit=1" | jq
```

### Verificar estado en Supabase

```sql
-- Eventos activos ahora
SELECT * FROM active_rain_events;

-- Todos los eventos de hoy
SELECT * FROM rain_events
WHERE event_start >= CURRENT_DATE
ORDER BY event_start DESC;

-- Estadísticas por estación
SELECT 
    station_name,
    COUNT(*) as total_events,
    SUM(rain_accumulated) as total_rain,
    AVG(duration_minutes) as avg_duration
FROM rain_events
WHERE event_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY station_name;
```

## 📊 Visualización en Dashboard

Para mostrar alertas en el dashboard, agregar en `dashboard.html`:

```javascript
async function loadActiveRainAlerts() {
    const response = await fetch('/api/rain/events/active');
    const result = await response.json();
    
    if (result.success && result.data.length > 0) {
        // Mostrar banner de alerta
        const alertDiv = document.getElementById('rain-alerts');
        alertDiv.innerHTML = result.data.map(event => `
            <div class="alert alert-rain">
                🌧️ ${event.station_name}: Lloviendo 
                ${event.rain_accumulated.toFixed(1)} mm 
                (hace ${Math.floor(event.duration_minutes)} min)
            </div>
        `).join('');
    }
}

// Actualizar cada minuto
setInterval(loadActiveRainAlerts, 60000);
```

## 🔍 Troubleshooting

### No se detectan eventos

1. Verificar que el contenedor está corriendo:
   ```bash
   docker ps | grep rain_alerts
   ```

2. Ver logs en busca de errores:
   ```bash
   docker logs rain_alerts --tail 50
   ```

3. Verificar que hay datos de lluvia:
   ```bash
   docker logs kafka_producer | grep rain
   ```

### Eventos no se guardan en Supabase

1. Verificar credenciales en `.env`:
   ```bash
   SUPABASE_URL=https://qyhfdjorguosygdkmtoz.supabase.co
   SUPABASE_KEY=tu_clave_anon_o_service_role
   ```

2. Verificar que la tabla existe:
   ```sql
   SELECT * FROM rain_events LIMIT 1;
   ```

## 📈 Próximas Mejoras

- [ ] Notificaciones por email/SMS
- [ ] Webhook para sistemas externos
- [ ] Predictor de lluvia usando ML
- [ ] Integración con sistema de riego automático
- [ ] Dashboard de estadísticas de lluvia
- [ ] Alertas por intensidad (lluvia ligera/moderada/fuerte)

## 💡 Casos de Uso

1. **Agricultura de Precisión**: Ajustar riego basado en lluvia real
2. **Alertas Tempranas**: Notificar antes de inundaciones
3. **Registro Histórico**: Análisis de patrones de lluvia
4. **Automatización**: Cerrar techos de invernaderos automáticamente
5. **Optimización de Recursos**: Cancelar riego programado si llovió
