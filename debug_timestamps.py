#!/usr/bin/env python
"""Script para diagnosticar el problema de zona horaria"""
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
from weatherlink_client import WeatherLinkClient

load_dotenv()

# Crear cliente para finca1
client = WeatherLinkClient(
    os.getenv('FINCA1_API_KEY'),
    os.getenv('FINCA1_API_SECRET'),
    os.getenv('FINCA1_STATION_ID')
)

# Obtener datos recientes (últimas 2 horas)
import time
end_ts = int(time.time())
start_ts = end_ts - 7200  # 2 horas atrás

print(f"\n{'='*60}")
print("DIAGNÓSTICO DE TIMESTAMPS DE WEATHERLINK")
print(f"{'='*60}")
print(f"Timestamp actual del sistema: {end_ts}")
print(f"Hora actual del sistema: {datetime.fromtimestamp(end_ts)}")
print(f"Hora actual en UTC: {datetime.utcfromtimestamp(end_ts)}")

ecuador_tz = pytz.timezone('America/Guayaquil')
now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
now_ecuador = now_utc.astimezone(ecuador_tz)
print(f"Hora actual en Ecuador (UTC-5): {now_ecuador.strftime('%Y-%m-%d %H:%M:%S %Z')}")

print(f"\n{'='*60}")
print("Obteniendo últimos registros de WeatherLink...")
print(f"{'='*60}\n")

try:
    data = client.get_historic_data(start_ts, end_ts)
    records = data.get('records', [])
    
    if records:
        print(f"Total de registros obtenidos: {len(records)}\n")
        
        # Mostrar los últimos 3 registros
        for i, record in enumerate(records[-3:], 1):
            ts = record['timestamp']
            
            print(f"Registro #{len(records) - 3 + i}:")
            print(f"  Timestamp crudo: {ts}")
            print(f"  fromtimestamp (local): {datetime.fromtimestamp(ts)}")
            print(f"  utcfromtimestamp: {datetime.utcfromtimestamp(ts)}")
            
            # Método actual (puede estar incorrecto)
            utc_time = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.UTC)
            ecuador_time = utc_time.astimezone(ecuador_tz)
            print(f"  UTC → Ecuador (método actual): {ecuador_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Método alternativo: asumir que ya es hora local
            local_time = datetime.fromtimestamp(ts)
            print(f"  Como hora local directa: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print()
    else:
        print("No se obtuvieron registros")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print(f"{'='*60}")
