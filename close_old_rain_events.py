"""
Script para cerrar eventos de lluvia inactivos.
Puede ejecutarse manualmente o como tarea periódica (cada 10-15 min).
Verifica los últimos datos de lluvia reales de cada estación antes de cerrar.
"""
import os
import time
import sys
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def get_latest_rain_for_station(station_key, headers):
    """Obtener la última lectura de lluvia real de weather_readings para una estación"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/weather_readings"
        params = {
            'station_key': f'eq.{station_key}',
            'select': 'rain_mm,event_time',
            'order': 'event_time.desc',
            'limit': '2'
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200 and response.json():
            rows = response.json()
            latest_rain = float(rows[0]['rain_mm']) if rows[0].get('rain_mm') is not None else None
            prev_rain = float(rows[1]['rain_mm']) if len(rows) > 1 and rows[1].get('rain_mm') is not None else None
            latest_time = rows[0].get('event_time')
            return latest_rain, prev_rain, latest_time
    except Exception as e:
        print(f"   ⚠️  Error obteniendo lluvia actual: {e}")
    return None, None, None


def close_old_events(minutes_threshold=30):
    """Cerrar eventos que no han tenido incremento de lluvia en X minutos"""
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Variables de entorno no configuradas")
        return
    
    print(f"\n🔧 Verificando eventos de lluvia (umbral: {minutes_threshold} min sin incremento)...\n")
    
    url = f"{SUPABASE_URL}/rest/v1/rain_events"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Obtener eventos activos
    params = {"is_active": "eq.true"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"❌ Error obteniendo eventos: {response.status_code}")
        return
    
    active_events = response.json()
    print(f"📊 Eventos activos encontrados: {len(active_events)}\n")
    
    if not active_events:
        print("✅ No hay eventos activos para cerrar")
        return
    
    closed_count = 0
    for event in active_events:
        event_id = event['id']
        station_key = event['station_key']
        station_name = event['station_name']
        event_start = event['event_start']
        updated_at = event.get('updated_at', event['event_start'])
        rain_at_start = float(event.get('rain_at_start', 0) or 0)
        
        # Parsear timestamps
        start_time = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        now = datetime.now(start_time.tzinfo)
        
        minutes_since_update = (now - update_time).total_seconds() / 60
        total_duration = (now - start_time).total_seconds() / 60
        
        print(f"📍 Evento ID {event_id} - {station_name} ({station_key})")
        print(f"   Inicio: {event_start}")
        print(f"   Última actualización: hace {minutes_since_update:.1f} minutos")
        
        # Verificar datos reales de lluvia de la estación
        latest_rain, prev_rain, latest_time = get_latest_rain_for_station(station_key, headers)
        
        rain_still_active = False
        if latest_rain is not None and prev_rain is not None:
            increment = latest_rain - prev_rain
            print(f"   Lluvia actual: {latest_rain:.2f} mm (incremento reciente: {increment:.2f} mm)")
            if increment >= 0.1:
                rain_still_active = True
                print(f"   ⏳ Lluvia aún activa (incremento >= 0.1 mm)")
        
        # Cerrar si: no hay lluvia activa Y ha pasado el umbral de tiempo
        should_close = not rain_still_active and minutes_since_update >= minutes_threshold
        
        if should_close:
            rain_accumulated = round(latest_rain - rain_at_start, 2) if latest_rain is not None else event.get('rain_accumulated')
            event_end = updated_at  # El evento terminó cuando se actualizó por última vez
            duration = (update_time - start_time).total_seconds() / 60
            
            update_url = f"{url}?id=eq.{event_id}"
            update_data = {
                "is_active": False,
                "event_end": event_end,
                "rain_at_end": latest_rain,
                "rain_accumulated": rain_accumulated,
                "duration_minutes": int(duration),
                "updated_at": now.isoformat()
            }
            
            update_response = requests.patch(update_url, headers=headers, json=update_data)
            
            if update_response.status_code in [200, 204]:
                print(f"   ✅ Evento cerrado | Duración: {duration:.0f} min | Acumulado: {rain_accumulated} mm")
                closed_count += 1
            else:
                print(f"   ❌ Error cerrando: {update_response.status_code} - {update_response.text}")
        elif rain_still_active:
            print(f"   🌧️  Evento sigue activo (lluvia detectada)")
        else:
            remaining = minutes_threshold - minutes_since_update
            print(f"   ⏳ Esperando {remaining:.0f} min más sin lluvia para cerrar")
        
        print()
    
    print(f"\n{'='*70}")
    print(f"✅ Resultado: {closed_count}/{len(active_events)} evento(s) cerrado(s)")
    print(f"{'='*70}\n")


def run_periodic(interval_minutes=10, threshold=30):
    """Ejecutar verificación periódica de eventos"""
    print(f"\n{'='*70}")
    print(f"🔄 MONITOR PERIÓDICO DE EVENTOS DE LLUVIA")
    print(f"   Intervalo de chequeo: cada {interval_minutes} minutos")
    print(f"   Umbral de cierre: {threshold} minutos sin incremento")
    print(f"{'='*70}\n")
    
    while True:
        try:
            close_old_events(threshold)
        except Exception as e:
            print(f"❌ Error en ciclo: {e}")
        
        print(f"⏰ Próxima verificación en {interval_minutes} minutos...")
        time.sleep(interval_minutes * 60)

if __name__ == '__main__':
    # Uso: python close_old_rain_events.py [umbral_minutos] [--loop intervalo_minutos]
    # Ejemplo manual:    python close_old_rain_events.py 30
    # Ejemplo periódico: python close_old_rain_events.py 30 --loop 10
    
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != '--loop' else 30
    
    print("\n" + "="*70)
    print("🌧️  MONITOR DE EVENTOS DE LLUVIA")
    print("="*70)
    
    if '--loop' in sys.argv:
        loop_idx = sys.argv.index('--loop')
        interval = int(sys.argv[loop_idx + 1]) if loop_idx + 1 < len(sys.argv) else 10
        run_periodic(interval_minutes=interval, threshold=threshold)
    else:
        close_old_events(threshold)
