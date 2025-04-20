import discord
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
RESPAWN_CHANNEL_ID = int(os.getenv('RESPAWN_CHANNEL_ID'))
OCUPADOS_CHANNEL_ID = int(os.getenv('OCUPADOS_CHANNEL_ID'))

client = discord.Client()

@client.event
async def on_ready():
    respawn_channel = client.get_channel(RESPAWN_CHANNEL_ID)
    ocupados_channel = client.get_channel(OCUPADOS_CHANNEL_ID)
    
    # Borrar los últimos 100 mensajes en los canales
    await respawn_channel.purge(limit=100)
    await ocupados_channel.purge(limit=100)
    
    print("Mensajes borrados en los canales.")
    await client.close()

client.run(TOKEN)
