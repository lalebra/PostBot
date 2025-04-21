from discord.ext import tasks
from datetime import datetime
import os
import sys

def iniciar_reinicio(bot):
    @tasks.loop(minutes=1)
    async def reiniciar_a_las_8utc():
        ahora = datetime.utcnow()
        if ahora.hour == 8 and ahora.minute == 0:
            print("🔁 Reiniciando bot automáticamente (4:00 AM RD / 8:00 AM UTC)")
            await bot.close()
            os.execv(sys.executable, ['python'] + sys.argv)

    reiniciar_a_las_8utc.start()
