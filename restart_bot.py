import os
import time
from datetime import datetime
import subprocess

# Función para calcular la hora actual en la República Dominicana (UTC-4)
def hora_local():
    return datetime.utcnow().replace(tzinfo=None) - timedelta(hours=4)

# Configuración para reiniciar el bot a las 4:00 AM (hora de RD)
while True:
    # Obtener la hora actual
    ahora = hora_local()
    
    # Comprobar si es las 4:00 AM
    if ahora.hour == 4 and ahora.minute == 0:
        print("Es hora de reiniciar el bot...")

        # Reiniciar el bot usando subprocess para llamar a render o el comando adecuado
        subprocess.run(["render", "restart", "<nombre_del_servicio_en_render>"])

        # Esperar un minuto para evitar que reinicie varias veces
        time.sleep(60)
    else:
        # Dormir por 60 segundos para revisar la hora de nuevo
        time.sleep(60)
