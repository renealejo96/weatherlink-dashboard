"""
Script para actualizar la función SQL en Supabase
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# SQL para actualizar la función
sql_query = """
CREATE OR REPLACE FUNCTION close_inactive_rain_events()
RETURNS void AS $$
BEGIN
    -- Cerrar eventos que no han tenido actualización en 30 minutos
    UPDATE rain_events
    SET is_active = false,
        event_end = updated_at,
        duration_minutes = EXTRACT(EPOCH FROM (updated_at - event_start))/60
    WHERE is_active = true
      AND updated_at < NOW() - INTERVAL '30 minutes';
END;
$$ LANGUAGE plpgsql;
"""

if __name__ == '__main__':
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Variables de entorno SUPABASE_URL y SUPABASE_KEY no configuradas")
        exit(1)
    
    print("🔄 Actualizando función SQL en Supabase...")
    print(f"📍 URL: {SUPABASE_URL}")
    
    # Ejecutar SQL usando la API de Supabase
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Nota: Supabase no permite ejecutar SQL arbitrario por REST API
    # La mejor opción es ejecutarlo en el dashboard de Supabase SQL Editor
    
    print("\n⚠️  IMPORTANTE:")
    print("=" * 70)
    print("La función SQL debe ejecutarse manualmente en Supabase SQL Editor:")
    print()
    print("1. Ve a: https://supabase.com/dashboard")
    print("2. Selecciona tu proyecto")
    print("3. Ve a SQL Editor")
    print("4. Ejecuta el siguiente SQL:")
    print("=" * 70)
    print(sql_query)
    print("=" * 70)
    print()
    print("O puedes ejecutar todo el archivo sql/rain_events_table.sql")
    print()
    
    # Intentar verificar si la tabla existe
    try:
        verify_url = f"{SUPABASE_URL}/rest/v1/rain_events?limit=1"
        verify_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.get(verify_url, headers=verify_headers)
        
        if response.status_code == 200:
            print("✅ Conexión a Supabase OK - tabla rain_events accesible")
            print(f"   Registros en tabla: se puede consultar")
        else:
            print(f"⚠️  Respuesta de Supabase: {response.status_code}")
    except Exception as e:
        print(f"❌ Error verificando conexión: {e}")
