import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CLIMA_CHANNEL_ID = int(os.getenv("CLIMA_CHANNEL_ID"))

ultimo_mensaje_global = None
cooldown_global = timedelta(seconds=30)
espera_entre_borrados = 1  # segundos

async def manejar_mensaje_global(message):
    global ultimo_mensaje_global

    if message.channel.id != CLIMA_CHANNEL_ID or message.author.bot:
        return False  # Ignorar mensajes irrelevantes

    ahora = datetime.utcnow()

    if ultimo_mensaje_global is None or ahora - ultimo_mensaje_global >= cooldown_global:
        ultimo_mensaje_global = ahora
        return False  # Permitido, no borrar
    else:
        try:
            await asyncio.sleep(espera_entre_borrados)  # Espera para evitar 429
            await message.delete()
            return True  # Se borró con delay
        except Exception as e:
            print(f"Error al borrar mensaje: {e}")
            return True  # Aunque falle, lo intentó
