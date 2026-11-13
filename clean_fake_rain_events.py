"""
Script de Limpieza de Eventos de Lluvia Fantasma (0.0 mm) en Supabase
Elimina registros huérfanos o falsos positivos con acumulado menor a 0.20 mm.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def purge_fake_events():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Variables SUPABASE_URL o SUPABASE_KEY no configuradas en .env")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    print("\n🧹 Iniciando purga de eventos fantasma en Supabase (rain_accumulated < 0.20 mm)...")

    # 1. Eventos inactivos con lluvia menor a 0.2 mm o 0.0 mm
    url = f"{SUPABASE_URL}/rest/v1/rain_events?is_active=eq.false&or=(rain_accumulated.lt.0.2,rain_accumulated.is.null)"
    
    # Primero contar
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Error consultando eventos: {resp.status_code} - {resp.text}")
        return

    fake_events = resp.json()
    count = len(fake_events)
    print(f"📊 Registros fantasma encontrados: {count}")

    if count == 0:
        print("✅ No hay registros fantasma para eliminar.")
        return

    # Eliminar
    del_resp = requests.delete(url, headers=headers)
    if del_resp.status_code in [200, 204]:
        print(f"✅ ¡Purga completada exitosamente! Se eliminaron {count} eventos falsos.")
    else:
        print(f"❌ Error al eliminar: {del_resp.status_code} - {del_resp.text}")

if __name__ == '__main__':
    purge_fake_events()
