"""
Script para cerrar manualmente eventos de lluvia antiguos
Útil para limpiar eventos que quedaron abiertos
"""
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def close_old_events(minutes_threshold=30):
    """Cerrar eventos que no se han actualizado en X minutos"""
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Variables de entorno no configuradas")
        return
    
    print(f"\n🔧 Cerrando eventos inactivos (más de {minutes_threshold} minutos)...\n")
    
    # Obtener eventos activos
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
    
    # Procesar cada evento
    closed_count = 0
    for event in active_events:
        event_id = event['id']
        station_name = event['station_name']
        event_start = event['event_start']
        updated_at = event.get('updated_at', event['event_start'])
        
        # Calcular duración en minutos
        start_time = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
        update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        now = datetime.now(start_time.tzinfo)
        
        minutes_since_update = (now - update_time).total_seconds() / 60
        total_duration = (update_time - start_time).total_seconds() / 60
        
        print(f"📍 Evento ID {event_id} - {station_name}")
        print(f"   Inicio: {event_start}")
        print(f"   Última actualización: hace {minutes_since_update:.1f} minutos")
        print(f"   Duración total: {total_duration:.1f} minutos")
        
        if minutes_since_update >= minutes_threshold:
            # Cerrar evento
            update_url = f"{url}?id=eq.{event_id}"
            update_data = {
                "is_active": False,
                "event_end": updated_at,
                "duration_minutes": int(total_duration),
                "updated_at": now.isoformat()
            }
            
            update_response = requests.patch(update_url, headers=headers, json=update_data)
            
            if update_response.status_code in [200, 204]:
                print(f"   ✅ Evento cerrado correctamente")
                closed_count += 1
            else:
                print(f"   ❌ Error cerrando evento: {update_response.status_code}")
        else:
            print(f"   ⏳ Aún activo (menos de {minutes_threshold} min desde última actualización)")
        
        print()
    
    print(f"\n{'='*70}")
    print(f"✅ Proceso completado: {closed_count} evento(s) cerrado(s)")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    import sys
    
    # Permitir especificar el umbral desde la línea de comandos
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    
    print("\n" + "="*70)
    print("🌧️  CERRAR EVENTOS DE LLUVIA ANTIGUOS")
    print("="*70)
    
    close_old_events(threshold)
