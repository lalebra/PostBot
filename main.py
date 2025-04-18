from keep_alive import keep_alive
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

# Lista de cuevas con sus códigos y nombres correspondientes
caves = [
    {"id": 1, "name": "Lobos - Superfice 1 - Panuk"},
    {"id": 2, "name": "Lobos/Cave 1 - -1 - Panuk"},
    {"id": 3, "name": "Lobos/Cave 1 - -2 - Panuk"},
    {"id": 4, "name": "Lobos/Cave 1 - -3 - Panuk"},
    {"id": 5, "name": "Lobos/Cave 2 - -1 - Panuk"},
    {"id": 6, "name": "Lobos/Cave 2 - -2 - Panuk"},
    {"id": 7, "name": "Lobos/Cave 2 - -3 - Panuk"},
    {"id": 8, "name": "Lobos/Cave 3 - -1 - Panuk"},
    {"id": 9, "name": "Lobos/Cave 3 - -2 - Panuk"},
    {"id": 10, "name": "Lobos/Cave 3 - -3 - Panuk"},
    {"id": 11, "name": "Lobos/Cave 4 - -1 - Panuk"},
    {"id": 12, "name": "Lobos/Cave 4 - -2 - Panuk"},
    {"id": 13, "name": "Lobos/Cave 4 - -3 - Panuk"},
    {"id": 14, "name": "Dark Dragons - Direita - Panuk"},
    {"id": 15, "name": "Dark Dragons - Esquerda - Panuk"},
    {"id": 16, "name": "Dry Dragons - Direita - Panuk"},
    {"id": 17, "name": "Dry Dragons - Esquerda - Panuk"},
    {"id": 18, "name": "Tigres Superfice - Panuk"},
    {"id": 19, "name": "Tigres -2 - Panuk"},
    {"id": 20, "name": "Tigres -3 - Panuk"},
    {"id": 21, "name": "Grim Reapers - Caminho das Medusas - Panuk"},
    {"id": 22, "name": "Medusas - Direita - Panuk"},
    {"id": 23, "name": "Medusas - Esquerda - Panuk"},
    {"id": 24, "name": "Vampires - Direita - Panuk"},
    {"id": 25, "name": "Vampires - Esquerda - Panuk"},
    {"id": 26, "name": "Aboboras - Direita - Panuk"},
    {"id": 27, "name": "Aboboras - Esquerda - Panuk"},
    {"id": 28, "name": "Frost Hydras - Panuk"},
    {"id": 29, "name": "Turamak - Panuk"},
    {"id": 30, "name": "Lobos - Superfice 2 - Panuk"},
    {"id": 31, "name": "Lobos - Superfice 3 - Panuk"},
    {"id": 32, "name": "Lobos - Superfice 4 - Panuk"},
    {"id": 33, "name": "Dark Hydra Esquerda - Panuk"},
    {"id": 34, "name": "Dark Hydra Direita - Panuk"},
    {"id": 35, "name": "Banshee Direita - Panuk"},
    {"id": 36, "name": "Banshee Esquerda - Panuk"},
    {"id": 37, "name": "Ice Witch - Panuk"},
    {"id": 38, "name": "Abobora - Axel"},
    {"id": 39, "name": "Olhão - Axel"},
    {"id": 40, "name": "Witch - Axel"},
    {"id": 41, "name": "Earth Witch Esquerda - Axel"},
    {"id": 42, "name": "Earth Witch Direita - Axel"},
    {"id": 43, "name": "Vampire - Axel"},
    {"id": 44, "name": "Savage/Cave 150 - Axel"},
    {"id": 45, "name": "Medusa/Dark Hydra - Axel"},
    {"id": 46, "name": "Grim Reaper - Axel"},
    {"id": 47, "name": "Demon Estrela - Axel"},
    {"id": 48, "name": "Lobos Terreo - Tundra"},
    {"id": 49, "name": "Lobos -1 - Tundra"},
    {"id": 50, "name": "Lobos -2 - Tundra"},
    {"id": 51, "name": "Lobos -3 - Tundra"},
    {"id": 52, "name": "Demons - Tundra"},
    {"id": 53, "name": "Explores -1 - Tundra"},
    {"id": 54, "name": "Explores -2 - Tundra"},
    {"id": 55, "name": "Elf lord - Tundra"},
    {"id": 56, "name": "Cave 200 - Earth Witch Tundra"},
    {"id": 57, "name": "Cave 200 - Ice Witch"},
    {"id": 58, "name": "Cave 200 - Vicious spider"},
    {"id": 59, "name": "Cave 200 - Omothymus"},
    {"id": 60, "name": "Cave 200 - Orbweaver"},
    {"id": 61, "name": "Demons DP - Hellviwer"},
    {"id": 62, "name": "Muncher Sul - Hellviwer"},
    {"id": 63, "name": "Muncher Esquerda - Hellviwer"},
    {"id": 64, "name": "Muncher Norte Direita - Hellviwer"},
    {"id": 65, "name": "Livraria Fire - Hellviwer"},
    {"id": 66, "name": "Livraria Energy - Hellviwer"},
    {"id": 67, "name": "Livraria Death - Hellviwer"},
    {"id": 68, "name": "Livraria Ice - Hellviwer"},
    {"id": 69, "name": "Livraria Earth - Hellviwer"},
    {"id": 70, "name": "Slauter - Esquerda - Hellviwer"},
    {"id": 71, "name": "Slauter - Direita - Hellviwer"},
    {"id": 72, "name": "Behemoth - Hellviwer"},
    {"id": 73, "name": "Panther - Hellviwer"},
    {"id": 74, "name": "Rhinor - Hellviwer"},
    {"id": 75, "name": "Incerator - Hellviwer"},
    {"id": 76, "name": "The Judge Esquerda - Hellviwer"},
    {"id": 77, "name": "The Judge Direita - Hellviwer"},
    {"id": 78, "name": "Sand Djin - Hellviwer"},
    {"id": 79, "name": "Elf Lord - Umbra"},
    {"id": 80, "name": "Night Elf - Umbra"},
    {"id": 81, "name": "Medusa Terreo - Umbra"},
    {"id": 82, "name": "Medusa -1 - Umbra"},
    {"id": 83, "name": "Abobora - Umbra"},
    {"id": 84, "name": "Vampire - Umbra"},
    {"id": 85, "name": "Thunder Dragon - Umbra"},
    {"id": 86, "name": "Banshee - Terreo - Umbra"},
    {"id": 87, "name": "Banshee - -1 - Umbra"},
    {"id": 88, "name": "Dry Dragon - Umbra"},
    {"id": 89, "name": "Nomades Direita - Yakka"},
    {"id": 90, "name": "Nomades Esquerda - Yakka"},
    {"id": 91, "name": "Nomades Leader - Yakka"},
    {"id": 92, "name": "Giant Spider - Direita - Yakka"},
    {"id": 93, "name": "Vampire Aprentice/Ghost - Yakka"},
    {"id": 94, "name": "Dark Dragons - Yakka"},
    {"id": 95, "name": "Dragons/Dragons Lord - Yakka"},
    {"id": 96, "name": "Tumba Grim/Frost Hydras - Yakka"},
    {"id": 97, "name": "Giant Spider - Esquerda - Yakka"},
    {"id": 98, "name": "Thunder Dragon - Yakka"},
    {"id": 99, "name": "Banshee - Yakka"},
    {"id": 100, "name": "Frost Demon - Yakka"},
    {"id": 101, "name": "Vampire - Yakka"},
    {"id": 102, "name": "Tomb Guard - Yakka"}
  
    # Agregar el resto de las cuevas aquí
]

def obtener_nombre_cueva(codigo):
    for cueva in caves:
        if cueva["id"] == codigo:
            return cueva["name"]
    return None

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
    display_name = usuario.nick or usuario.name

    embed_posteo = discord.Embed(title="✅ Cueva Reclamada", color=0x00ff00)
    embed_posteo.add_field(name="Cueva", value=nombre_cueva, inline=True)  # Aquí usamos el nombre de la cueva
    embed_posteo.add_field(name="Tiempo Restante", value=formatear_tiempo(tiempo_final), inline=True)
    embed_posteo.set_footer(text=f"Reclamado por {display_name}", icon_url=usuario.display_avatar.url)

    embed_ocupado = discord.Embed(title="🔵 Cueva Ocupada", color=0xff0000)
    embed_ocupado.add_field(name="Cueva", value=nombre_cueva, inline=True)  # Aquí usamos el nombre de la cueva
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

@bot.command()
async def next(ctx, tipo: str, numero: int, duracion: str = "1h"):
    clave = f"{tipo.upper()} {numero}"
    usuario = ctx.author

    if clave in cuevas_ocupadas and cuevas_ocupadas[clave]["usuario"].id == usuario.id:
        await ctx.send("⚠️ No puedes hacer cola para una cueva que ya estás posteando.")
        return

    if clave not in colas_espera:
        colas_espera[clave] = []

    for persona, _ in colas_espera[clave]:
        if persona == usuario:
            await ctx.send("🔛 Ya estás en la cola para esa cueva.")
            return

    tiempo_segundos = convertir_duracion(duracion)
    if not tiempo_segundos or tiempo_segundos < 3600 or tiempo_segundos > 7200:
        await ctx.send("⛔ La duración debe ser entre 1h y 2h (ej: `!next B 1 2h`).")
        return

    colas_espera[clave].append((usuario, duracion))
    await ctx.send(f"📅 {usuario.mention} añadido a la cola para la cueva {clave} ({duracion}).")

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
