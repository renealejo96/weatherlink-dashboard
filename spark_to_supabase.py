"""
Integrador Spark → Supabase
Guarda los datos procesados por Spark directamente en Supabase
"""

import os
import math
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, from_unixtime, lit, expr, when
)
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType
)
import requests
import json


# Configuración de Supabase REST API
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def safe_float(value):
    """Convierte a float validando que no sea NaN o Infinity"""
    if value is None:
        return None
    try:
        val = float(value)
        # Rechazar NaN e Infinity
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def insert_to_supabase_rest(records):
    """Insertar registros usando Supabase REST API"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL y SUPABASE_KEY deben estar definidos")
    
    url = f"{SUPABASE_URL}/rest/v1/weather_readings"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # UPSERT en caso de duplicados
    }
    
    response = requests.post(url, headers=headers, json=records)
    
    # 200, 201, 204 son códigos de éxito
    # 409 es duplicado (ya existe) - también lo tratamos como éxito
    if response.status_code not in [200, 201, 204, 409]:
        raise Exception(f"Error al insertar: {response.status_code} - {response.text}")
    
    return response


def save_to_supabase(batch_df, batch_id):
    """
    Función para guardar cada micro-batch de Spark en Supabase usando REST API
    """
    try:
        # Convertir a pandas para insertar
        pandas_df = batch_df.toPandas()
        
        if len(pandas_df) == 0:
            print(f"⏭️  Batch {batch_id}: Sin datos para insertar")
            return
        
        # Preparar registros para Supabase REST API
        records = []
        for _, row in pandas_df.iterrows():
            # Convertir event_time a string ISO para JSON
            event_time_str = None
            if row['event_time'] is not None:
                try:
                    # pandas.Timestamp tiene método isoformat()
                    event_time_str = row['event_time'].isoformat()
                except AttributeError:
                    # Fallback si no es Timestamp
                    event_time_str = str(row['event_time'])
            
            record = {
                'station_key': str(row['station_key']) if row['station_key'] is not None else None,
                'station_name': str(row['station_name']) if row['station_name'] is not None else None,
                'station_id': int(row['station_id']) if row['station_id'] is not None else None,
                'event_time': event_time_str,
                'temp_celsius': safe_float(row['temp_c']),
                'temp_fahrenheit': safe_float(row['temp_f']),
                'humidity': safe_float(row['humidity']),
                'vpd_kpa': safe_float(row['vpd_kpa']),
                'dew_point': safe_float(row['dew_point']),
                'rain_mm': safe_float(row['rain_mm']),
                'rain_field': str(row['rain_field']) if row['rain_field'] is not None else None,
                'solar_radiation': safe_float(row['solar_radiation']),
                'uv_index': safe_float(row['uv_index']),
                'wind_speed': safe_float(row['wind_speed']),
                'wind_dir': safe_float(row['wind_dir']),
            }
            records.append(record)
        
        # Insertar usando REST API
        response = insert_to_supabase_rest(records)
        
        if response.status_code == 409:
            print(f"⚠️  Batch {batch_id}: {len(records)} registros ya existen (duplicados)")
        else:
            print(f"✅ Batch {batch_id}: {len(records)} registros guardados en Supabase")
        
    except Exception as e:
        print(f"❌ Error en batch {batch_id}: {e}")
        import traceback
        traceback.print_exc()


def build_spark(app_name: str = 'WeatherLinkToSupabase'):
    return (
        SparkSession.builder
        .appName(app_name)
        .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0')
        .config('spark.sql.streaming.checkpointLocation', '/tmp/spark-supabase-checkpoints')
        .getOrCreate()
    )


def main():
    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')
    topic = os.getenv('KAFKA_TOPIC_RAW', 'weatherlink.raw')

    spark = build_spark()
    spark.sparkContext.setLogLevel('WARN')

    # Kafka source
    raw = (
        spark.readStream
        .format('kafka')
        .option('kafka.bootstrap.servers', bootstrap)
        .option('subscribe', topic)
        .option('startingOffsets', 'latest')
        .load()
    )

    # Schema para el JSON event
    payload_schema = StructType([
        StructField('timestamp', LongType(), True),
        StructField('temperature', DoubleType(), True),
        StructField('humidity', DoubleType(), True),
        StructField('rain_rate', DoubleType(), True),
        StructField('rain_rate_mm', DoubleType(), True),
        StructField('rain_rate_field', StringType(), True),
        StructField('solar_radiation', DoubleType(), True),
        StructField('uv_index', DoubleType(), True),
        StructField('dew_point', DoubleType(), True),
        StructField('wind_speed', DoubleType(), True),
        StructField('wind_dir', DoubleType(), True),
    ])

    event_schema = StructType([
        StructField('station_key', StringType(), True),
        StructField('station_name', StringType(), True),
        StructField('station_id', StringType(), True),
        StructField('ingest_ts', LongType(), True),
        StructField('event_ts', LongType(), True),
        StructField('payload', payload_schema, True),
    ])

    parsed = raw.select(
        col('key').cast('string').alias('kafka_key'),
        from_json(col('value').cast('string'), event_schema).alias('evt')
    ).select('kafka_key', 'evt.*')

    # Procesamiento base
    df = (
        parsed
        .withColumn('event_time', to_timestamp(from_unixtime(col('event_ts'))))
        .withColumn('temp_f', col('payload.temperature'))
        .withColumn('humidity', col('payload.humidity'))
        .withColumn('rain_mm', col('payload.rain_rate_mm'))
        .withColumn('rain_field', col('payload.rain_rate_field'))
        .withColumn('solar_radiation', col('payload.solar_radiation'))
        .withColumn('uv_index', col('payload.uv_index'))
        .withColumn('dew_point', col('payload.dew_point'))
        .withColumn('wind_speed', col('payload.wind_speed'))
        .withColumn('wind_dir', col('payload.wind_dir'))
    )

    # Cálculo de VPD en kPa
    df = df.withColumn('temp_c', (col('temp_f') - lit(32)) * lit(5.0) / lit(9.0))
    df = df.withColumn('vpsat', lit(0.6108) * expr('exp((17.27 * temp_c) / (temp_c + 237.3))'))
    df = df.withColumn('vpactual', (col('humidity') / lit(100.0)) * col('vpsat'))
    df = df.withColumn('vpd_kpa', col('vpsat') - col('vpactual'))

    # Seleccionar columnas finales
    final_df = df.select(
        'station_key',
        'station_name',
        'station_id',
        'event_time',
        'temp_c',
        'temp_f',
        'humidity',
        'vpd_kpa',
        'dew_point',
        'rain_mm',
        'rain_field',
        'solar_radiation',
        'uv_index',
        'wind_speed',
        'wind_dir'
    )

    # Escribir a Supabase usando foreachBatch
    query = (
        final_df
        .writeStream
        .foreachBatch(save_to_supabase)
        .outputMode('append')
        .start()
    )

    print(f"🚀 Streaming iniciado: Kafka → Spark → Supabase")
    print(f"📊 Topic: {topic}")
    print(f"💾 Tabla: weather_readings")
    print(f"⏰ Esperando datos...")

    query.awaitTermination()


if __name__ == '__main__':
    main()
