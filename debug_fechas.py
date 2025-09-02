import pandas as pd
from datetime import datetime
import pytz

# Script de debug para revisar fechas
def debug_fechas():
    print("=== DEBUG DE FECHAS ===")
    print(f"Fecha actual del sistema: {datetime.now()}")
    print(f"Fecha actual UTC: {datetime.now(pytz.UTC)}")
    print(f"Fecha actual México: {datetime.now(pytz.timezone('America/Mexico_City'))}")
    
    # Simular algunos timestamps Unix que podrían venir de la API
    sample_timestamps = [
        1725235200,  # Ejemplo 1
        1725667200,  # Ejemplo 2
        1725753600,  # Ejemplo 3
    ]
    
    print("\n=== CONVERSIÓN DE TIMESTAMPS ===")
    for ts in sample_timestamps:
        dt_utc = pd.to_datetime(ts, unit='s', utc=True)
        dt_mexico = dt_utc.tz_convert('America/Mexico_City')
        print(f"Timestamp {ts}:")
        print(f"  UTC: {dt_utc}")
        print(f"  México: {dt_mexico}")
        print(f"  Fecha México: {dt_mexico.strftime('%d/%m/%Y')}")
        print()

if __name__ == "__main__":
    debug_fechas()
