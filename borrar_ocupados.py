import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

# Cargar las variables de entorno
load_dotenv()

# Usar el token de tu bot
TOKEN = os.getenv('DISCORD_TOKEN')

# IDs de los canales donde están los embeds
OCUPADOS_CHANNEL_ID = int(os.getenv("OCUPADOS_CHANNEL_ID"))

# Crear el bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # Obtener el canal de ocupados
    canal_ocupados = bot.get_channel(OCUPADOS_CHANNEL_ID)

    if canal_ocupados:
        async for mensaje in canal_ocupados.history(limit=100):
            # Buscar los mensajes que tengan embeds de "Cueva Ocupada"
            if mensaje.embeds and mensaje.embeds[0].title == "🔵 Cueva Ocupada":
                try:
                    # Eliminar los mensajes
                    await mensaje.delete()
                    print(f"Mensaje de ocupada eliminado: {mensaje.id}")
                except Exception as e:
                    print(f"Error al eliminar mensaje {mensaje.id}: {e}")

    # Desconectar el bot después de limpiar los embeds
    await bot.close()

# Iniciar el bot usando el token cargado desde el .env
bot.run(os.getenv("DISCORD_TOKEN"))
