"""
API endpoints para obtener datos de Supabase
para visualización en dashboard
"""

import os
import requests
from datetime import datetime, timedelta
from flask import jsonify, request
from dotenv import load_dotenv

load_dotenv()

# Configuración de Supabase REST API
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def supabase_request(endpoint, params=None):
    """Hace una petición GET a la API REST de Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_latest_readings():
    """
    Obtiene las últimas lecturas de todas las estaciones
    Ideal para el dashboard principal
    """
    try:
        # Usar la vista latest_readings que creamos en SQL
        rows = supabase_request('latest_readings')
        
        # Formatear para el dashboard
        data = []
        for row in rows:
            data.append({
                'station': row['station_name'],
                'station_key': row['station_key'],
                'ultima_actualizacion': row['event_time'],
                'temperatura_c': float(row['temp_celsius']) if row.get('temp_celsius') else None,
                'humedad': float(row['humidity']) if row.get('humidity') else None,
                'dpv_kpa': float(row['vpd_kpa']) if row.get('vpd_kpa') else None,
                'radiacion_solar': float(row['solar_radiation']) if row.get('solar_radiation') else None,
                'lluvia_mm': float(row['rain_mm']) if row.get('rain_mm') else None,
                'velocidad_viento': float(row['wind_speed']) if row.get('wind_speed') else None,
            })
        
        return {'success': True, 'data': data}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_station_history(station_key: str, hours: int = 24):
    """
    Obtiene el historial de una estación para gráficas
    """
    try:
        # Calcular timestamp de inicio
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Parámetros para filtrar y ordenar
        params = {
            'select': 'event_time,temp_celsius,humidity,vpd_kpa,rain_mm,solar_radiation',
            'station_key': f'eq.{station_key}',
            'event_time': f'gte.{start_time}',
            'order': 'event_time.asc'
        }
        
        rows = supabase_request('weather_readings', params)
        
        # Formatear para gráficas
        timestamps = []
        temp = []
        humidity = []
        vpd = []
        rain = []
        solar = []
        
        for row in rows:
            timestamps.append(row['event_time'])
            temp.append(float(row['temp_celsius']) if row.get('temp_celsius') else None)
            humidity.append(float(row['humidity']) if row.get('humidity') else None)
            vpd.append(float(row['vpd_kpa']) if row.get('vpd_kpa') else None)
            rain.append(float(row['rain_mm']) if row.get('rain_mm') else None)
            solar.append(float(row['solar_radiation']) if row.get('solar_radiation') else None)
        
        return {
            'success': True,
            'data': {
                'timestamps': timestamps,
                'temperatura': temp,
                'humedad': humidity,
                'dpv': vpd,
                'lluvia': rain,
                'radiacion_solar': solar
            }
        }
    
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_daily_summary(station_key: str, days: int = 7):
    """
    Obtiene resumen diario usando la función SQL
    """
    try:
        # Llamar a la función RPC de Supabase
        url = f"{SUPABASE_URL}/rest/v1/rpc/get_daily_averages"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            'p_station_key': station_key,
            'p_days': days
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return {'success': True, 'data': response.json()}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_all_stations_comparison():
    """
    Compara los últimos datos de todas las estaciones
    """
    try:
        latest = get_latest_readings()
        if not latest['success']:
            return latest
        
        comparison = {
            'labels': [],
            'temperatura': [],
            'humedad': [],
            'dpv': [],
            'radiacion': []
        }
        
        for station in latest['data']:
            comparison['labels'].append(station['station'])
            comparison['temperatura'].append(station['temperatura_c'])
            comparison['humedad'].append(station['humedad'])
            comparison['dpv'].append(station['dpv_kpa'])
            comparison['radiacion'].append(station['radiacion_solar'])
        
        return {'success': True, 'data': comparison}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================
# Funciones auxiliares para integrar con Flask
# ============================================

def register_supabase_routes(app):
    """
    Registra las rutas de Supabase en la app Flask
    """
    
    @app.route('/api/latest')
    def api_latest_readings():
        """GET /api/latest - Últimas lecturas de todas las estaciones"""
        result = get_latest_readings()
        if result['success']:
            return jsonify(result['data'])
        return jsonify({'error': result['error']}), 500
    
    @app.route('/api/station/<station_key>/history')
    def api_station_history(station_key):
        """GET /api/station/<key>/history?hours=24 - Historial de una estación"""
        hours = int(request.args.get('hours', 24))
        result = get_station_history(station_key, hours)
        if result['success']:
            return jsonify(result['data'])
        return jsonify({'error': result['error']}), 500
    
    @app.route('/api/station/<station_key>/daily')
    def api_daily_summary(station_key):
        """GET /api/station/<key>/daily?days=7 - Resumen diario"""
        days = int(request.args.get('days', 7))
        result = get_daily_summary(station_key, days)
        if result['success']:
            return jsonify(result['data'])
        return jsonify({'error': result['error']}), 500
    
    @app.route('/api/comparison')
    def api_comparison():
        """GET /api/comparison - Comparación de todas las estaciones"""
        result = get_all_stations_comparison()
        if result['success']:
            return jsonify(result['data'])
        return jsonify({'error': result['error']}), 500


# ============================================
# Script de prueba standalone
# ============================================

if __name__ == '__main__':
    print("=" * 80)
    print("🧪 PROBANDO CONEXIÓN CON SUPABASE")
    print("=" * 80)
    print()
    
    # Test 1: Últimas lecturas
    print("📊 Test 1: Obtener últimas lecturas...")
    result = get_latest_readings()
    if result['success']:
        print(f"✅ {len(result['data'])} estaciones encontradas")
        for station in result['data']:
            print(f"   - {station['station']}: {station['temperatura_c']}°C, {station['humedad']}%, DPV {station['dpv_kpa']} kPa")
    else:
        print(f"❌ Error: {result['error']}")
    
    print()
    
    # Test 2: Historial de una estación
    print("📈 Test 2: Historial de FINCA1 (últimas 24h)...")
    result = get_station_history('finca1', hours=24)
    if result['success']:
        data = result['data']
        print(f"✅ {len(data['timestamps'])} registros encontrados")
        if len(data['timestamps']) > 0:
            print(f"   Primer registro: {data['timestamps'][0]}")
            print(f"   Último registro: {data['timestamps'][-1]}")
    else:
        print(f"❌ Error: {result['error']}")
    
    print()
    
    # Test 3: Comparación
    print("🔬 Test 3: Comparación de estaciones...")
    result = get_all_stations_comparison()
    if result['success']:
        data = result['data']
        print(f"✅ Comparando {len(data['labels'])} estaciones")
        for i, label in enumerate(data['labels']):
            print(f"   - {label}: Temp={data['temperatura'][i]}°C, Hum={data['humedad'][i]}%")
    else:
        print(f"❌ Error: {result['error']}")
    
    print()
    print("=" * 80)
