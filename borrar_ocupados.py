import discord
import os
from discord.ext import commands

# Obtener variables de entorno desde GitHub Secrets
TOKEN = os.getenv('DISCORD_TOKEN')
OCUPADOS_CHANNEL_ID = int(os.getenv("OCUPADOS_CHANNEL_ID"))

# Crear el bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    canal_ocupados = bot.get_channel(OCUPADOS_CHANNEL_ID)

    if canal_ocupados:
        count = 0
        async for mensaje in canal_ocupados.history(limit=100):
            if mensaje.embeds and mensaje.embeds[0].title == "🔵 Cueva Ocupada":
                try:
                    await mensaje.delete()
                    print(f"🧹 Eliminado mensaje: {mensaje.id}")
                    count += 1
                except Exception as e:
                    print(f"⚠️ Error al eliminar {mensaje.id}: {e}")
        print(f"🧾 Total de mensajes eliminados: {count}")
    else:
        print("❌ Canal de ocupados no encontrado")

    await bot.close()

# Ejecutar bot
bot.run(TOKEN)
