import time
import requests


class WeatherLinkClient:
    """Cliente para interactuar con la API de WeatherLink v2"""
    
    BASE_URL = "https://api.weatherlink.com/v2"
    
    def __init__(self, api_key, api_secret, station_id):
        self.api_key = api_key
        self.api_secret = api_secret
        self.station_id = station_id
    
    def _make_request(self, endpoint, params=None):
        """Hacer una petición autenticada a la API"""
        if params is None:
            params = {}
        
        # Agregar api-key a los parámetros
        params['api-key'] = self.api_key
        
        # El API Secret va como header, NO como parámetro
        headers = {
            'X-Api-Secret': self.api_secret
        }
        
        # Hacer petición
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error en API: {response.status_code} - {response.text}")
    
    def _calculate_vpd(self, temp_f, humidity):
        """Calcular DPV (Déficit de Presión de Vapor) en kPa"""
        if temp_f is None or humidity is None:
            return None
        
        # Convertir Fahrenheit a Celsius
        temp_c = (temp_f - 32) * 5 / 9
        
        # Calcular presión de vapor de saturación (VPsat) usando ecuación de Tetens
        vpsat = 0.6108 * (2.71828 ** ((17.27 * temp_c) / (temp_c + 237.3)))
        
        # Calcular presión de vapor actual (VPactual)
        vpactual = (humidity / 100) * vpsat
        
        # DPV = VPsat - VPactual
        vpd = vpsat - vpactual
        
        return round(vpd, 2)
    
    def get_current_conditions(self):
        """Obtener condiciones actuales de la estación"""
        endpoint = "current/" + self.station_id
        data = self._make_request(endpoint)
        
        # Buscar el sensor meteorológico principal (ISS)
        # Tipos de sensores comunes: 23 (ISS), 45, 53 (WeatherLink Live con ISS), 55 (WeatherLink Live), etc.
        weather_data = {}
        
        if 'sensors' in data:
            for sensor in data['sensors']:
                if 'data' in sensor and len(sensor['data']) > 0:
                    sensor_data = sensor['data'][0]
                    sensor_type = sensor.get('sensor_type')
                    
                    # Consolidar datos de múltiples sensores
                    # Sensor meteorológico exterior (temp, hum, viento, lluvia)
                    if sensor_type in [23, 45, 53, 55]:
                        # Manejar diferentes formatos de nombres de campos
                        temp = sensor_data.get('temp') or sensor_data.get('temp_out')
                        hum = sensor_data.get('hum') or sensor_data.get('hum_out')
                        
                        # Para lluvia, priorizar lluvia diaria acumulada
                        rain = (sensor_data.get('rainfall_daily_mm') or 
                               sensor_data.get('rainfall_daily_in') or
                               sensor_data.get('rain_rate_last') or 
                               sensor_data.get('rainfall_last_15_min') or
                               sensor_data.get('rain_rate_in') or
                               sensor_data.get('rain_day_mm') or
                               sensor_data.get('rain_day_in'))
                        
                        weather_data.update({
                            'timestamp': sensor_data.get('ts'),
                            'temperature': temp,
                            'humidity': hum,
                            'wind_speed': (sensor_data.get('wind_speed_last') or 
                                         sensor_data.get('wind_speed_avg_last_10_min') or
                                         sensor_data.get('wind_speed') or
                                         sensor_data.get('wind_speed_10_min')),
                            'wind_dir': sensor_data.get('wind_dir_last') or sensor_data.get('wind_dir'),
                            'rain_rate': rain,
                            'solar_radiation': sensor_data.get('solar_rad'),
                            'uv_index': sensor_data.get('uv_index') or sensor_data.get('uv'),
                            'dew_point': sensor_data.get('dew_point'),
                            'heat_index': sensor_data.get('heat_index'),
                            'wind_chill': sensor_data.get('wind_chill'),
                        })
                        
                        # Calcular DPV si tenemos temp y humedad
                        if temp and hum:
                            weather_data['vpd'] = self._calculate_vpd(temp, hum)
                    
                    # Sensor de presión barométrica
                    if sensor_type in [242, 243]:
                        weather_data.update({
                            'pressure': sensor_data.get('bar_sea_level'),
                            'pressure_trend': sensor_data.get('bar_trend')
                        })
                    
                    # Si no hay timestamp aún, usar este
                    if 'timestamp' not in weather_data:
                        weather_data['timestamp'] = sensor_data.get('ts')
        
        # Si no se encontraron datos, devolver la respuesta completa
        if not weather_data:
            return {'raw_data': data, 'timestamp': None}
        
        return weather_data
    
    def get_historic_data(self, start_timestamp, end_timestamp):
        """Obtener datos históricos de la estación
        
        La API de WeatherLink limita a 24 horas (86400 segundos) por petición.
        Este método divide automáticamente en múltiples peticiones si es necesario.
        """
        MAX_RANGE = 86400  # 24 horas en segundos
        all_records = []
        
        # Dividir el rango en chunks de 24 horas
        current_start = start_timestamp
        
        while current_start < end_timestamp:
            current_end = min(current_start + MAX_RANGE, end_timestamp)
            
            endpoint = "historic/" + self.station_id
            params = {
                'start-timestamp': current_start,
                'end-timestamp': current_end
            }
            
            try:
                data = self._make_request(endpoint, params)
                
                # Procesar datos históricos de este chunk
                if 'sensors' in data:
                    for sensor in data['sensors']:
                        sensor_type = sensor.get('sensor_type')
                        
                        # Solo procesar sensores meteorológicos principales (incluyendo tipo 53)
                        if sensor_type in [23, 45, 53, 55] and 'data' in sensor:
                            for record in sensor['data']:
                                # Manejar múltiples formatos de nombres de campos
                                # Datos históricos usan: temp_last, hum_last, wind_speed_avg, solar_rad_avg
                                # Datos actuales usan: temp/temp_out, hum/hum_out, wind_speed_last
                                temp = (record.get('temp') or 
                                       record.get('temp_out') or 
                                       record.get('temp_last'))
                                
                                hum = (record.get('hum') or 
                                      record.get('hum_out') or 
                                      record.get('hum_last'))
                                
                                wind = (record.get('wind_speed_last') or 
                                       record.get('wind_speed_avg_last_10_min') or
                                       record.get('wind_speed') or
                                       record.get('wind_speed_10_min') or
                                       record.get('wind_speed_avg'))
                                
                                rain = (record.get('rain_rate_last', 0) or 
                                       record.get('rainfall_last_15_min', 0) or
                                       record.get('rain_rate_in', 0) or
                                       record.get('rainfall_in', 0) or
                                       record.get('rainfall_mm', 0))
                                
                                solar = (record.get('solar_rad') or
                                        record.get('solar_rad_avg'))
                                
                                all_records.append({
                                    'timestamp': record.get('ts'),
                                    'temperature': temp,
                                    'humidity': hum,
                                    'wind_speed': wind,
                                    'wind_dir': record.get('wind_dir_last') or record.get('wind_dir'),
                                    'rain': rain,
                                    'solar_radiation': solar,
                                    'uv_index': record.get('uv_index') or record.get('uv'),
                                    'dew_point': record.get('dew_point') or record.get('dew_point_last'),
                                })
                            break  # Solo usar el primer sensor meteorológico
            except Exception as e:
                # Si hay error en un chunk, continuar con el siguiente
                print(f"Error obteniendo datos de {current_start} a {current_end}: {str(e)}")
            
            # Mover al siguiente chunk
            current_start = current_end
        
        return {
            'station_id': self.station_id,
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'records': all_records
        }
    
    def get_station_metadata(self):
        """Obtener información/metadatos de la estación"""
        endpoint = "stations/" + self.station_id
        return self._make_request(endpoint)
