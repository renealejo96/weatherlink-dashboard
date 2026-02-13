"""
API endpoints para obtener datos de Supabase
para visualización en dashboard
"""

import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

class SupabaseAPI:
    def __init__(self, url, api_key, timeout=30):
        self.url = url
        self.api_key = api_key
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
        self.timeout = timeout

    def _request(self, method, endpoint, params=None, json=None):
        """Hace una petición a la API REST de Supabase"""
        url = f"{self.url}/rest/v1/{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, params=params, json=json, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # En caso de error, devuelve un diccionario con el error
            return {'success': False, 'error': str(e), 'data': []}

    def get_latest_readings(self):
        """
        Obtiene las últimas lecturas de todas las estaciones
        """
        try:
            rows = self._request('GET', 'latest_readings')
            if isinstance(rows, dict) and 'success' in rows and not rows['success']:
                return rows

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

    def get_station_history(self, station_key: str, hours: int = 24):
        """
        Obtiene el historial de una estación para gráficas
        """
        try:
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            params = {
                'select': 'event_time,temp_celsius,humidity,vpd_kpa,rain_mm,solar_radiation',
                'station_key': f'eq.{station_key}',
                'event_time': f'gte.{start_time}',
                'order': 'event_time.asc'
            }
            rows = self._request('GET', 'weather_readings', params=params)
            if isinstance(rows, dict) and 'success' in rows and not rows['success']:
                return rows

            timestamps, temp, humidity, vpd, rain, solar = [], [], [], [], [], []
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
                    'timestamps': timestamps, 'temperatura': temp, 'humedad': humidity,
                    'dpv': vpd, 'lluvia': rain, 'radiacion_solar': solar
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_daily_summary(self, station_key: str, days: int = 7):
        """
        Obtiene resumen diario usando la función SQL
        """
        try:
            body = {'p_station_key': station_key, 'p_days': days}
            result = self._request('POST', 'rpc/get_daily_averages', json=body)
            if isinstance(result, dict) and 'success' in result and not result['success']:
                return result
            return {'success': True, 'data': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_all_stations_comparison(self):
        """
        Compara los últimos datos de todas las estaciones
        """
        latest = self.get_latest_readings()
        if not latest['success']:
            return latest
        
        comparison = {'labels': [], 'temperatura': [], 'humedad': [], 'dpv': [], 'radiacion': []}
        for station in latest['data']:
            comparison['labels'].append(station['station'])
            comparison['temperatura'].append(station['temperatura_c'])
            comparison['humedad'].append(station['humedad'])
            comparison['dpv'].append(station['dpv_kpa'])
            comparison['radiacion'].append(station['radiacion_solar'])
        
        return {'success': True, 'data': comparison}

    def get_active_rain_events(self):
        """Obtiene eventos de lluvia activos"""
        try:
            params = {
                'is_active': 'eq.true',
                'order': 'event_start.desc'
            }
            data = self._request('GET', 'rain_events', params=params)
            if isinstance(data, dict) and 'success' in data and not data['success']:
                return data
            return {'success': True, 'data': data}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_rain_events_history(self, station_key=None, limit=10):
        """Obtiene historial de eventos de lluvia"""
        try:
            params = {'order': 'event_start.desc', 'limit': limit}
            if station_key:
                params['station_key'] = f'eq.{station_key}'
            
            data = self._request('GET', 'rain_events', params=params)
            if isinstance(data, dict) and 'success' in data and not data['success']:
                return data
            return {'success': True, 'data': data}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_accumulated_rain(self):
        """Obtiene la lluvia acumulada por día y semana"""
        try:
            eight_weeks_ago = (datetime.now() - timedelta(weeks=8)).isoformat()
            params = {
                'event_start': f'gte.{eight_weeks_ago}',
                'order': 'event_start.desc',
                'limit': 1000
            }
            events = self._request('GET', 'rain_events', params=params)
            if isinstance(events, dict) and 'success' in events and not events['success']:
                return events

            by_week = defaultdict(lambda: defaultdict(float))
            by_day = defaultdict(lambda: defaultdict(float))
            
            for event in events:
                rain = event.get('rain_accumulated', 0) or 0
                event_start = datetime.fromisoformat(event['event_start'].replace('Z', '+00:00'))
                
                year, week, _ = event_start.isocalendar()
                week_key = f"{year % 100:02d}-{week:02d}"
                day_key = event_start.strftime('%Y-%m-%d')
                
                by_week[event['station_key']][week_key] += rain
                by_day[event['station_key']][day_key] += rain
            
            result = {
                'by_week': {k: dict(v) for k, v in by_week.items()},
                'by_day': {k: dict(v) for k, v in by_day.items()}
            }
            return {'success': True, 'data': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================
# Script de prueba standalone
# ============================================

if __name__ == '__main__':
    load_dotenv()
    
    # Asegúrate de que las variables de entorno están cargadas
    SUPABASE_URL_TEST = os.getenv('SUPABASE_URL')
    SUPABASE_KEY_TEST = os.getenv('SUPABASE_KEY')

    if not SUPABASE_URL_TEST or not SUPABASE_KEY_TEST:
        print("❌ Error: Las variables de entorno SUPABASE_URL y SUPABASE_KEY son necesarias.")
    else:
        api = SupabaseAPI(url=SUPABASE_URL_TEST, api_key=SUPABASE_KEY_TEST)
        
        print("=" * 80)
        print("🧪 PROBANDO CONEXIÓN CON SUPABASE")
        print("=" * 80)
        
        # Test 1: Últimas lecturas
        print("\n📊 Test 1: Obtener últimas lecturas...")
        result = api.get_latest_readings()
        if result['success']:
            print(f"✅ {len(result['data'])} estaciones encontradas")
            for station in result['data']:
                print(f"   - {station['station']}: {station.get('temperatura_c')}°C, {station.get('humedad')}%, DPV {station.get('dpv_kpa')} kPa")
        else:
            print(f"❌ Error: {result['error']}")
        
        # Test 2: Historial de una estación
        print("\n📈 Test 2: Historial de 'finca1' (últimas 24h)...")
        result = api.get_station_history('finca1', hours=24)
        if result['success']:
            data = result['data']
            print(f"✅ {len(data['timestamps'])} registros encontrados")
            if len(data['timestamps']) > 0:
                print(f"   Primer registro: {data['timestamps'][0]}")
                print(f"   Último registro: {data['timestamps'][-1]}")
        else:
            print(f"❌ Error: {result['error']}")
        
        # Test 3: Comparación
        print("\n🔬 Test 3: Comparación de estaciones...")
        result = api.get_all_stations_comparison()
        if result['success']:
            data = result['data']
            print(f"✅ Comparando {len(data['labels'])} estaciones")
            for i, label in enumerate(data['labels']):
                print(f"   - {label}: Temp={data['temperatura'][i]}°C, Hum={data['humedad'][i]}%")
        else:
            print(f"❌ Error: {result['error']}")
            
        print("\n" + "=" * 80)
