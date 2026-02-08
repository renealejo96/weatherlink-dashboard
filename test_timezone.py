#!/usr/bin/env python
"""Script de prueba para verificar zona horaria de Ecuador"""
from datetime import datetime
import pytz

# Zona horaria de Ecuador
ecuador_tz = pytz.timezone('America/Guayaquil')

# Timestamp de ejemplo (actual)
timestamp = 1707338487  # Ejemplo

# Convertir a Ecuador
utc_time = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)
ecuador_time = utc_time.astimezone(ecuador_tz)

print("=" * 50)
print("TEST DE ZONA HORARIA - ECUADOR")
print("=" * 50)
print(f"Timestamp: {timestamp}")
print(f"UTC: {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Ecuador: {ecuador_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Offset: UTC{ecuador_time.strftime('%z')}")
print("=" * 50)
print("✓ pytz instalado y funcionando correctamente")
