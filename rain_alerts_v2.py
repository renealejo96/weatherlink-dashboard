"""
Sistema Avanzado de Alertas de Lluvia con Estado Persistente
Detecta inicio/fin de eventos de lluvia y calcula acumulados en tiempo real
"""

import os
import math
import requests
import json
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, from_unixtime, lit, window
)
from pyspark.sql.types import *


# Configuración
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')
KAFKA_TOPIC_RAW = 'weatherlink.raw'

# Umbrales
RAIN_START_THRESHOLD = 0.1  # mm de incremento para detectar inicio
NO_RAIN_TIMEOUT_MINUTES = 30  # minutos sin incremento para cerrar evento


class RainEventState:
    """Estado del evento de lluvia para una estación"""
    def __init__(self):
        self.is_raining = False
        self.event_id = None
        self.event_start = None
        self.rain_at_start = 0.0
        self.last_rain_value = 0.0
        self.last_update = None
        self.rain_accumulated = 0.0
        self.max_intensity = 0.0


def safe_float(value):
    """Convierte a float validando que no sea NaN o Infinity"""
    if value is None:
        return None
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def upsert_rain_event(event_data):
    """Crear o actualizar evento de lluvia en Supabase"""
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
        # Intentar insertar
        response = requests.post(url, headers=headers, json=[event_data])
        
        if response.status_code in [200, 201]:
            return response.json()[0] if response.json() else None
        elif response.status_code == 409:  # Ya existe
            # Actualizar registro existente
            update_url = f"{url}?station_key=eq.{event_data['station_key']}&is_active=eq.true"
            headers["Prefer"] = "return=representation"
            response = requests.patch(update_url, headers=headers, json=event_data)
            return response.json()[0] if response.json() else None
        else:
            print(f"⚠️  Error guardando evento: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Excepción en upsert_rain_event: {e}")
        return None


def close_rain_event(station_key, rain_at_end, event_start):
    """Cerrar evento de lluvia activo"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    
    url = f"{SUPABASE_URL}/rest/v1/rain_events"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        update_url = f"{url}?station_key=eq.{station_key}&is_active=eq.true"
        event_end = datetime.now()
        event_end_iso = event_end.isoformat()
        
        # Calcular duración en minutos
        duration_minutes = int((event_end - event_start).total_seconds() / 60)
        
        update_data = {
            "is_active": False,
            "event_end": event_end_iso,
            "rain_at_end": float(rain_at_end),
            "duration_minutes": duration_minutes,
            "updated_at": event_end_iso
        }
        
        response = requests.patch(update_url, headers=headers, json=update_data)
        if response.status_code in [200, 204]:
            print(f"✅ Evento de lluvia cerrado para {station_key}")
            print(f"   Duración total: {duration_minutes} minutos")
        else:
            print(f"⚠️  Error cerrando evento: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error en close_rain_event: {e}")


def process_rain_data(batch_df, batch_id):
    """
    Procesa batch de datos detectando eventos de lluvia
    Mantiene estado en memoria (simplificado para esta versión)
    """
    global station_states
    
    if batch_df.isEmpty():
        return
    
    pandas_df = batch_df.toPandas()
    current_time = datetime.now()
    
    for _, row in pandas_df.iterrows():
        station_key = row['station_key']
        station_name = row['station_name']
        event_time = row['event_time']
        rain_mm = safe_float(row['rain_mm'])
        
        if rain_mm is None:
            continue
        
        # Inicializar estado si no existe
        if station_key not in station_states:
            station_states[station_key] = {
                'last_rain': rain_mm,
                'last_update': current_time,
                'is_raining': False,
                'event_start': None,
                'rain_at_start': rain_mm
            }
            continue
        
        state = station_states[station_key]
        rain_increment = rain_mm - state['last_rain']
        
        # DETECTAR INICIO DE LLUVIA
        if not state['is_raining'] and rain_increment >= RAIN_START_THRESHOLD:
            print(f"\n🌧️  ¡LLUVIA DETECTADA en {station_name}!")
            print(f"   Incremento: {rain_increment:.2f} mm")
            print(f"   Valor anterior: {state['last_rain']:.2f} mm")
            print(f"   Valor actual: {rain_mm:.2f} mm")
            
            state['is_raining'] = True
            state['event_start'] = current_time
            state['rain_at_start'] = state['last_rain']  # Valor ANTES del incremento
            
            # Guardar en Supabase
            event_data = {
                'station_key': station_key,
                'station_name': station_name,
                'event_start': state['event_start'].isoformat(),
                'is_active': True,
                'rain_at_start': float(state['rain_at_start']),
                'rain_accumulated': float(rain_increment),
                'max_intensity': float(rain_increment),  # Por ahora
                'updated_at': current_time.isoformat()
            }
            
            result = upsert_rain_event(event_data)
            if result:
                print(f"   ✅ Evento registrado en base de datos (ID: {result.get('id')})")
        
        # ACTUALIZAR EVENTO ACTIVO
        elif state['is_raining'] and rain_increment > 0:
            accumulated = rain_mm - state['rain_at_start']
            duration = (current_time - state['event_start']).total_seconds() / 60
            
            print(f"🌧️  Lluvia continúa en {station_name}")
            print(f"   Acumulado desde inicio: {accumulated:.2f} mm")
            print(f"   Duración: {duration:.1f} minutos")
            
            # Actualizar en Supabase
            event_data = {
                'rain_accumulated': float(accumulated),
                'rain_at_end': float(rain_mm),  # Actualizar también el valor final
                'duration_minutes': int(duration),
                'updated_at': current_time.isoformat()
            }
            
            url = f"{SUPABASE_URL}/rest/v1/rain_events"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            update_url = f"{url}?station_key=eq.{station_key}&is_active=eq.true"
            requests.patch(update_url, headers=headers, json=event_data)
        
        # DETECTAR FIN DE LLUVIA (sin incremento por X minutos)
        elif state['is_raining']:
            time_since_last = (current_time - state['last_update']).total_seconds() / 60
            
            if rain_increment == 0 and time_since_last >= NO_RAIN_TIMEOUT_MINUTES:
                accumulated = rain_mm - state['rain_at_start']
                print(f"\n✅ Fin de lluvia en {station_name}")
                print(f"   Total caído: {accumulated:.2f} mm")
                print(f"   Duración: {(current_time - state['event_start']).total_seconds() / 60:.1f} min")
                
                close_rain_event(station_key, rain_mm, state['event_start'])
                state['is_raining'] = False
                state['event_start'] = None
        
        # Actualizar estado
        state['last_rain'] = rain_mm
        state['last_update'] = current_time


def build_spark():
    """Construir sesión Spark"""
    return (
        SparkSession.builder
        .appName('WeatherLink-RainAlerts-v2')
        .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0')
        .config('spark.sql.streaming.statefulOperator.checkCorrectness.enabled', 'false')
        .getOrCreate()
    )


# Estado global (en producción usar checkpointing de Spark)
station_states = {}


def main():
    """Streaming principal"""
    
    spark = build_spark()
    spark.sparkContext.setLogLevel('WARN')

    # Kafka source
    raw = (
        spark.readStream
        .format('kafka')
        .option('kafka.bootstrap.servers', KAFKA_BOOTSTRAP)
        .option('subscribe', KAFKA_TOPIC_RAW)
        .option('startingOffsets', 'latest')
        .load()
    )

    # Schema
    payload_schema = StructType([
        StructField('timestamp', LongType(), True),
        StructField('temperature', DoubleType(), True),
        StructField('humidity', DoubleType(), True),
        StructField('rain_rate', DoubleType(), True),
        StructField('rain_rate_mm', DoubleType(), True),
        StructField('rain_rate_field', StringType(), True),
    ])

    event_schema = StructType([
        StructField('station_key', StringType(), True),
        StructField('station_name', StringType(), True),
        StructField('station_id', StringType(), True),
        StructField('event_ts', LongType(), True),
        StructField('payload', payload_schema, True),
    ])

    # Parsear
    parsed = raw.select(
        from_json(col('value').cast('string'), event_schema).alias('evt')
    ).select('evt.*')

    # Extraer datos
    df = (
        parsed
        .withColumn('event_time', to_timestamp(from_unixtime(col('event_ts'))))
        .withColumn('rain_mm', col('payload.rain_rate_mm'))
        .select('station_key', 'station_name', 'event_time', 'rain_mm')
        .filter(col('rain_mm').isNotNull())
    )

    # Procesar
    query = (
        df
        .writeStream
        .foreachBatch(process_rain_data)
        .outputMode('append')
        .option('checkpointLocation', '/tmp/rain-alerts-checkpoint')
        .start()
    )

    print(f"\n{'='*70}")
    print(f"🌧️  SISTEMA DE ALERTAS DE LLUVIA v2.0")
    print(f"{'='*70}")
    print(f"📊 Kafka Topic: {KAFKA_TOPIC_RAW}")
    print(f"💾 Base de datos: rain_events table")
    print(f"🔔 Umbral de detección: {RAIN_START_THRESHOLD} mm")
    print(f"⏱️  Timeout sin lluvia: {NO_RAIN_TIMEOUT_MINUTES} minutos")
    print(f"{'='*70}\n")
    print(f"⏰ Esperando eventos de lluvia...\n")

    query.awaitTermination()


if __name__ == '__main__':
    main()
