import os
import sys
from datetime import datetime
from discord.ext import tasks

def iniciar_reinicio(bot):
    @tasks.loop(minutes=1)
    async def reiniciar_a_las_4am_rd():
        ahora = datetime.utcnow()
        if ahora.hour == 8 and ahora.minute == 0:  # Esto es 4:00 AM RD, que es 8:00 AM UTC
            print("🔁 Reiniciando bot automáticamente (4:00 AM RD / 8:00 AM UTC)")
            os.execv(sys.executable, [sys.executable] + sys.argv)  # Reemplaza el proceso

    reiniciar_a_las_4am_rd.start()
