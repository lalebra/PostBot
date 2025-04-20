from keep_alive import keep_alive
keep_alive()

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

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

cuevas_ocupadas = {}
colas_espera = {}
cooldowns = {}
tareas_embed = {}

def obtener_nombre_cueva(numero):
    for cueva in caves:
        if cueva["id"] == numero:
            return cueva["name"]
    return None

def convertir_duracion(duracion: str):
    try:
        if duracion.endswith("h"):
            return int(duracion[:-1]) * 3600
        if duracion.endswith("m"):
            return int(duracion[:-1]) * 60
    except:
        return None

def formatear_tiempo(futuro):
    restante = futuro - datetime.utcnow()
    minutos, segundos = divmod(int(restante.total_seconds()), 60)
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h {minutos}m"

def tiene_posteo_activo(usuario):
    return any(data["usuario"].id == usuario.id for data in cuevas_ocupadas.values())

def esta_en_una_cola(usuario):
    for cola in colas_espera.values():
        for persona, _ in cola:
            if persona.id == usuario.id:
                return True
    return False

@bot.event
async def on_ready():
    print(f"🔥 Bot activo como un motor 2 tiempos: {bot.user}")

@bot.command()
async def claim(ctx, tipo: str, numero: int, duracion: str):
    await procesar_claim(ctx.author, tipo, numero, duracion, ctx)

async def procesar_claim(usuario, tipo: str, numero: int, duracion: str, ctx=None):
    clave = f"{tipo.upper()} {numero}"
    ahora = datetime.utcnow()
    autor_id = usuario.id

    nombre_cueva = obtener_nombre_cueva(numero)
    if not nombre_cueva:
        if ctx:
            await ctx.send(f"❌ No se ha encontrado la cueva con el código {clave}.")
        return

    if clave in cuevas_ocupadas:
        if ctx:
            await ctx.send(f"❌ La cueva {clave} ya está ocupada.")
        return

    if tiene_posteo_activo(usuario):
        if ctx:
            await ctx.send("⚠️ Ya tienes un posteo activo.")
        return

    if esta_en_una_cola(usuario):
        if ctx:
            await ctx.send("🚫 No puedes postear mientras estás en una cola.")
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
        "duracion": duracion,
    }

    iniciar_tarea_embed(clave)

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

    await finalizar_cueva(clave, cancelador=autor)

async def finalizar_cueva(clave, cancelador=None):
    data = cuevas_ocupadas.get(clave)
    if not data:
        return

    usuario = data["usuario"]
    canal_ocupados = bot.get_channel(OCUPADOS_CHANNEL_ID)

    # cooldown
    cooldowns.setdefault(clave, {})[usuario.id] = datetime.utcnow() + timedelta(minutes=15)

    try:
        await data["mensaje_ocupado"].delete()
    except:
        pass

    try:
        await data["mensaje_posteo"].edit(embed=discord.Embed(title="❌ Cueva Liberada", description=f"{usuario.display_name} ha liberado la cueva.", color=0xaaaaaa))
    except:
        pass

    tareas_embed.get(clave, lambda: None)().cancel()
    tareas_embed.pop(clave, None)
    cuevas_ocupadas.pop(clave, None)

    # Ver si hay cola
    if clave in colas_espera and colas_espera[clave]:
        siguiente, duracion = colas_espera[clave].pop(0)
        await procesar_claim(siguiente, *clave.split(), duracion)

@bot.command()
async def next(ctx, tipo: str, numero: int, duracion: str = "1h"):
    clave = f"{tipo.upper()} {numero}"
    usuario = ctx.author

    if clave not in cuevas_ocupadas:
        await ctx.send("⚠️ Esa cueva no está activa. Usa `!claim` para postearla primero.")
        return

    if cuevas_ocupadas[clave]["usuario"].id == usuario.id:
        await ctx.send("⚠️ No puedes hacer cola para una cueva que ya estás posteando.")
        return

    if esta_en_una_cola(usuario):
        for c, cola in colas_espera.items():
            for persona, _ in cola:
                if persona.id == usuario.id:
                    await ctx.send(f"🚫 Ya estás en la cola para la cueva {c}.")
                    return

    tiempo_segundos = convertir_duracion(duracion)
    if not tiempo_segundos or tiempo_segundos < 3600 or tiempo_segundos > 7200:
        await ctx.send("⛔ La duración debe ser entre 1h y 2h (ej: `!next B 1 2h`).")
        return

    colas_espera.setdefault(clave, []).append((usuario, duracion))
    await ctx.send(f"🗓️ {usuario.mention} añadido a la cola para la cueva {clave} ({duracion}).")

@bot.command()
async def salircola(ctx):
    usuario = ctx.author
    for clave in list(colas_espera.keys()):
        nueva_cola = [(p, t) for p, t in colas_espera[clave] if p.id != usuario.id]
        if len(nueva_cola) < len(colas_espera[clave]):
            colas_espera[clave] = nueva_cola
            await ctx.send(f"👋 Saliste de la cola de la cueva {clave}.")
            return
    await ctx.send("❌ No estás en ninguna cola.")

bot.run(os.getenv("DISCORD_TOKEN"))
