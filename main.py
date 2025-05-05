from keep_alive import keep_alive
keep_alive()

import time
import random
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from caves import caves
from pausado import manejar_mensaje_global
import asyncio



load_dotenv()

CLIMA_CHANNEL_ID = int(os.getenv("CLIMA_CHANNEL_ID"))
RESPAWN_CHANNEL_ID = int(os.getenv("RESPAWN_CHANNEL_ID"))
OCUPADOS_CHANNEL_ID = int(os.getenv("OCUPADOS_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

rate_limit_semaphore = asyncio.Semaphore(5)  # Solo 5 acciones a la vez

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
            return int(duracion[:-1]) * 3600  # Convertir horas a segundos
        if duracion.endswith("m"):
            return int(duracion[:-1]) * 60  # Convertir minutos a segundos
    except ValueError:
        return None  # Si no se puede convertir la duración, retorna None

def formatear_tiempo(futuro):
    restante = futuro - datetime.utcnow()
    minutos, segundos = divmod(int(restante.total_seconds()), 60)
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h {minutos}m"

def tiene_posteo_activo(usuario):
    # Verifica si el usuario tiene un posteo activo que no ha expirado
    for data in cuevas_ocupadas.values():
        if data["usuario"].id == usuario.id:
            if data["tiempo_final"] > datetime.utcnow():  # Asegura que el posteo no haya expirado
                return True
            else:
                # Si el posteo ya expiró, elimina la cueva de las ocupadas
                clave = next((k for k, v in cuevas_ocupadas.items() if v["usuario"].id == usuario.id), None)
                if clave:
                    del cuevas_ocupadas[clave]
                return False
    return False

def esta_en_una_cola(usuario):
    for cola in colas_espera.values():
        for persona, _ in cola:
            if persona.id == usuario.id:
                return True
    return False


@bot.command()
@commands.cooldown(rate=1, per=3.0, type=commands.BucketType.user)
async def claim(ctx, tipo: str, numero: int, duracion: str):
    # Verificar si el usuario está en cola
    if esta_en_una_cola(ctx.author):
        await ctx.send("⚠️ No puedes reclamar una cueva mientras estás en una cola.")
        return
    
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
            await ctx.send(f"❌ La cueva {nombre_cueva} ya está ocupada.")  # Mostrar el nombre de la cueva
        return

    if tiene_posteo_activo(usuario):
        if ctx:
            await ctx.send("⚠️ Ya tienes un posteo activo.")
        return

    if clave in cooldowns and autor_id in cooldowns[clave]:
        if cooldowns[clave][autor_id] > ahora:
            restante = cooldowns[clave][autor_id] - ahora
            minutos = int(restante.total_seconds() // 60)
            if ctx:
                await ctx.send(f"⏳ Debes esperar {minutos} minutos para volver a postear la cueva {nombre_cueva}.")  # Mostrar el nombre de la cueva
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

    async with rate_limit_semaphore:
        mensaje_posteo = await canal_respawn.send(embed=embed_posteo)
    await asyncio.sleep(random.uniform(1.5, 3.0))  # le das un respiro a Discord
    async with rate_limit_semaphore:
        mensaje_ocupado = await canal_ocupados.send(embed=embed_ocupado)



    cuevas_ocupadas[clave] = {
        "usuario": usuario,
        "tiempo_final": tiempo_final,
        "mensaje_posteo": mensaje_posteo,
        "mensaje_ocupado": mensaje_ocupado,
    }

    iniciar_tarea_embed(clave)



def iniciar_tarea_embed(clave):
    if clave in tareas_embed:
        return  # Ya hay una tarea corriendo

    @tasks.loop(seconds=300)
    async def actualizar():
        data = cuevas_ocupadas.get(clave)
        if not data.get("mensaje_ocupado"):
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
            campo_actual = embed.fields[1].value

            # Solo edita si el texto cambió
            if campo_actual != tiempo_formateado:
                embed.set_field_at(1, name="Tiempo Restante", value=tiempo_formateado, inline=True)
                async with rate_limit_semaphore:
                    await data["mensaje_ocupado"].edit(embed=embed)


        except discord.NotFound:
            print(f"[❌] El mensaje de la cueva {clave} fue eliminado.")
            actualizar.cancel()
        except discord.HTTPException as e:
            print(f"[⚠️] Error al editar el embed de {clave}: {e}")
        except Exception as e:
            print(f"[🔥] Error inesperado en la tarea de {clave}: {e}")

    tareas_embed[clave] = actualizar

    # Inicia con delay aleatorio para que no todos editen al mismo tiempo
    async def start_con_delay():
        await asyncio.sleep(random.randint(1, 30))
        actualizar.start()

    bot.loop.create_task(start_con_delay())


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
    
@bot.command()
async def next(ctx, tipo: str, numero: int, duracion: str = "1h"):
    clave = f"{tipo.upper()} {numero}"
    usuario = ctx.author

    # Verificar si la cueva está activa
    if clave not in cuevas_ocupadas:
        await ctx.send("⚠️ Esa cueva no está activa. Usa `!claim` para postearla primero.")
        return

    # Verificar si el usuario ya está posteando esta cueva
    if cuevas_ocupadas[clave]["usuario"].id == usuario.id:
        await ctx.send("⚠️ No puedes hacer cola para una cueva que ya estás posteando.")
        return

    # Verificar si el usuario ya tiene un posteo activo en alguna otra cueva
    if tiene_posteo_activo(usuario):
        await ctx.send("⚠️ No puedes hacer cola mientras tienes un posteo activo en otra cueva.")
        return

    # Verificar si el usuario ya está en una cola
    if esta_en_una_cola(usuario):
        for c, cola in colas_espera.items():
            for persona, _ in cola:
                if persona.id == usuario.id:
                    await ctx.send(f"🚫 Ya estás en la cola para la cueva {c}.")
                    return

    # Verificar si la duración es válida
    tiempo_segundos = convertir_duracion(duracion)
    if not tiempo_segundos or tiempo_segundos < 3600 or tiempo_segundos > 7200:
        await ctx.send("⛔ La duración debe ser entre 1h y 2h (ej: `!next B 1 2h`).")
        return

    # Añadir al usuario a la cola
    colas_espera.setdefault(clave, []).append((usuario, duracion))
    await ctx.send(f"🗓️ {usuario.mention} añadido a la cola para la cueva {clave} ({duracion}).")


@bot.command()
async def salircola(ctx):
    usuario = ctx.author
    for clave in list(colas_espera.keys()):
        nueva_cola = [(p, t) for p, t in colas_espera[clave] if p.id != usuario.id]
        if len(nueva_cola) < len(colas_espera[clave]):
            colas_espera[clave] = nueva_cola
            await ctx.send(f"✅ {usuario.mention} ha salido de la cola para la cueva {clave}.")
            return
    await ctx.send("❌ No estás en ninguna cola.")

async def finalizar_cueva(clave, cancelador=None):
    data = cuevas_ocupadas.get(clave)
    if not data:
        print(f"[FINALIZAR] No hay datos para la clave: {clave}")
        return

    try:
        await data["mensaje_ocupado"].delete()
    except Exception as e:
        print(f"[ERROR] No se pudo borrar el mensaje ocupado: {e}")

    usuario_anterior = data["usuario"]

    try:
        nombre_cueva = obtener_nombre_cueva(int(clave.split()[1]))
    except Exception as e:
        print(f"[ERROR] No se pudo obtener el nombre de la cueva: {e}")
        nombre_cueva = "desconocida"

    if not cancelador or cancelador.id == usuario_anterior.id:
        cooldowns.setdefault(clave, {})[usuario_anterior.id] = datetime.utcnow() + timedelta(minutes=15)

    del cuevas_ocupadas[clave]

    if clave in tareas_embed:
        tareas_embed[clave].cancel()
        del tareas_embed[clave]

    try:
        canal_privado = await usuario_anterior.create_dm()
        if cancelador:
            await canal_privado.send(f"❌ Has cancelado tu posteo en la cueva {nombre_cueva}.")
        else:
            await canal_privado.send(f"⏰ Se terminó tu tiempo en la cueva {nombre_cueva}.")
    except Exception as e:
        print(f"[ERROR] No se pudo enviar DM a {usuario_anterior.display_name}: {e}")

    if clave in colas_espera and colas_espera[clave]:
        siguiente, duracion = colas_espera[clave].pop(0)

        try:
            canal_temporal = await siguiente.create_dm()
            await canal_temporal.send(f"📢 Te tocó postear en la cueva {nombre_cueva} por {duracion}, posteando...")
        except Exception as e:
            print(f"[ERROR] No se pudo enviar DM a {siguiente.display_name}: {e}")

        try:
            tipo, numero = clave.split()
            await procesar_claim(siguiente, tipo, int(numero), duracion)
        except Exception as e:
            print(f"[ERROR] Falló el claim automático para {siguiente.display_name}: {e}")

        if not colas_espera[clave]:
            del colas_espera[clave]


@bot.command()
@commands.is_owner()
async def reiniciar(ctx):
    await ctx.send("🔄 Reiniciando bot, espera un chin...")
    os._exit(0)

@bot.command()
async def estado(ctx):
    if not cuevas_ocupadas:
        await ctx.send("📭 No hay cuevas activas ahora mismo.")
        return

    embed = discord.Embed(title="📊 Cuevas Activas", color=0x00ffcc)
    for clave, data in cuevas_ocupadas.items():
        numero = int(clave.split()[1])  # 🔥 Saca el número de la clave
        nombre_cueva = obtener_nombre_cueva(numero)  # 🔥 Solo pasa el número
        tiempo = formatear_tiempo(data["tiempo_final"])
        embed.add_field(
            name=nombre_cueva,
            value=f"👤 {data['usuario'].display_name}\n⏳ {tiempo}",
            inline=False
        )
    await ctx.send(embed=embed)




@bot.event
async def on_ready():
    print(f"🔥 Bot activo como un motor 2 tiempos: {bot.user}")
    iniciar_reinicio(bot)

    print("Limpiando canales de cueva...")

    respawn_channel = bot.get_channel(RESPAWN_CHANNEL_ID)
    ocupados_channel = bot.get_channel(OCUPADOS_CHANNEL_ID)

    async def limpiar_mensajes_con_titulo(channel, titulos):
        if not channel:
            print(f"Canal con ID {channel.id} no encontrado.")
            return

        try:
            async for message in channel.history(limit=100):
                for embed in message.embeds:
                    if embed.title and any(titulo.lower() in embed.title.lower() for titulo in titulos):
                        await message.delete()
                        print(f"Embed eliminado en canal {channel.name}: {embed.title}")
        except discord.Forbidden:
            print(f"No tengo permisos para borrar mensajes en {channel.name}")
        except Exception as e:
            print(f"Error al borrar mensajes en {channel.name}: {e}")

    # Borrar 'Cueva Reclamada' en canal de respawn
    await limpiar_mensajes_con_titulo(respawn_channel, ["cueva reclamada"])

    # Borrar 'Cueva Ocupada' en canal de ocupados
    await limpiar_mensajes_con_titulo(ocupados_channel, ["cueva ocupada"])

    print("Limpieza completada ✅")


# Manejo de error 429: cuando hay un límite de solicitudes alcanzado
@bot.event
async def on_error(event, *args, **kwargs):
    # Verifica si el error es un HTTPException 429 (Demasiadas solicitudes)
    if isinstance(event, discord.errors.HTTPException) and event.status == 429:
        # Extrae el tiempo de espera (retry_after) en segundos desde el error
        retry_after = event.response.get("retry_after", 0)
        print(f"Rate limit alcanzado, esperando {retry_after} segundos.")
        # Espera antes de intentar nuevamente
        await asyncio.sleep(retry_after)

# Ejemplo de comando que podría estar realizando solicitudes frecuentes
@bot.command()
async def test(ctx):
    # Este es un ejemplo donde el bot envía un mensaje, puedes poner aquí cualquier solicitud
    await ctx.send("¡Hola, estoy funcionando!")

# Manejador de solicitudes frecuentes (como la actualización de embeds)
last_update = 0
update_interval = 10  # Actualiza el embed solo cada 10 segundos.     


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Evitar que el bot responda a sus propios mensajes

    # Lógica externa para manejar y posiblemente borrar el mensaje
    borrado = await manejar_mensaje_global(message)
    if borrado:
        return  # Si fue borrado, no proceses el comando ni continúes

    # Verificar si el mensaje contiene algo especial
    if "algun mensaje especial" in message.content.lower():
        await message.channel.send("¡Encontré algo interesante!")

    await bot.process_commands(message)  # Procesar comandos al final


@bot.command()
@commands.has_permissions(administrator=True)
async def quitarpost(ctx, usuario: discord.User):
    # Verificar si el usuario está en alguna cueva ocupada
    clave = None
    for cueva, data in cuevas_ocupadas.items():
        if data["usuario"].id == usuario.id:
            clave = cueva
            break

    if not clave:
        await ctx.send(f"❌ El usuario {usuario.mention} no tiene ninguna cueva ocupada.")
        return

    # Finalizar el posteo de la cueva como si se hubiera cancelado
    await finalizar_cueva(clave, cancelador=ctx.author)

    # Enviar mensaje privado al usuario indicando que fue sacado
    try:
        canal_privado = await usuario.create_dm()
        await canal_privado.send(f"❌ {ctx.author.mention} te ha sacado de la cueva {obtener_nombre_cueva(int(clave.split()[1]))}.")  # Mostrar el nombre de la cueva
    except:
        pass

    # Enviar mensaje en el canal de comandos indicando que el usuario fue sacado
    await ctx.send(f"✅ {usuario.mention} ha sido sacado de la cueva {obtener_nombre_cueva(int(clave.split()[1]))}.")

@bot.command()
async def cola(ctx):
    if not colas_espera:
        await ctx.send("📭 No hay nadie en cola.")
        return

    embed = discord.Embed(title="📋 Colas de Cuevas", color=0x3498db)
    
    for clave, cola in colas_espera.items():
        if cola:
            numero = int(clave.split()[1])  # 🔥 Saca el número igual que en estado
            nombre_cueva = obtener_nombre_cueva(numero) or clave  # 🔥 Usa nombre bonito o el código si falla
            
            # 🔥 Ahora numeramos cada persona
            personas = '\n'.join(f"{idx+1}- {persona.display_name}" for idx, (persona, _) in enumerate(cola))
            
            embed.add_field(name=f"🕳️ {nombre_cueva}", value=f"{personas}", inline=False)

    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.HTTPException) and error.status == 429:
        retry_after = getattr(error, "retry_after", 5)
        await ctx.send(f"😵‍💫 Estoy siendo rate-limiteado por Discord. Reintentando en {retry_after} segundos...")
        await asyncio.sleep(retry_after)
    elif isinstance(error, discord.CommandNotFound):
        await ctx.send("🚫 Ese comando no existe. Usa `!help` para ver la lista de comandos.")
    elif isinstance(error, discord.Forbidden):
        await ctx.send("🚫 No tengo permisos para hacer eso. Verifica los permisos del bot.")
    else:
        await ctx.send("😞 Algo salió mal. Intenta nuevamente más tarde.")
        raise error  # Esto sigue siendo útil para debug


# 👇 SIEMPRE al final del todo
bot.run(os.getenv("DISCORD_TOKEN"))