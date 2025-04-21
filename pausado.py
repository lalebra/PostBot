import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CLIMA_CHANNEL_ID = int(os.getenv("CLIMA_CHANNEL_ID"))

ultimo_mensaje_global = None
cooldown_global = timedelta(seconds=30)

async def manejar_mensaje_global(message):
    global ultimo_mensaje_global

    if message.channel.id != CLIMA_CHANNEL_ID or message.author.bot:
        return False  # Nada que borrar

    ahora = datetime.utcnow()

    if ultimo_mensaje_global is None or ahora - ultimo_mensaje_global >= cooldown_global:
        ultimo_mensaje_global = ahora
        return False  # Dejar pasar
    else:
        try:
            await message.delete()
            return True  # Fue borrado
        except:
            return True  # Intentó borrarlo igual
