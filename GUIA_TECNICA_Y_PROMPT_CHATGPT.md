# 📄 DOCUMENTO TÉCNICO INTEGRAL DEL PROYECTO & PROMPT PARA CHATGPT
# Sistema Meteorológico Agroclimático en Streaming (WeatherLink v2 + Kafka + Spark + PostgreSQL/Supabase + Flask + Grafana)

---

## 🤖 SECCIÓN 1: PROMPT DIRECTO PARA CHATGPT / LLM

> **Instrucciones para el usuario:**  
> Copia y pega todo el contenido de este bloque en ChatGPT cuando quieras que actúe como tu Arquitecto de Software Senior, redactor de la guía técnica final o desarrollador de nuevas características.

```markdown
Actúa como un Arquitecto de Software Senior y Especialista en Ingeniería de Datos IoT y Sistemas Agroclimáticos.

A continuación te presento la documentación técnica completa, la arquitectura, el código fuente analizado, los esquemas de base de datos, el flujo de procesamiento en tiempo real con Kafka/Spark/PostgreSQL y los problemas específicos de datos meteorológicos (particularmente la discrepancia entre datos de medición regular vs. datos durante eventos de lluvia en la API de WeatherLink v2 de Davis Instruments) de mi proyecto en producción.

Con base en toda esta información técnica detallada:
1. Ayúdame a estructurar y redactar la Guía Técnica de Desarrollo y Manual de Operaciones formal para el equipo de desarrollo.
2. Desarrolla la Propuesta de Mejora y Modernización de la Arquitectura (optimizaciones de rendimiento, refactorización de consumidores de streaming, normalización del modelo de datos de precipitación y reducción de huella de memoria).
3. Resuelve detalladamente la configuración de Alarmas de Lluvia en Grafana y PostgreSQL, explicando exactamente qué consultas SQL y métricas utilizar para evitar falsos positivos causados por acumuladores diarios.
4. Genera el código o módulos específicos que te vaya solicitando paso a paso.

Aquí tienes el contexto técnico completo del sistema:
```

---

## 📌 SECCIÓN 2: RESUMEN EJECUTIVO Y OBJETIVOS DEL SISTEMA

### 2.1 Propósito
El sistema es una **plataforma IoT de monitoreo agroclimático en tiempo real** diseñada para capturar, procesar en streaming, persistir y visualizar variables meteorológicas críticas de **3 estaciones meteorológicas Davis Instruments (Vantage Pro2 / WeatherLink Live)** instaladas en fincas agrícolas de floricultura y cultivo en Ecuador:
1. **Finca 1 (`finca1`)**: PYGANFLOR (ID: `167591`)
2. **Finca 2 (`finca2`)**: Urcuquí (ID: `209314`)
3. **Finca 3 (`finca3`)**: Malchinguí (ID: `219603`)

### 2.2 Variables Clave Monitoreadas
* **Déficit de Presión de Vapor (DPV / VPD en kPa)**: Métrica agronómica principal calculada a partir de temperatura y humedad relativa (Ecuación de Tetens) para optimizar la transpiración vegetal y control de riego en invernaderos.
* **Precipitación / Lluvia**: Detección de inicio, duración, intensidad máxima (mm/h), acumulado por evento (mm), acumulados diarios y semanales.
* **Temperatura ambiente (°C / °F)** y **Humedad Relativa (%)**.
* **Radiación Solar ($W/m^2$)** e **Índice UV**.
* **Velocidad ($km/h$ o $mph$)** y **Dirección del Viento (°)**.
* **Punto de Rocío (Dew Point)** y **Presión Atmosférica**.

---

## 🏗️ SECCIÓN 3: ARQUITECTURA TÉCNICA GENERAL DEL SISTEMA

### 3.1 Diagrama de Flujo de Datos End-to-End

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FUENTES DE DATOS EXTERNAS                              │
│  Estaciones Davis Instruments (Vantage Pro2 / WeatherLink Live / EnviroMonitor) │
│       [Finca 1: PYGANFLOR]     [Finca 2: Urcuquí]     [Finca 3: Malchinguí]     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTPS (API REST v2)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      CAPA DE INGESTA (KAFKA PRODUCER)                           │
│  - Contenedor: `kafka_producer` (Python + Requests + kafka-python)              │
│  - Polling periódico configurable (`POLL_INTERVAL_SEC` = 60s - 270s)           │
│  - Normalización inicial de unidades (F->C, in->mm) y cálculo previo DPV        │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Eventos JSON estructurados
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  CAPA DE MENSAJERÍA / BROKER DISTRIBUIDO                        │
│  - Motor: Redpanda (Broker C++ compatible con Kafka API v2.8+)                  │
│  - Tópico Principal: `weatherlink.raw` (Particionado por `station_key`)         │
│  - Interfaz de Gestión: Redpanda Console UI (Puerto 8082)                       │
└───────────────────┬─────────────────────────────────────────┬───────────────────┘
                    │                                         │
                    ▼ Consumo Streaming (Consumer 1)          ▼ Consumo Streaming (Consumer 2)
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│    PIPELINE ETL & TELEMETRÍA          │ │     MOTOR DE ALERTAS DE LLUVIA        │
│  - Contenedor: `spark_streaming`      │ │  - Contenedor: `rain_alerts`          │
│  - PySpark Structured Streaming       │ │  - PySpark Structured Streaming       │
│  - Cálculo dinámico de DPV (kPa)      │ │  - Seguimiento de estado en memoria   │
│  - Limpieza de datos (NaN / Inf)      │ │  - Detección de inicio: Δ >= 0.1 mm   │
│  - Batch Writer -> REST Supabase API  │ │  - Timeout de fin: 30 min sin lluvia  │
│  - Destino: Tabla `weather_readings`  │ │  - Destino: Tabla `rain_events`       │
└───────────────────┬───────────────────┘ └───────────────────┬───────────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │ PostgreSQL / REST
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  CAPA DE BASE DE DATOS Y ESTADO (SUPABASE / POSTGRESQL)        │
│  - Tablas: `weather_readings` (Lecturas históricas), `rain_events` (Eventos)    │
│  - Vistas: `active_rain_events` (Eventos en curso), `latest_readings`           │
│  - Procedimientos: `close_inactive_rain_events()`, `get_daily_averages()`       │
│  - Proceso Auxiliar: `rain_monitor` (`close_old_rain_events.py` cada 10 min)   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     │                                       │
                     ▼                                       ▼
┌────────────────────────────────────────┐ ┌────────────────────────────────────────┐
│     CAPA WEB / DASHBOARD NATIVO        │ │     CAPA DE OBSERVABILIDAD / GRAFANA   │
│  - Backend: Flask + Gunicorn           │ │  - Conexión nativa PostgreSQL/Supabase │
│  - Proxy Inverso: Nginx + SSL          │ │  - Visualización DPV en tiempo real    │
│  - Frontend: HTML5 + JS + Chart.js     │ │  - Alertas instantáneas de lluvia      │
│  - Exportador: Excel .xlsx (openpyxl)  │ │  - Comparativa de microclimas          │
└────────────────────────────────────────┘ └────────────────────────────────────────┘
```

---

## 🔍 SECCIÓN 4: ANÁLISIS A FONDO DEL PROBLEMA DE DATOS DE LLUVIA (WEATHERLINK API)

### 4.1 ¿Por qué la API entrega datos distintos cuando llueve vs cuando no llueve?

La API WeatherLink v2 de Davis Instruments maneja la lluvia mediante un sensor de balancín basculante (*tipping bucket* de 0.2 mm o 0.01 pulgadas por oscilación). Esto origina **dos naturalezas de datos completamente diferentes**:

1. **Variables Acumulativas Diarias (Medición periódica general):**
   * Campos: `rainfall_daily_mm`, `rainfall_daily_in`, `rain_day_mm`, `rain_day_in`.
   * **Comportamiento:** Representan el agua acumulada desde las 00:00:00 (medianoche local) hasta el instante actual.
   * **Trampa:** Si cayeron 10 mm a las 07:00 AM y a las 14:00 PM hace pleno sol, la API **sigue entregando `rainfall_daily_mm = 10.0`**. El valor nunca disminuye durante el día; solo se resetea a `0.0` a la medianoche.

2. **Variables de Intensidad / Tasa Instantánea (Medición de evento activo):**
   * Campos: `rain_rate_last_mm`, `rain_rate_last_in`, `rain_rate_mm`, `rain_rate_in`, `rain_rate_last`.
   * **Comportamiento:** Representa la intensidad instantánea extrapolada a una hora ($mm/hora$) basada en el tiempo transcurrido entre los últimos basculamientos del pluviómetro.
   * **Comportamiento en reposo:** Cuando **no llueve**, este campo es `0.0` o `null`. Cuando **está lloviendo activamente**, este campo toma valores como `2.4 mm/h`, `15.0 mm/h`, etc.

3. **Variables de Ventana Móvil / Rango Temporal:**
   * `rainfall_last_15_min_mm` / `rainfall_last_15_min_in`: Lluvia en los últimos 15 minutos.
   * `rainfall_last_60_min_mm` / `rainfall_last_60_min_in`: Lluvia en la última hora.
   * `rainfall_last_24_hr_mm`: Lluvia acumulada en las últimas 24 horas continuas.

4. **Diferencia entre Endpoint `/v2/current` vs `/v2/historic`:**
   * `/v2/current/{station_id}`: Entrega el estado instantáneo de los sensores (tipo 23, 45, 53, 55). Trae campos como `temp`, `hum`, `wind_speed_last`, `rain_rate_last`, `rainfall_daily_mm`.
   * `/v2/historic/{station_id}`: Entrega registros empaquetados por intervalos de archivo (por ejemplo, cada 5 o 15 minutos). Aquí el campo `rainfall_mm` **sí representa el incremento exacto caído en ese intervalo específico**, no el acumulado del día.

---

### 4.2 Diagnóstico del "Relajo" en el Código Actual

Al examinar el archivo `weatherlink_client.py`:
```python
def _rain_to_mm(self, sensor_data):
    mm_keys = [
        "rainfall_daily_mm",      # <--- PRIMERA PRIORIDAD: ¡ACUMULADO DEL DÍA!
        "rainfall_mm",
        "rainfall_last_15_min_mm",
        "rain_day_mm",
        "rain_rate_mm",           # <--- TASA INSTANTÁNEA
    ]
    ...
```
Y luego en `get_current_conditions()`:
```python
rain_mm, rain_field, rain_unit = self._rain_to_mm(sensor_data)
weather_data.update({
    'rain_rate': rain_mm,         # <--- Se guarda el acumulado diario en un campo llamado rain_rate
    'rain_rate_mm': rain_mm,
    ...
})
```

**Consecuencia en la Base de Datos y en Grafana:**
* La columna `rain_mm` en la tabla `weather_readings` contiene en realidad el **acumulado diario de lluvia**.
* Si configuras en Grafana una alerta con la regla simple:
  `SELECT rain_mm FROM weather_readings WHERE rain_mm > 0`
  👉 **Grafana se mantendrá en estado de ALARMA todo el día** desde el momento en que cayó la primera gota de lluvia en la madrugada hasta la medianoche, aunque ya haya dejado de llover.

---

### 4.3 Solución para Grafana y Alarmas de Lluvia

Tienes tres estrategias para resolver y activar alarmas en Grafana sin falsos positivos:

#### Estrategia 1 (Recomendada con la Base de Datos Actual): Consultar la vista `active_rain_events`
El servicio `rain_alerts_v2.py` ya gestiona el ciclo de vida del evento de lluvia.
* **Consulta SQL en Grafana para panel de estado / Alerta:**
```sql
SELECT 
  station_name,
  rain_accumulated,
  duration_minutes,
  event_start
FROM active_rain_events
WHERE station_key = 'finca1';
```
* **Condición de Alarma en Grafana:**
  * Disparar alarma si el número de filas devueltas (`COUNT`) es `>= 1`.
  * Mientras no llueva, la consulta devuelve 0 filas (Estado Normal). En cuanto llueve, devuelve 1 fila con la duración y el acumulado en curso (Estado Alerting).

#### Estrategia 2: Consulta SQL Diferencial en `weather_readings` (Sin tocar backend)
Si se desea detectar si ha llovido en los últimos 5 a 15 minutos directamente sobre la serie de tiempo:
```sql
WITH diff_data AS (
  SELECT 
    event_time,
    station_key,
    rain_mm,
    rain_mm - LAG(rain_mm, 1, rain_mm) OVER (PARTITION BY station_key ORDER BY event_time) AS rain_delta
  FROM weather_readings
  WHERE event_time >= NOW() - INTERVAL '15 minutes'
)
SELECT 
  event_time,
  GREATEST(0, COALESCE(rain_delta, 0)) AS lluvia_reciente_mm
FROM diff_data
WHERE station_key = 'finca1'
ORDER BY event_time DESC
LIMIT 1;
```
* **Condición de Alarma:** `lluvia_reciente_mm > 0.1`.

#### Estrategia 3 (Mejora Estructural en Ingesta): Normalizar el Payload de la API
Separar explícitamente en el modelo de datos:
1. `rain_rate_mm_hr`: Intensidad instantánea real (`rain_rate_last_mm` o `rain_rate_last * 25.4`).
2. `rainfall_daily_mm`: Acumulado del día.
3. `is_raining`: Booleano (`true` si `rain_rate_mm_hr > 0` o delta positivo).

---

## 🧮 SECCIÓN 5: CÁLCULO CIENTÍFICO DE VARIABLES AGROCLIMÁTICAS

### 5.1 Ecuación de Tetens para el Déficit de Presión de Vapor (DPV / VPD)
El DPV expresa la diferencia entre la cantidad de humedad que el aire puede retener cuando está saturado ($VP_{sat}$) y la cantidad real de humedad en el aire ($VP_{actual}$).

1. **Conversión de Temperatura ($°F \rightarrow °C$):**
   $$T_C = (T_F - 32) \times \frac{5}{9}$$
2. **Presión de Vapor de Saturación ($VP_{sat}$ en $kPa$):**
   $$VP_{sat} = 0.6108 \times \exp\left( \frac{17.27 \times T_C}{T_C + 237.3} \right)$$
3. **Presión de Vapor Actual ($VP_{actual}$ en $kPa$):**
   $$VP_{actual} = \left( \frac{\text{Humedad Relativa \%}}{100} \right) \times VP_{sat}$$
4. **Déficit de Presión de Vapor ($DPV$ en $kPa$):**
   $$DPV = VP_{sat} - VP_{actual}$$

### 5.2 Rangos de Interpretación Agronómica
* **$< 0.4\text{ kPa}$ (Peligro - Exceso de Humedad):** Cierre estomático por saturación, alto riesgo de hongos (botrytis, mildiu), transpiración nula.
* **$0.4 - 0.8\text{ kPa}$ (Bajo / Invernadero de enraizamiento):** Transpiración lenta.
* **$0.8 - 1.2\text{ kPa}$ (ÓPTIMO FOTOSINTÉTICO):** Máxima apertura estomática, asimilación óptima de nutrientes y $CO_2$.
* **$1.2 - 1.6\text{ kPa}$ (Aceptable / Moderado):** Transpiración activa.
* **$> 1.6\text{ kPa}$ (Peligro - Estrés Hídrico Severo):** Cierre estomático para evitar deshidratación, aborto de botones florales, quemadura de hojas.

---

## 🗄️ SECCIÓN 6: ESQUEMA DE BASE DE DATOS (POSTGRESQL / SUPABASE)

### 6.1 Tabla: `weather_readings` (Series Temporales)
```sql
CREATE TABLE IF NOT EXISTS weather_readings (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT NOT NULL,
    station_name TEXT NOT NULL,
    station_id BIGINT,
    event_time TIMESTAMPTZ NOT NULL,
    temp_celsius NUMERIC(5,2),
    temp_fahrenheit NUMERIC(5,2),
    humidity NUMERIC(5,2),
    vpd_kpa NUMERIC(5,3),
    dew_point NUMERIC(5,2),
    rain_mm NUMERIC(8,2),            -- Valor reportado por la estación (acumulado diario / rate)
    rain_field TEXT,                  -- Nombre del campo original extraído de la API
    solar_radiation NUMERIC(7,2),     -- W/m2
    uv_index NUMERIC(4,2),
    wind_speed NUMERIC(6,2),          -- km/h
    wind_dir NUMERIC(5,1),            -- Grados (0 - 360)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_key, event_time)
);

CREATE INDEX idx_weather_station_time ON weather_readings(station_key, event_time DESC);
```

### 6.2 Tabla: `rain_events` (Ciclo de Vida de Precipitaciones)
```sql
CREATE TABLE IF NOT EXISTS rain_events (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT NOT NULL,
    station_name TEXT NOT NULL,
    event_start TIMESTAMPTZ NOT NULL,
    event_end TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    rain_at_start NUMERIC(10,2),      -- Baseline en mm antes de iniciar
    rain_at_end NUMERIC(10,2),        -- Lectura al culminar
    rain_accumulated NUMERIC(10,2),   -- Total caído durante el evento (mm)
    max_intensity NUMERIC(10,2),      -- Pico de intensidad detectado
    duration_minutes INTEGER,         -- Duración total calculada
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_key, event_start)
);

CREATE INDEX idx_rain_events_station ON rain_events(station_key);
CREATE INDEX idx_rain_events_active ON rain_events(is_active) WHERE is_active = true;
CREATE INDEX idx_rain_events_start ON rain_events(event_start DESC);
```

### 6.3 Vista: `active_rain_events`
```sql
CREATE OR REPLACE VIEW active_rain_events AS
SELECT 
    id,
    station_key,
    station_name,
    event_start,
    rain_at_start,
    rain_accumulated,
    max_intensity,
    EXTRACT(EPOCH FROM (NOW() - event_start))/60 as duration_minutes,
    NOW() - event_start as duration
FROM rain_events
WHERE is_active = true
ORDER BY event_start DESC;
```

### 6.4 Procedimiento de Cierre Automático: `close_inactive_rain_events()`
```sql
CREATE OR REPLACE FUNCTION close_inactive_rain_events()
RETURNS void AS $$
BEGIN
    UPDATE rain_events
    SET is_active = false,
        event_end = updated_at,
        duration_minutes = EXTRACT(EPOCH FROM (updated_at - event_start))/60
    WHERE is_active = true
      AND updated_at < NOW() - INTERVAL '30 minutes';
END;
$$ LANGUAGE plpgsql;
```

---

## 💻 SECCIÓN 7: COMPONENTES DE CÓDIGO Y ESTRUCTURA DEL REPOSITORIO

### 7.1 Módulos Principales
| Archivo | Responsabilidad / Descripción |
| :--- | :--- |
| `weatherlink_client.py` | Cliente HTTP autenticado con API Secret en Header (`X-Api-Secret`) y API Key en query param para WeatherLink v2. Cálculo de DPV, parseo de sensores ISS y soporte de histórico con paginación de 24h. |
| `kafka_producer.py` | Orquestador de sondeo periódico multiescáner (Finca 1, 2 y 3). Publica eventos estructurados a Redpanda en el tópico `weatherlink.raw`. |
| `spark_to_supabase.py` | PySpark Structured Streaming. Procesa el micro-batch, recalcula DPV, valida números seguros (`safe_float`) y hace upsert mediante Supabase REST API a `weather_readings`. |
| `rain_alerts_v2.py` | Motor de estado de lluvia. Detecta umbral de inicio ($\ge 0.1\text{ mm}$), maneja resets de acumulador a medianoche, detecta inactividad (30 min) y duración máxima (12h). |
| `close_old_rain_events.py`| Monitor independiente que verifica periódicamente si existen eventos abiertos abandonados en Supabase y los cierra forzosamente. |
| `supabase_api.py` | Wrapper cliente para Flask para consumir endpoints REST de Supabase (`latest_readings`, `weather_readings`, `rain_events`, `active_rain_events`). |
| `app.py` | Servidor Web Flask con endpoints para frontend, vistas de detalle por finca, comparativa, eventos de lluvia y exportación de reportes a Excel con `openpyxl`. |
| `docker-compose.yml` | Orquestación completa de 7 microservicios en Docker (Flask, Redpanda, Redpanda Console, Producer, Spark Streaming, Rain Alerts, Rain Monitor, Nginx). |

---

## 🚀 SECCIÓN 8: DIAGNÓSTICO TÉCNICO Y PROPUESTA DE MEJORA INTEGRAL

### 8.1 Deuda Técnica y Cuellos de Botella Detectados

1. **Uso Excesivo de PySpark para Ingesta Ligera:**
   * *Diagnóstico:* Se tienen 3 estaciones emitiendo datos cada 60–270 segundos (apenas ~3 eventos/minuto). Levantar la JVM de Apache Spark para este volumen consume entre 1.5 GB y 3 GB de memoria RAM en el VPS, lo cual encarece los costos de infraestructura y añade lentitud de arranque.
   * *Propuesta:* Reemplazar PySpark por un consumidor en **Python Asyncio nativo con `aiokafka` y `asyncpg`** o **FastAPI / Go**. El consumo de RAM bajará de 2.5 GB a menos de 80 MB, con latencia de persistencia sub-segundo.

2. **Estado en Memoria Volátil en `rain_alerts_v2.py`:**
   * *Diagnóstico:* La variable `station_states = {}` vive en la memoria RAM del script. Si el contenedor se reinicia en medio de una tormenta, pierde el `rain_at_start` y el `event_start` previo, pudiendo crear eventos huérfanos o duplicados.
   * *Propuesta:* Mover el estado del evento de lluvia a **Redis** o consultar directamente el estado abierto existente en la base de datos `rain_events` al iniciar el microservicio.

3. **Falta de Particionamiento en PostgreSQL:**
   * *Diagnóstico:* La tabla `weather_readings` inserta miles de filas por semana. Con el paso de los meses, las consultas históricas de Grafana se ralentizarán.
   * *Propuesta:* Implementar particionamiento por mes mediante `pg_partman` o activar la extensión **TimescaleDB** (disponible en PostgreSQL) para convertir `weather_readings` en un *Hypertable* con compresión columnar automática para datos mayores a 30 días.

4. **Alertas Multicanal en Tiempo Real:**
   * *Diagnóstico:* Actualmente la detección de lluvia escribe en base de datos, pero no notifica activamente al agrónomo ni al personal de campo.
   * *Propuesta:* Integrar un despachador de alertas que envíe mensajes inmediatos con botones de acción a **Telegram Bot** y **WhatsApp Business API (Twilio/Meta)** con formato:
     ```text
     🌧️ ¡ALERTA DE LLUVIA INICIADA!
     📍 Estación: Finca 1 - PYGANFLOR
     ⏱️ Hora de inicio: 15:42 (UTC-5)
     💧 Intensidad actual: 4.8 mm/h
     ⚠️ Acción recomendada: Cerrar cortinas de invernadero / Suspender riego sector B.
     ```

5. **Tablero Unificado en Grafana con Métricas de Estrés de DPV:**
   * *Propuesta:* Diseñar un dashboard con indicadores tipo *Gauge* y mapas de calor (*Heatmaps*) para DPV, con alertas automáticas cuando el DPV permanezca fuera del rango $0.8 - 1.2\text{ kPa}$ por más de 30 minutos consecutivos durante horas de sol.

---

## 🛠️ SECCIÓN 9: GUÍA RÁPIDA DE COMANDOS Y DESPLIEGUE

### 9.1 Levantar el Entorno Completo con Docker
```bash
# 1. Clonar o ingresar al directorio del proyecto
cd "D:/todo en vs code/NUEVO DPV/NUEVO DPV"

# 2. Configurar variables de entorno
cp .env.example .env
# (Editar .env con las API Keys de Davis y credenciales de Supabase)

# 3. Construir y levantar todos los contenedores en segundo plano
docker-compose up -d --build

# 4. Verificar estado de los contenedores
docker ps

# 5. Monitorear logs en vivo del sistema de alertas de lluvia
docker logs -f rain_alerts

# 6. Monitorear logs del productor de Kafka
docker logs -f kafka_producer
```

### 9.2 URLs de Acceso a Servicios Locales / VPS
* **Dashboard Web Principal (Nginx):** `http://localhost:8081` o `https://tu-dominio.com`
* **API REST Flask directa:** `http://localhost:8080`
* **Redpanda Console (Kafka UI):** `http://localhost:8082`
* **API de Eventos de Lluvia Activos:** `http://localhost:8080/api/rain/events/active`
* **API de Lluvia Acumulada Semanal/Diaria:** `http://localhost:8080/api/rain/accumulated`

---

## 📝 SECCIÓN 10: PROMPTS SECUNDARIOS LISTOS PARA USAR CON CHATGPT

### Prompt A: "Generar la Guía Técnica de Desarrollo Paso a Paso"
> *"Con base en el Documento Técnico Integral provisto, genera una Guía Técnica de Desarrollo paso a paso estructurada en formato Markdown para desarrolladores junior y senior que se integren al proyecto. Debe incluir: configuración del entorno local, explicación detallada de cada archivo del repositorio, diagrama de arquitectura en Mermaid, guía de endpoints de la API, estructura de base de datos y cómo realizar pruebas unitarias y de integración."*

### Prompt B: "Refactorizar PySpark a Consumidor Ligero Python (aiokafka + asyncpg)"
> *"Tomando en cuenta la Sección 8 del Documento Técnico, escribe la refactorización completa de `spark_to_supabase.py` y `rain_alerts_v2.py` para convertirlos en microservicios asíncronos ultraligeros usando `aiokafka` y `asyncpg` (o cliente REST de Supabase con `httpx`), eliminando la dependencia de Java/Spark para ahorrar memoria RAM en el servidor VPS."*

### Prompt C: "Diseñar el Dashboard y Alertas en Grafana con PostgreSQL"
> *"Basándote en la Sección 4 y 6 del Documento Técnico, genera la especificación completa y las consultas SQL optimizadas para configurar un Dashboard en Grafana conectado a Supabase/PostgreSQL. Incluye las queries para: panel de DPV con umbrales de color, serie temporal de temperatura y radiación, panel de lluvia acumulada del día y la regla de alerta exacta para eventos de lluvia activa sin falsos positivos."*
