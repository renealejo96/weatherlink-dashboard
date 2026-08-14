"""
Consumidor Asíncrono Ultraligero: Kafka -> Supabase (Lecturas Meteorológicas)
Reemplaza Apache Spark Streaming para reducir el consumo de RAM de ~2 GB a < 40 MB.
"""

import os
import sys
import json
import math
import asyncio
import signal
from datetime import datetime
import httpx
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

load_dotenv()

# Configuración de Entorno
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_RAW', 'weatherlink.raw')
KAFKA_GROUP = os.getenv('KAFKA_CONSUMER_GROUP_WEATHER', 'weather-supabase-consumer')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

BATCH_SIZE = int(os.getenv('STREAM_BATCH_SIZE', '10'))
FLUSH_INTERVAL_SEC = float(os.getenv('STREAM_FLUSH_INTERVAL', '3.0'))

running = True


def safe_float(value):
    """Valida y convierte a float evitando NaN e Infinity."""
    if value is None:
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def calculate_vpd(temp_f, humidity):
    """Calcula el DPV (VPD) en kPa usando la ecuación de Tetens."""
    if temp_f is None or humidity is None:
        return None
    try:
        temp_c = (temp_f - 32.0) * 5.0 / 9.0
        vpsat = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        vpactual = (humidity / 100.0) * vpsat
        return round(vpsat - vpactual, 3)
    except Exception:
        return None


def transform_event(event):
    """Transforma el payload crudo del evento a la estructura de weather_readings."""
    payload = event.get('payload', {})
    event_ts = event.get('event_ts') or payload.get('timestamp')
    
    event_time_iso = None
    if event_ts:
        event_time_iso = datetime.utcfromtimestamp(event_ts).isoformat() + "+00:00"
    else:
        event_time_iso = datetime.utcnow().isoformat() + "+00:00"

    temp_f = safe_float(payload.get('temperature'))
    humidity = safe_float(payload.get('humidity'))
    temp_c = round((temp_f - 32.0) * 5.0 / 9.0, 2) if temp_f is not None else None
    vpd_kpa = calculate_vpd(temp_f, humidity)

    rain_daily = safe_float(payload.get('rain_daily_mm'))
    rain_rate = safe_float(payload.get('rain_rate_mm_h')) or 0.0
    rain_15m = safe_float(payload.get('rain_last_15_min_mm'))
    legacy_rain = safe_float(payload.get('rain_rate_mm'))
    is_raining = bool(payload.get('is_raining')) if payload.get('is_raining') is not None else (rain_rate > 0)

    return {
        'station_key': str(event.get('station_key')),
        'station_name': str(event.get('station_name')),
        'station_id': str(event.get('station_id')),
        'event_time': event_time_iso,
        'temp_celsius': temp_c,
        'temp_fahrenheit': temp_f,
        'humidity': humidity,
        'vpd_kpa': vpd_kpa,
        'dew_point': safe_float(payload.get('dew_point')),
        'rain_mm': legacy_rain if legacy_rain is not None else rain_daily,
        'rain_field': str(payload.get('rain_rate_field')) if payload.get('rain_rate_field') else None,
        'rain_daily_mm': rain_daily if rain_daily is not None else legacy_rain,
        'rain_rate_mm_h': rain_rate,
        'rain_last_15_min_mm': rain_15m,
        'is_raining': is_raining,
        'solar_radiation': safe_float(payload.get('solar_radiation')),
        'uv_index': safe_float(payload.get('uv_index')),
        'wind_speed': safe_float(payload.get('wind_speed')),
        'wind_dir': safe_float(payload.get('wind_dir')),
    }


async def insert_batch_to_supabase(client: httpx.AsyncClient, records: list):
    """Envía un lote de registros a Supabase REST API usando Upsert."""
    if not records or not SUPABASE_URL or not SUPABASE_KEY:
        return False

    url = f"{SUPABASE_URL}/rest/v1/weather_readings"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    for attempt in range(1, 4):
        try:
            resp = await client.post(url, headers=headers, json=records, timeout=10.0)
            if resp.status_code in [200, 201, 204, 409]:
                return True
            print(f"⚠️ Error insertando lote (Intento {attempt}/3): HTTP {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"⚠️ Excepción HTTP en insert_batch (Intento {attempt}/3): {e}")
        await asyncio.sleep(1.0 * attempt)

    return False


async def run_consumer():
    """Bucle principal de consumo asíncrono."""
    global running

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: SUPABASE_URL y SUPABASE_KEY son requeridas en .env")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🚀 INICIANDO CONSUMIDOR ASÍNCRONO ULTRALIGERO (KAFKA -> SUPABASE)")
    print(f"📊 Broker: {KAFKA_BOOTSTRAP} | Tópico: {KAFKA_TOPIC}")
    print(f"💾 Destino: {SUPABASE_URL}/rest/v1/weather_readings")
    print(f"⚡ Consumo de RAM estimado: < 40 MB (Reemplazo de Apache Spark)")
    print(f"{'='*70}\n")

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=KAFKA_GROUP,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    # Reintentos de conexión con Kafka
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

    buffer = []
    last_flush_time = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        try:
            while running:
                try:
                    # Polling con timeout de 1s para permitir vaciado periódico
                    msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                    if msg and msg.value:
                        transformed = transform_event(msg.value)
                        buffer.append(transformed)
                except asyncio.TimeoutError:
                    pass

                now = asyncio.get_event_loop().time()
                time_since_flush = now - last_flush_time

                # Vaciar buffer si alcanzó el tamaño o el tiempo
                if len(buffer) >= BATCH_SIZE or (buffer and time_since_flush >= FLUSH_INTERVAL_SEC):
                    records_to_send = list(buffer)
                    buffer.clear()
                    last_flush_time = now

                    ok = await insert_batch_to_supabase(http_client, records_to_send)
                    if ok:
                        stations = ", ".join(set(r['station_name'] for r in records_to_send))
                        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] {len(records_to_send)} lecturas guardadas en Supabase ({stations})")
                    else:
                        print(f"❌ Falló la inserción de {len(records_to_send)} registros")

        except asyncio.CancelledError:
            pass
        finally:
            # Guardar registros remanentes antes de salir
            if buffer:
                print(f"💾 Guardando {len(buffer)} registros remanentes antes de cerrar...")
                await insert_batch_to_supabase(http_client, buffer)
            await consumer.stop()
            print("🛑 Consumidor detenido limpiamente.")


def handle_stop(signame):
    global running
    print(f"\n🛑 Señal {signame} recibida. Cerrando consumidor...")
    running = False


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for signame in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, signame), lambda s=signame: handle_stop(s))
        except NotImplementedError:
            pass  # Windows no soporta add_signal_handler para todas las señales

    try:
        loop.run_until_complete(run_consumer())
    except KeyboardInterrupt:
        handle_stop('KeyboardInterrupt')
    finally:
        loop.close()


if __name__ == '__main__':
    main()
