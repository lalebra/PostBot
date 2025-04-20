import os
import datetime
import time

def restart():
    print("Reiniciando el bot...")
    os.system("python main.py")

while True:
    now = datetime.datetime.utcnow()
    hora_rd = (now - datetime.timedelta(hours=4)).time()  # Ajusta a hora RD

    if hora_rd.hour == 4 and hora_rd.minute == 0:
        restart()
        time.sleep(60)  # Espera 1 minuto para no reiniciar más de una vez

    time.sleep(10)  # Chequea cada 10 segundos
