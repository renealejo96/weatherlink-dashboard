from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from weatherlink_client import WeatherLinkClient
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configurar las 3 estaciones
STATIONS = {
    'finca1': {
        'name': 'PYGANFLOR',
        'api_key': os.getenv('FINCA1_API_KEY'),
        'api_secret': os.getenv('FINCA1_API_SECRET'),
        'station_id': os.getenv('FINCA1_STATION_ID')
    },
    'finca2': {
        'name': 'Urcuquí',
        'api_key': os.getenv('FINCA2_API_KEY'),
        'api_secret': os.getenv('FINCA2_API_SECRET'),
        'station_id': os.getenv('FINCA2_STATION_ID')
    },
    'finca3': {
        'name': 'Malchinguí',
        'api_key': os.getenv('FINCA3_API_KEY'),
        'api_secret': os.getenv('FINCA3_API_SECRET'),
        'station_id': os.getenv('FINCA3_STATION_ID')
    }
}

# Crear clientes para cada estación
clients = {}
for key, station in STATIONS.items():
    clients[key] = WeatherLinkClient(
        station['api_key'],
        station['api_secret'],
        station['station_id']
    )

# Sistema de caché simple (TTL: 5 minutos)
CACHE = {}
CACHE_TTL = 300  # segundos

def get_cache_key(station_key, start_ts, end_ts):
    """Generar clave de caché"""
    return f"{station_key}_{start_ts}_{end_ts}"

def get_cached_data(cache_key):
    """Obtener datos del caché si aún son válidos"""
    if cache_key in CACHE:
        cached_time, cached_data = CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL:
            return cached_data
    return None

def set_cached_data(cache_key, data):
    """Guardar datos en el caché"""
    CACHE[cache_key] = (time.time(), data)


@app.route('/')
def index():
    """Página principal con dashboard de las 3 estaciones"""
    return render_template('index.html', stations=STATIONS)


@app.route('/api/current/<station_key>')
def get_current_data(station_key):
    """Obtener datos actuales de una estación"""
    if station_key not in clients:
        return jsonify({'error': 'Estación no encontrada'}), 404
    
    try:
        data = clients[station_key].get_current_conditions()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical/<station_key>')
def get_historical_data(station_key):
    """Obtener datos históricos de una estación"""
    if station_key not in clients:
        return jsonify({'error': 'Estación no encontrada'}), 404
    
    # Obtener parámetros de fecha
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    days = request.args.get('days', type=int, default=7)
    
    try:
        if start_date and end_date:
            # Usar fechas específicas
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86399  # Final del día
        else:
            # Usar últimos N días
            end_timestamp = int(datetime.now().timestamp())
            start_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
        
        # Verificar caché
        cache_key = get_cache_key(station_key, start_timestamp, end_timestamp)
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            cached_data['from_cache'] = True
            return jsonify(cached_data)
        
        # Si no hay en caché, obtener de la API
        data = clients[station_key].get_historic_data(start_timestamp, end_timestamp)
        data['from_cache'] = False
        
        # Guardar en caché
        set_cached_data(cache_key, data)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/station/<station_key>')
def station_detail(station_key):
    """Página de detalle de una estación con gráficos"""
    if station_key not in STATIONS:
        return "Estación no encontrada", 404
    
    return render_template('station_detail.html', 
                         station_key=station_key, 
                         station=STATIONS[station_key])


@app.route('/compare')
def compare_stations():
    """Página para comparar las 3 estaciones"""
    return render_template('compare.html', stations=STATIONS)


@app.route('/api/compare')
def get_compare_data():
    """Obtener datos de todas las estaciones para comparar"""
    days = request.args.get('days', type=int, default=7)
    
    end_timestamp = int(datetime.now().timestamp())
    start_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
    
    result = {}
    for key, client in clients.items():
        try:
            data = client.get_historic_data(start_timestamp, end_timestamp)
            result[key] = {
                'name': STATIONS[key]['name'],
                'data': data
            }
        except Exception as e:
            result[key] = {
                'name': STATIONS[key]['name'],
                'error': str(e)
            }
    
    return jsonify(result)


@app.route('/api/export/<station_key>')
def export_to_excel(station_key):
    """Exportar datos históricos a Excel"""
    if station_key not in clients:
        return jsonify({'error': 'Estación no encontrada'}), 404
    
    # Obtener parámetros de fecha
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    days = request.args.get('days', type=int, default=7)
    
    try:
        if start_date and end_date:
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86399
        else:
            end_timestamp = int(datetime.now().timestamp())
            start_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
        
        # Obtener datos
        data = clients[station_key].get_historic_data(start_timestamp, end_timestamp)
        records = data.get('records', [])
        
        # Crear archivo Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos Meteorológicos"
        
        # Estilo para encabezados
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        # Encabezados
        headers = ['Fecha y Hora', 'Temperatura (°C)', 'Humedad (%)', 'Viento (km/h)', 
                   'Lluvia (mm)', 'Radiación Solar (W/m²)', 'DPV (kPa)']
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Datos
        for row_idx, record in enumerate(records, 2):
            # Fecha
            ws.cell(row=row_idx, column=1, value=datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d %H:%M:%S'))
            
            # Temperatura (F -> C)
            temp_c = ((record.get('temperature', 0) - 32) * 5 / 9) if record.get('temperature') else None
            ws.cell(row=row_idx, column=2, value=round(temp_c, 2) if temp_c else '')
            
            # Humedad
            ws.cell(row=row_idx, column=3, value=record.get('humidity', ''))
            
            # Viento (mph -> km/h)
            wind_kmh = (record.get('wind_speed', 0) * 1.60934) if record.get('wind_speed') else None
            ws.cell(row=row_idx, column=4, value=round(wind_kmh, 2) if wind_kmh else '')
            
            # Lluvia en mm (el backend ya entrega mm)
            rain_mm = record.get('rain')
            ws.cell(row=row_idx, column=5, value=round(rain_mm, 2) if rain_mm else '')
            
            # Radiación Solar
            ws.cell(row=row_idx, column=6, value=record.get('solar_radiation', ''))
            
            # DPV (kPa)
            if record.get('temperature') and record.get('humidity'):
                tc = (record['temperature'] - 32) * 5 / 9
                vpsat = 0.6108 * (2.718281828 ** ((17.27 * tc) / (tc + 237.3)))
                vpactual = (record['humidity'] / 100) * vpsat
                dpv = vpsat - vpactual
                ws.cell(row=row_idx, column=7, value=round(dpv, 3))
            else:
                ws.cell(row=row_idx, column=7, value='')
        
        # Ajustar ancho de columnas
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column].width = adjusted_width
        
        # Guardar en memoria
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generar nombre de archivo
        filename = f"{STATIONS[station_key]['name']}_datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
