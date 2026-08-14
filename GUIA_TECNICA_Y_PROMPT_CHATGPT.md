# 📄 DOCUMENTO TÉCNICO INTEGRAL & PROMPT MAESTRO PARA OTRA IA (CHATGPT / CLAUDE)
# Sistema Meteorológico Agroclimático en Streaming de Alto Rendimiento
## WeatherLink v2 API + Redpanda (Kafka) + Python Asyncio Streaming + Redis State Engine + Supabase (PostgreSQL) + Flask + Grafana

---

## 🤖 SECCIÓN 1: PROMPT DIRECTO PARA OTRA IA (CHATGPT / CLAUDE)

> **Instrucciones para el usuario:**  
> Copia y pega el contenido dentro de este bloque en cualquier modelo de lenguaje (ChatGPT, Claude, etc.) cuando requieras que redacte manuales técnicos, guías de desarrollo, informes de arquitectura o genere nuevas integraciones.

```markdown
Actúa como un Arquitecto de Software Principal y Especialista en Arquitecturas IoT en Streaming y Sistemas Agroclimáticos.

A continuación te presento la documentación técnica completa, la arquitectura de microservicios, el código fuente en producción, los esquemas de base de datos relacional, el pipeline de streaming optimizado (Python Asyncio + Redis + Redpanda/Kafka), la lógica de cálculo agronómico (DPV / Ecuación de Tetens) y el modelo de eventos de lluvia en tiempo real de mi proyecto agroclimático.

Con base en todo este documento técnico:
1. Ayúdame a estructurar y redactar la Guía Técnica de Desarrollo y Manual de Operaciones formal para desarrolladores e ingenieros de campo.
2. Explica la arquitectura de alto rendimiento y la optimización de memoria RAM (reducción de 3.5 GB a < 200 MB mediante el reemplazo de Apache Spark por consumidores asíncronos con aiokafka y persistencia de estado en Redis).
3. Detalla la configuración de Alertas en Grafana (Lluvia activa y Estrés Hídrico por DPV > 1.5 kPa) y cómo se resolvieron los problemas de falsos positivos por acumuladores diarios y el error de etiquetas duplicadas `{}`.
4. Genera el código, módulos o pruebas adicionales que te vaya solicitando paso a paso.

Aquí tienes el contexto técnico completo del sistema:
```

---

## 📌 SECCIÓN 2: VISIÓN GENERAL Y PROPÓSITO DEL SISTEMA

### 2.1 Propósito
El sistema es una **plataforma IoT de monitoreo agroclimático en tiempo real de alto rendimiento** diseñada para capturar, procesar en streaming, persistir y visualizar variables meteorológicas críticas de **3 estaciones meteorológicas Davis Instruments (Vantage Pro2 / WeatherLink Live)** instaladas en fincas agrícolas de floricultura y cultivo en Ecuador:
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

## 🏗️ SECCIÓN 3: ARQUITECTURA TÉCNICA GENERAL (OPTIMIZADA)

### 3.1 Diagrama de Flujo de Datos End-to-End

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FUENTES DE DATOS EXTERNAS                              │
│  Estaciones Davis Instruments (Vantage Pro2 / WeatherLink Live / EnviroMonitor) │
│       [Finca 1: PYGANFLOR]     [Finca 2: Urcuquí]     [Finca 3: Malchinguí]     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTPS (API REST v2) cada 60-270s
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      CAPA DE INGESTA (KAFKA PRODUCER)                           │
│  - Contenedor: `kafka_producer` (Python + Requests + kafka-python)              │
│  - Módulo: `weatherlink_client.py` con extracción enriquecida de métricas       │
│  - Publicación periódica en Redpanda (Kafka API)                                │
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
                    ▼ Consumo Asíncrono (Consumer 1)          ▼ Consumo Asíncrono (Consumer 2)
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│    CONSUMIDOR ASÍNCRONO TELEMETRÍA    │ │     MOTOR DE ALERTAS CON REDIS        │
│  - Contenedor: `spark_streaming`      │ │  - Contenedor: `rain_alerts`          │
│  - Script: `consumer_weather_to_`     │ │  - Script: `consumer_rain_alerts.py`  │
│    `supabase.py` (aiokafka + httpx)   │ │  - aiokafka + redis.asyncio + httpx   │
│  - Cálculo de DPV (Tetens en Python)  │ │  - Persistencia de estado en Redis    │
│  - Validación y micro-batching        │ │  - Detección de inicio: Δ >= 0.1 mm   │
│  - Huella de memoria: < 40 MB RAM     │ │  - Timeout de fin: 30 min sin lluvia  │
│  - Destino: Tabla `weather_readings`  │ │  - Destino: Tabla `rain_events`       │
└───────────────────┬───────────────────┘ └───────────────────┬───────────────────┘
                    │                                         │
                    │                                   ┌─────┴─────┐
                    │                                   │   REDIS   │ (Memoria < 10 MB)
                    │                                   │  Key-Val  │ TTL 24h
                    │                                   └───────────┘
                    └────────────────────┬────────────────────┘
                                         │ PostgreSQL / REST (Supabase)
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
│  - Exportador: Excel .xlsx (openpyxl)  │ │  - Alertas de DPV > 1.5 kPa (Estrés)   │
└────────────────────────────────────────┘ └────────────────────────────────────────┘
```

---

## ⚡ SECCIÓN 4: BENCHMARK Y OPTIMIZACIÓN DE MEMORIA RAM

### 4.1 Comparativa de Rendimiento: Spark vs. Python Asyncio + Redis

| Componente | Arquitectura Anterior (Apache Spark) | Nueva Arquitectura (Asyncio + Redis) | Mejora / Reducción |
| :--- | :--- | :--- | :--- |
| **Pipeline Telemetría** | PySpark Structured Streaming (~1.5 GB RAM) | `consumer_weather_to_supabase.py` (~35 MB RAM) | **-97.6% RAM** |
| **Motor Alertas Lluvia** | PySpark Streaming (~1.5 GB RAM) | `consumer_rain_alerts.py` (~38 MB RAM) | **-97.4% RAM** |
| **Gestor de Estado** | En memoria volátil de Python (RAM de Spark) | Redis 7 Alpine (~8 MB RAM persistente en disco) | **Resistente a reinicios** |
| **Consumo Total Stack** | **~3.5 GB a 4.0 GB RAM** | **< 200 MB RAM** | **~95% Ahorro total** |
| **Tiempo de Arranque** | 45 a 90 segundos (Arranque JVM) | < 2 segundos (Arranque instantáneo) | **45x más rápido** |

---

## 🔍 SECCIÓN 5: ANÁLISIS A FONDO DEL MODELO DE DATOS DE LLUVIA

### 5.1 Diferenciación de Campos en la API de Davis Instruments (WeatherLink v2)

Las estaciones Davis operan mediante un balancín basculante (*tipping bucket* de 0.2 mm o 0.01 in):
1. **`rain_daily_mm` (Acumulador diario):** Suma toda la precipitación acumulada desde las 00:00:00 (medianoche local). **No vuelve a 0 cuando deja de llover**. Mantiene el valor acumulado hasta la siguiente medianoche.
2. **`rain_rate_mm_h` (Tasa / Intensidad instantánea):** Intensidad en tiempo real en $mm/h$. Cuando no llueve es `0.0`. Solo es $>0$ mientras el balancín bascula activamente.
3. **`rain_last_15_min_mm` / `rain_last_60_min_mm`:** Acumulados móviles de los últimos 15 y 60 minutos.
4. **`is_raining`:** Booleano (`true`/`false`) que indica si la estación está registrando lluvia activa.

---

## 🗄️ SECCIÓN 6: ESQUEMA DE BASE DE DATOS (SUPABASE / POSTGRESQL)

### 6.1 Tabla: `weather_readings` (Telemetría de Sensores)
```sql
CREATE TABLE IF NOT EXISTS public.weather_readings (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT NOT NULL,
    station_name TEXT NOT NULL,
    station_id TEXT,
    event_time TIMESTAMPTZ NOT NULL,
    temp_celsius NUMERIC(5,2),
    temp_fahrenheit NUMERIC(5,2),
    humidity NUMERIC(5,2),
    vpd_kpa NUMERIC(5,3),             -- DPV calculado en kPa
    dew_point NUMERIC(5,2),
    rain_mm NUMERIC(8,2),            -- Campo heredado de compatibilidad
    rain_field TEXT,
    rain_rate_mm_h NUMERIC(8,2),     -- Intensidad instantánea real (mm/h)
    rain_daily_mm NUMERIC(8,2),      -- Acumulado del día (mm)
    rain_last_15_min_mm NUMERIC(8,2),-- Lluvia en últimos 15 min (mm)
    is_raining BOOLEAN DEFAULT false,-- Flag booleano de lluvia activa
    solar_radiation NUMERIC(7,2),    -- Radiación solar (W/m2)
    uv_index NUMERIC(4,2),
    wind_speed NUMERIC(6,2),         -- Velocidad viento (km/h)
    wind_dir NUMERIC(5,1),           -- Dirección viento (0 - 360)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_key, event_time)
);

CREATE INDEX IF NOT EXISTS idx_weather_station_time ON weather_readings(station_key, event_time DESC);
```

### 6.2 Tabla: `rain_events` (Ciclo de Vida de Precipitaciones)
```sql
CREATE TABLE IF NOT EXISTS public.rain_events (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT NOT NULL,
    station_name TEXT NOT NULL,
    event_start TIMESTAMPTZ NOT NULL,
    event_end TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    rain_at_start NUMERIC(10,2),      -- Baseline antes de iniciar (mm)
    rain_at_end NUMERIC(10,2),        -- Lectura final al culminar (mm)
    rain_accumulated NUMERIC(10,2),   -- Total llovido durante el evento (mm)
    max_intensity NUMERIC(10,2),      -- Pico de intensidad detectado (mm/h)
    duration_minutes INTEGER,         -- Duración total en minutos
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_key, event_start)
);

CREATE INDEX IF NOT EXISTS idx_rain_events_station ON rain_events(station_key);
CREATE INDEX IF NOT EXISTS idx_rain_events_active ON rain_events(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_rain_events_start ON rain_events(event_start DESC);
```

### 6.3 Vista: `latest_readings`
```sql
CREATE OR REPLACE VIEW public.latest_readings AS
SELECT DISTINCT ON (station_key) 
    station_key,
    station_name,
    station_id,
    event_time,
    temp_celsius,
    temp_fahrenheit,
    humidity,
    vpd_kpa,
    dew_point,
    rain_mm,
    rain_rate_mm_h,
    rain_daily_mm,
    rain_last_15_min_mm,
    is_raining,
    solar_radiation,
    uv_index,
    wind_speed,
    wind_dir,
    created_at
FROM public.weather_readings
ORDER BY station_key, event_time DESC;
```

---

## 📊 SECCIÓN 7: CONFIGURACIÓN EXACTA DE ALERTAS EN GRAFANA

### 7.1 Alerta 1: Detección de Lluvia Activa
* **Problema resuelto:** Se eliminó el error `has duplicate results with labels {}` devolviendo una sola serie de valor numérico llamada `"value"` con la etiqueta `"metric"`.
* **Consulta SQL (Query A):**
  ```sql
  SELECT 
    event_time AS "time",
    station_name AS "metric",
    CASE WHEN is_raining THEN 1 ELSE 0 END AS "value"
  FROM weather_readings
  WHERE event_time >= NOW() - INTERVAL '15 minutes'
  ORDER BY event_time ASC;
  ```
* **Bloque B (Reduce):** Function `Last`, Mode `Strict`.
* **Bloque C (Threshold):** `IS ABOVE 0`.
* **Comportamiento:** Se dispara inmediatamente al detectar lluvia (`value == 1`) y se resuelve automáticamente cuando deja de llover (`value == 0`).

---

### 7.2 Alerta 2: Estrés Hídrico por DPV Alto (> 1.5 kPa)
* **Consulta SQL (Query A):**
  ```sql
  SELECT 
    event_time AS "time",
    station_name AS "metric",
    vpd_kpa AS "value"
  FROM weather_readings
  WHERE event_time >= NOW() - INTERVAL '15 minutes'
  ORDER BY event_time ASC;
  ```
* **Bloque B (Reduce):** Function `Last`, Mode `Strict`.
* **Bloque C (Threshold):** `IS ABOVE 1.5`.
* **Evaluación:** `Evaluate every: 2m`, `For: 5m` (confirmar persistencia de estrés).
* **Acción agronómica recomendada:** Activar nebulizadores (foggers) o pulso corto de riego para elevar humedad relativa.

---

## 💻 SECCIÓN 8: LISTADO DE ARCHIVOS Y RESPONSABILIDADES

| Archivo | Responsabilidad |
| :--- | :--- |
| `weatherlink_client.py` | Cliente HTTP autenticado con API Secret en Header (`X-Api-Secret`) para WeatherLink v2. Extrae métricas separadas de lluvia (`_extract_rain_metrics`) y calcula DPV. |
| `kafka_producer.py` | Orquestador de polling multiescáner (Fincas 1, 2, 3). Publica en Redpanda (`weatherlink.raw`). |
| `consumer_weather_to_supabase.py` | **NUEVO:** Consumidor asíncrono ultraligero (`aiokafka` + `httpx`). Procesa telemetría e inserta en Supabase `weather_readings`. |
| `consumer_rain_alerts.py` | **NUEVO:** Motor asíncrono de eventos de lluvia con persistencia de estado en Redis y sincronización automática con Supabase. |
| `spark_to_supabase.py` | Consumidor alternativo en Apache Spark (modo legado). |
| `rain_alerts_v2.py` | Motor de alertas alternativo en Apache Spark (modo legado). |
| `close_old_rain_events.py` | Monitor periódico de respaldo para cierre de eventos huérfanos. |
| `supabase_api.py` | Wrapper cliente REST de Supabase para Flask. |
| `app.py` | Servidor Web Flask con dashboard, comparativas y exportador Excel (`openpyxl`). |
| `docker-compose.yml` | Orquestación Docker para desarrollo (Nginx, Flask, Redpanda, Producer, Async Telemetry, Async Rain Alerts, Redis). |
| `docker-compose.production.yml` | Orquestación Docker optimizada para producción en VPS. |

---

## 🚀 SECCIÓN 9: COMANDOS DE DESPLIEGUE EN PRODUCCIÓN (VPS)

```bash
# 1. Acceder al VPS
ssh usuario@tu-vps

# 2. Ir a la carpeta del proyecto
cd /var/www/weatherlink

# 3. Descargar cambios
git pull origin main

# 4. Reconstruir contenedores con Redis y los nuevos consumidores asíncronos
docker-compose down
docker-compose up -d --build

# 5. Monitorear logs en vivo
docker logs -f spark_streaming   # Consumidor de telemetría (< 40 MB RAM)
docker logs -f rain_alerts       # Motor de alertas con Redis (< 40 MB RAM)
docker logs -f weatherlink_redis # Contenedor de Redis

# 6. Comprobar ahorro de memoria en el servidor
docker stats --no-stream
```
