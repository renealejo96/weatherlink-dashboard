#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de prueba para verificar la conexión con WeatherLink API"""

import os
from dotenv import load_dotenv
from weatherlink_client import WeatherLinkClient

# Cargar variables de entorno
load_dotenv()

print("=" * 60)
print("PRUEBA DE CONEXIÓN A WEATHERLINK API")
print("=" * 60)

# Probar cada estación
stations = {
    'PYGANFLOR': {
        'api_key': os.getenv('FINCA1_API_KEY'),
        'api_secret': os.getenv('FINCA1_API_SECRET'),
        'station_id': os.getenv('FINCA1_STATION_ID')
    },
    'Urcuquí': {
        'api_key': os.getenv('FINCA2_API_KEY'),
        'api_secret': os.getenv('FINCA2_API_SECRET'),
        'station_id': os.getenv('FINCA2_STATION_ID')
    },
    'Malchinguí': {
        'api_key': os.getenv('FINCA3_API_KEY'),
        'api_secret': os.getenv('FINCA3_API_SECRET'),
        'station_id': os.getenv('FINCA3_STATION_ID')
    }
}

for name, config in stations.items():
    print(f"\n🌤️  Probando estación: {name}")
    print(f"   Station ID: {config['station_id']}")
    
    try:
        client = WeatherLinkClient(
            config['api_key'],
            config['api_secret'],
            config['station_id']
        )
        
        # Intentar obtener datos actuales
        data = client.get_current_conditions()
        
        if data:
            print(f"   ✅ Conexión exitosa!")
            if 'temperature' in data:
                temp = data.get('temperature')
                hum = data.get('humidity')
                print(f"   📊 Temperatura: {temp}°F" if temp else "   📊 Temperatura: N/A")
                print(f"   💧 Humedad: {hum}%" if hum else "   💧 Humedad: N/A")
        else:
            print(f"   ⚠️  Sin datos disponibles")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
