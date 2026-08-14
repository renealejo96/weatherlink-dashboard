"""
Motor Asíncrono Ultraligero de Alertas de Lluvia con Persistencia de Estado en Redis
Reemplaza PySpark Streaming para procesar eventos de lluvia en tiempo real (< 40 MB RAM).
"""

import os
import sys
import json
import math
import asyncio
import signal
from datetime import datetime, timedelta
import httpx
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

load_dotenv()

# Configuración
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_RAW', 'weatherlink.raw')
KAFKA_GROUP = os.getenv('KAFKA_CONSUMER_GROUP_RAIN', 'rain-alerts-async-engine')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Umbrales de detección
RAIN_START_THRESHOLD = float(os.getenv('RAIN_START_THRESHOLD', '0.1'))  # mm
NO_RAIN_TIMEOUT_MINUTES = int(os.getenv('NO_RAIN_TIMEOUT_MINUTES', '30'))  # minutos de inactividad
MAX_EVENT_DURATION_MINUTES = int(os.getenv('MAX_EVENT_DURATION_MINUTES', '720'))  # 12 horas max

running = True
redis_client = None
memory_fallback_states = {}


def safe_float(value):
    if value is None:
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


# ==============================================================================
# GESTIÓN DE ESTADO PERSISTENTE (REDIS CON FALLBACK EN MEMORIA)
# ==============================================================================

async def get_redis_connection():
    """Intenta conectar a Redis; si falla, opera con memoria local."""
    global redis_client
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3.0)
        await client.ping()
        print(f"✅ Conexión establecida con Redis en: {REDIS_URL}")
        return client
    except Exception as e:
        print(f"⚠️ Redis no disponible ({e}). Operando con estado en memoria local.")
        return None


async def load_station_state(station_key: str):
    """Carga el estado de la estación desde Redis o memoria."""
    global redis_client, memory_fallback_states
    if redis_client:
        try:
            data = await redis_client.get(f"rain_state:{station_key}")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"⚠️ Error leyendo de Redis para {station_key}: {e}")

    return memory_fallback_states.get(station_key)


async def save_station_state(station_key: str, state: dict):
    """Guarda el estado de la estación en Redis y memoria."""
    global redis_client, memory_fallback_states
    memory_fallback_states[station_key] = state
    if redis_client:
        try:
            # TTL de 24 horas para evitar fugas de memoria
            await redis_client.setex(f"rain_state:{station_key}", 86400, json.dumps(state))
        except Exception as e:
            print(f"⚠️ Error guardando en Redis para {station_key}: {e}")


async def sync_state_from_supabase(client: httpx.AsyncClient):
    """Recupera eventos abiertos desde Supabase para inicializar el estado en Redis."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        url = f"{SUPABASE_URL}/rest/v1/rain_events?is_active=eq.true"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        resp = await client.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            active_events = resp.json()
            for ev in active_events:
                s_key = ev['station_key']
                state = {
                    'station_key': s_key,
                    'station_name': ev.get('station_name', s_key),
                    'is_raining': True,
                    'event_id': ev.get('id'),
                    'event_start': ev.get('event_start'),
                    'last_rain': float(ev.get('rain_at_end') or ev.get('rain_at_start') or 0.0),
                    'rain_at_start': float(ev.get('rain_at_start') or 0.0),
                    'last_update': ev.get('updated_at') or ev.get('event_start'),
                    'max_intensity': float(ev.get('max_intensity') or 0.0),
                    'last_station_ts': None
                }
                await save_station_state(s_key, state)
                print(f"🔄 Evento activo #{ev.get('id')} sincronizado desde Supabase para {ev.get('station_name', s_key)}")
    except Exception as e:
        print(f"⚠️ Excepción sincronizando estado desde Supabase: {e}")


# ==============================================================================
# OPERACIONES CON SUPABASE (EVENTOS DE LLUVIA)
# ==============================================================================

async def upsert_rain_event_supabase(client: httpx.AsyncClient, event_data: dict):
    """Inserta o actualiza un evento de lluvia en Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = f"{SUPABASE_URL}/rest/v1/rain_events"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    try:
        resp = await client.post(url, headers=headers, json=[event_data], timeout=10.0)
        if resp.status_code in [200, 201]:
            rows = resp.json()
            return rows[0] if rows else None
        elif resp.status_code == 409:  # Ya existe evento activo
            update_url = f"{url}?station_key=eq.{event_data['station_key']}&is_active=eq.true"
            patch_resp = await client.patch(update_url, headers=headers, json=event_data, timeout=10.0)
            rows = patch_resp.json()
            return rows[0] if rows else None
        else:
            print(f"⚠️ Error en Supabase upsert_rain_event: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"⚠️ Excepción en upsert_rain_event_supabase: {e}")
    return None


async def update_rain_event_supabase(client: httpx.AsyncClient, station_key: str, update_data: dict):
    """Actualiza los datos en tiempo real de un evento activo en Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    url = f"{SUPABASE_URL}/rest/v1/rain_events?station_key=eq.{station_key}&is_active=eq.true"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = await client.patch(url, headers=headers, json=update_data, timeout=10.0)
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️ Excepción actualizando evento de lluvia para {station_key}: {e}")
        return False


async def close_rain_event_supabase(client: httpx.AsyncClient, station_key: str, rain_at_end: float, event_start_iso: str, rain_at_start: float = 0.0):
    """Cierra formalmente un evento de lluvia activo en Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    url = f"{SUPABASE_URL}/rest/v1/rain_events?station_key=eq.{station_key}&is_active=eq.true"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        now_dt = datetime.utcnow()
        now_iso = now_dt.isoformat() + "+00:00"

        start_dt = datetime.fromisoformat(event_start_iso.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            duration_minutes = int((now_dt - start_dt).total_seconds() / 60)
        else:
            duration_minutes = int((now_dt.replace(tzinfo=start_dt.tzinfo) - start_dt).total_seconds() / 60)

        rain_accumulated = round(rain_at_end - rain_at_start, 2) if rain_at_end >= rain_at_start else 0.10
        if rain_accumulated <= 0:
            rain_accumulated = 0.10

        update_payload = {
            "is_active": False,
            "event_end": now_iso,
            "rain_at_end": float(rain_at_end),
            "rain_accumulated": float(rain_accumulated),
            "duration_minutes": max(1, duration_minutes),
            "updated_at": now_iso
        }

        resp = await client.patch(url, headers=headers, json=update_payload, timeout=10.0)
        if resp.status_code in [200, 204]:
            print(f"✅ Evento de lluvia CERRADO en Supabase para {station_key} (Total: {rain_accumulated} mm, Duración: {duration_minutes} min)")
        else:
            print(f"⚠️ Error cerrando evento de lluvia: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"⚠️ Excepción cerrando evento en Supabase: {e}")


# ==============================================================================
# MOTOR DE DETECCIÓN Y PROCESAMIENTO DE LLUVIA
# ==============================================================================

async def process_telemetry_event(client: httpx.AsyncClient, event: dict):
    """Procesa una lectura meteorológica entrante y aplica la máquina de estados de lluvia."""
    payload = event.get('payload', {})
    station_key = str(event.get('station_key'))
    station_name = str(event.get('station_name'))

    # Lectura de lluvia (prioriza acumulado diario, con fallback a rain_rate_mm)
    rain_daily = safe_float(payload.get('rain_daily_mm'))
    if rain_daily is None:
        rain_daily = safe_float(payload.get('rain_rate_mm'))
    if rain_daily is None:
        return

    rain_rate_mm_h = safe_float(payload.get('rain_rate_mm_h')) or 0.0
    station_ts = event.get('event_ts') or payload.get('timestamp')
    current_time_iso = datetime.utcnow().isoformat() + "+00:00"
    current_dt = datetime.utcnow()

    # Cargar estado
    state = await load_station_state(station_key)

    if not state:
        state = {
            'station_key': station_key,
            'station_name': station_name,
            'last_rain': rain_daily,
            'last_update': current_time_iso,
            'last_station_ts': station_ts,
            'is_raining': False,
            'event_start': None,
            'rain_at_start': rain_daily,
            'max_intensity': rain_rate_mm_h
        }
        await save_station_state(station_key, state)
        print(f"🌱 Estado inicializado para {station_name} (Lluvia actual: {rain_daily:.2f} mm)")
        return

    # Evitar procesamiento redundante si el timestamp de la estación no cambió
    if state.get('last_station_ts') and station_ts and state['last_station_ts'] == station_ts:
        return

    state['last_station_ts'] = station_ts
    last_rain = float(state.get('last_rain', rain_daily))
    rain_increment = round(rain_daily - last_rain, 2)
    current_intensity = max(rain_rate_mm_h, rain_increment)

    # 1. DETECTAR RESET DE ACUMULADOR DIARIO (Medianoche)
    if rain_daily < last_rain:
        print(f"⚠️ Reset de acumulador detectado en {station_name} ({last_rain:.2f} mm -> {rain_daily:.2f} mm)")
        if state.get('is_raining'):
            await close_rain_event_supabase(client, station_key, last_rain, state['event_start'], state['rain_at_start'])
            state['is_raining'] = False
            state['event_start'] = None
        state['last_rain'] = rain_daily
        state['rain_at_start'] = rain_daily
        state['last_update'] = current_time_iso
        await save_station_state(station_key, state)
        return

    # 2. DETECTAR INICIO DE LLUVIA
    if not state.get('is_raining') and (rain_increment >= RAIN_START_THRESHOLD or rain_rate_mm_h > 0):
        print(f"\n🌧️  ¡LLUVIA DETECTADA en {station_name}!")
        print(f"   Incremento: {rain_increment:.2f} mm | Tasa instantánea: {rain_rate_mm_h:.2f} mm/h")
        print(f"   Valor anterior: {last_rain:.2f} mm -> Actual: {rain_daily:.2f} mm")

        state['is_raining'] = True
        state['event_start'] = current_time_iso
        state['rain_at_start'] = last_rain
        state['last_rain'] = rain_daily
        state['last_update'] = current_time_iso
        state['max_intensity'] = current_intensity

        event_payload = {
            'station_key': station_key,
            'station_name': station_name,
            'event_start': current_time_iso,
            'is_active': True,
            'rain_at_start': float(last_rain),
            'rain_accumulated': float(rain_increment if rain_increment > 0 else 0.10),
            'max_intensity': float(current_intensity),
            'updated_at': current_time_iso
        }

        res = await upsert_rain_event_supabase(client, event_payload)
        if res:
            state['event_id'] = res.get('id')
            print(f"   ✅ Evento registrado en base de datos (ID: {res.get('id')})")

        await save_station_state(station_key, state)
        return

    # 3. SI ESTÁ LLOVIENDO: CONTINUACIÓN O CIERRE POR TIMEOUT
    if state.get('is_raining'):
        last_update_dt = datetime.fromisoformat(state['last_update'].replace('Z', '+00:00')).replace(tzinfo=None)
        start_dt = datetime.fromisoformat(state['event_start'].replace('Z', '+00:00')).replace(tzinfo=None)

        time_since_last_update_min = (current_dt - last_update_dt).total_seconds() / 60
        event_duration_min = (current_dt - start_dt).total_seconds() / 60

        # Cerrar evento si hay inactividad (30 min) o se superó la duración máxima (12h)
        if (rain_increment <= 0 and rain_rate_mm_h <= 0 and time_since_last_update_min >= NO_RAIN_TIMEOUT_MINUTES) or event_duration_min >= MAX_EVENT_DURATION_MINUTES:
            reason = "duración máxima (12h)" if event_duration_min >= MAX_EVENT_DURATION_MINUTES else f"inactividad ({NO_RAIN_TIMEOUT_MINUTES} min)"
            print(f"\n✅ Fin de lluvia en {station_name} por {reason}.")
            await close_rain_event_supabase(client, station_key, rain_daily, state['event_start'], state['rain_at_start'])
            state['is_raining'] = False
            state['event_start'] = None
            state['rain_at_start'] = rain_daily
            state['last_rain'] = rain_daily
            state['last_update'] = current_time_iso
            await save_station_state(station_key, state)
            return

        # Si hay incremento o tasa positiva, actualizar acumulación en tiempo real
        if rain_increment > 0 or rain_rate_mm_h > 0:
            accumulated = round(rain_daily - float(state['rain_at_start']), 2)
            new_max_intensity = float(max(current_intensity, state.get('max_intensity', 0.0)))
            state['max_intensity'] = new_max_intensity
            state['last_rain'] = rain_daily
            state['last_update'] = current_time_iso

            print(f"🌧️  Lluvia continúa en {station_name}: Acumulado {accumulated:.2f} mm | Tasa: {current_intensity:.2f} mm/h")

            update_data = {
                'rain_accumulated': float(accumulated),
                'max_intensity': new_max_intensity,
                'updated_at': current_time_iso
            }
            await update_rain_event_supabase(client, station_key, update_data)
            await save_station_state(station_key, state)
            return

    # Si no llueve y no hubo incremento, solo actualizar la última lectura
    state['last_rain'] = rain_daily
    await save_station_state(station_key, state)


# ==============================================================================
# MONITOR PERIÓDICO DE FONDO (CIERRE DE EVENTOS INACTIVOS)
# ==============================================================================

async def background_inactivity_checker(client: httpx.AsyncClient):
    """Chequea periódicamente si alguna estación quedó en lluvia activa sin recibir datos nuevos."""
    while running:
        await asyncio.sleep(180)  # Cada 3 minutos
        if not running:
            break
        try:
            stations = ['finca1', 'finca2', 'finca3']
            for s_key in stations:
                state = await load_station_state(s_key)
                if state and state.get('is_raining') and state.get('last_update'):
                    last_upd = datetime.fromisoformat(state['last_update'].replace('Z', '+00:00')).replace(tzinfo=None)
                    diff_min = (datetime.utcnow() - last_upd).total_seconds() / 60
                    if diff_min >= NO_RAIN_TIMEOUT_MINUTES:
                        print(f"⏰ [Monitor de fondo] Cerrando evento por timeout en {state.get('station_name', s_key)} ({diff_min:.1f} min sin lluvia)")
                        await close_rain_event_supabase(client, s_key, state['last_rain'], state['event_start'], state['rain_at_start'])
                        state['is_raining'] = False
                        state['event_start'] = None
                        await save_station_state(s_key, state)
        except Exception as e:
            print(f"⚠️ Error en background_inactivity_checker: {e}")


# ==============================================================================
# BUCLE PRINCIPAL DE CONSUMO
# ==============================================================================

async def run_rain_engine():
    global running, redis_client

    print(f"\n{'='*70}")
    print(f"🌧️  INICIANDO MOTOR ASÍNCRONO DE ALERTAS DE LLUVIA (REDIS + KAFKA)")
    print(f"📊 Broker: {KAFKA_BOOTSTRAP} | Tópico: {KAFKA_TOPIC}")
    print(f"🔔 Umbral inicio: {RAIN_START_THRESHOLD} mm | Timeout inactividad: {NO_RAIN_TIMEOUT_MINUTES} min")
    print(f"⚡ Consumo de RAM estimado: < 40 MB (Reemplazo de Apache Spark)")
    print(f"{'='*70}\n")

    redis_client = await get_redis_connection()

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=KAFKA_GROUP,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    for i in range(1, 11):
        try:
            await consumer.start()
            print("✅ Conectado exitosamente a Kafka/Redpanda.")
            break
        except Exception as e:
            print(f"⏳ Esperando broker Kafka ({i}/10)... Error: {e}")
            await asyncio.sleep(3)
    else:
        print("❌ No se pudo conectar a Kafka tras 10 intentos. Abortando.")
        return

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        # Sincronizar estado inicial desde Supabase
        await sync_state_from_supabase(http_client)

        # Iniciar tarea en segundo plano para verificación de inactividad
        monitor_task = asyncio.create_task(background_inactivity_checker(http_client))

        try:
            while running:
                try:
                    msg = await asyncio.wait_for(consumer.getone(), timeout=2.0)
                    if msg and msg.value:
                        await process_telemetry_event(http_client, msg.value)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            monitor_task.cancel()
            await consumer.stop()
            if redis_client:
                await redis_client.close()
            print("🛑 Motor de alertas de lluvia detenido limpiamente.")


def handle_stop(signame):
    global running
    print(f"\n🛑 Señal {signame} recibida. Cerrando motor de alertas...")
    running = False


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for signame in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, signame), lambda s=signame: handle_stop(s))
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(run_rain_engine())
    except KeyboardInterrupt:
        handle_stop('KeyboardInterrupt')
    finally:
        loop.close()


if __name__ == '__main__':
    main()
