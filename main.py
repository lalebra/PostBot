import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from caves import caves


load_dotenv()

CLIMA_CHANNEL_ID = int(os.getenv("CLIMA_CHANNEL_ID"))
RESPAWN_CHANNEL_ID = int(os.getenv("RESPAWN_CHANNEL_ID"))
OCUPADOS_CHANNEL_ID = int(os.getenv("OCUPADOS_CHANNEL_ID"))
COLA_CHANNEL_ID = int(os.getenv("COLA_CHANNEL_ID"))  # Nuevo canal de cola

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

cuevas_ocupadas = {}
colas_espera = {}
cooldowns = {}
tareas_embed = {}


def obtener_nombre_cueva(codigo):
    for cueva in caves:
        if cueva["id"] == codigo:
            return cueva["name"]
    return None

@bot.event
async def on_ready():
    print(f"🔥 Bot activo como un motor 2 tiempos: {bot.user}")
    await actualizar_embed_cola()

@bot.command()
async def claim(ctx, tipo: str, numero: int, duracion: str):
    await procesar_claim(ctx.author, tipo, numero, duracion, ctx)

async def procesar_claim(usuario, tipo: str, numero: int, duracion: str, ctx=None):
    clave = f"{tipo.upper()} {numero}"
    ahora = datetime.utcnow()
    autor_id = usuario.id

    # Obtén el nombre de la cueva correspondiente al código
    nombre_cueva = obtener_nombre_cueva(numero)
    if not nombre_cueva:
        if ctx:
            await ctx.send(f"❌ No se ha encontrado la cueva con el código {clave}.")
        return

    if clave in cuevas_ocupadas:
        if ctx:
            await ctx.send(f"❌ La cueva {clave} ya está ocupada.")
        return

    if clave in cooldowns and autor_id in cooldowns[clave]:
        if cooldowns[clave][autor_id] > ahora:
            restante = cooldowns[clave][autor_id] - ahora
            minutos = int(restante.total_seconds() // 60)
            if ctx:
                await ctx.send(f"⏳ Debes esperar {minutos} minutos para volver a postear la cueva {clave}.")
            return

    tiempo_segundos = convertir_duracion(duracion)
    if not tiempo_segundos or tiempo_segundos < 3600 or tiempo_segundos > 7200:
        if ctx:
            await ctx.send("⛔ La duración debe ser entre 1h y 2h (ej: `!claim B 1 2h`).")
        return

    tiempo_final = ahora + timedelta(seconds=tiempo_segundos)
    display_name = usuario.display_name

    embed_posteo = discord.Embed(title="✅ Cueva Reclamada", color=0x00ff00)
    embed_posteo.add_field(name="Cueva", value=nombre_cueva, inline=True)
    embed_posteo.add_field(name="Tiempo Restante", value=formatear_tiempo(tiempo_final), inline=True)
    embed_posteo.set_footer(text=f"Reclamado por {display_name}", icon_url=usuario.display_avatar.url)

    embed_ocupado = discord.Embed(title="🔵 Cueva Ocupada", color=0xff0000)
    embed_ocupado.add_field(name="Cueva", value=nombre_cueva, inline=True)
    embed_ocupado.add_field(name="Tiempo Restante", value=formatear_tiempo(tiempo_final), inline=True)
    embed_ocupado.set_footer(text=f"Posteado por {display_name}", icon_url=usuario.display_avatar.url)

    canal_respawn = bot.get_channel(RESPAWN_CHANNEL_ID)
    canal_ocupados = bot.get_channel(OCUPADOS_CHANNEL_ID)

    mensaje_posteo = await canal_respawn.send(embed=embed_posteo)
    mensaje_ocupado = await canal_ocupados.send(embed=embed_ocupado)

    cuevas_ocupadas[clave] = {
        "usuario": usuario,
        "tiempo_final": tiempo_final,
        "mensaje_posteo": mensaje_posteo,
        "mensaje_ocupado": mensaje_ocupado,
    }

    iniciar_tarea_embed(clave)
    await actualizar_embed_cola()

def iniciar_tarea_embed(clave):
    @tasks.loop(seconds=30)
    async def actualizar():
        data = cuevas_ocupadas.get(clave)
        if not data:
            actualizar.cancel()
            return

        tiempo_restante = data["tiempo_final"] - datetime.utcnow()
        if tiempo_restante.total_seconds() <= 0:
            await finalizar_cueva(clave)
            actualizar.cancel()
            return

        tiempo_formateado = formatear_tiempo(data["tiempo_final"])
        try:
            embed = data["mensaje_ocupado"].embeds[0]
            embed.set_field_at(1, name="Tiempo Restante", value=tiempo_formateado, inline=True)
            await data["mensaje_ocupado"].edit(embed=embed)
        except:
            pass

    tareas_embed[clave] = actualizar
    actualizar.start()

@bot.command()
async def cancel(ctx):
    autor = ctx.author
    clave = None
    for cueva, data in cuevas_ocupadas.items():
        if data["usuario"].id == autor.id:
            clave = cueva
            break

    if not clave:
        await ctx.send("❌ No tienes ninguna cueva posteada.")
        return

    await finalizar_cueva(clave, cancelador=ctx.author)

async def finalizar_cueva(clave, cancelador=None):
    data = cuevas_ocupadas.get(clave)
    if not data:
        return

    try:
        await data["mensaje_ocupado"].delete()
    except:
        pass

    usuario_anterior = data["usuario"]
    
    # Aplicar cooldown solo si es el mismo usuario que posteo
    if cancelador and cancelador.id == usuario_anterior.id:
        cooldowns.setdefault(clave, {})[usuario_anterior.id] = datetime.utcnow() + timedelta(minutes=15)

    del cuevas_ocupadas[clave]

    # Parar la tarea del embed
    if clave in tareas_embed:
        tareas_embed[clave].cancel()
        del tareas_embed[clave]

    if clave in colas_espera and colas_espera[clave]:
        siguiente, duracion = colas_espera[clave].pop(0)
        canal_temporal = await siguiente.create_dm()
        mensaje = await canal_temporal.send(f"📢 Te tocó postear en la cueva {clave} por {duracion}, posteando...")

        tipo, numero = clave.split()
        ctx_fake = await bot.get_context(mensaje)
        await procesar_claim(siguiente, tipo, int(numero), duracion, ctx_fake)

    await actualizar_embed_cola()

async def actualizar_embed_cola():
    cola_channel = bot.get_channel(COLA_CHANNEL_ID)
    
    embed_cola = discord.Embed(title="📜 Cola de Reclamaciones", color=0x00ffff)
    for clave, cola in colas_espera.items():
        nombre_cueva = obtener_nombre_cueva(clave.split()[1])
        lista_usuarios = "\n".join([f"{usuario.display_name} - {duracion}" for usuario, duracion in cola])
        embed_cola.add_field(name=f"Cueva {nombre_cueva}", value=lista_usuarios if lista_usuarios else "No hay usuarios en cola.", inline=False)

    # Si ya existe un embed, lo actualizamos; si no, lo creamos
    mensajes = await cola_channel.history(limit=1).flatten()
    if mensajes:
        await mensajes[0].edit(embed=embed_cola)
    else:
        await cola_channel.send(embed=embed_cola)

def formatear_tiempo(tiempo_final):
    restante = tiempo_final - datetime.utcnow()
    minutos, segundos = divmod(int(restante.total_seconds()), 60)
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h {minutos}m"

def convertir_duracion(duracion: str):
    try:
        if "h" in duracion:
            horas = int(duracion.replace("h", ""))
            return horas * 3600
        elif "m" in duracion:
            mins = int(duracion.replace("m", ""))
            return mins * 60
        else:
            return None
    except:
        return None

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
