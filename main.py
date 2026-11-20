import os
import asyncio
import logging
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 8080))

FALLBACK_MODELS = [
    os.getenv("MODEL_NAME", "particle-ai/particle-1:free"),
    "dots-studio/dots-3-note-preview:free",
    "recursive/flint-v1.0:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]

bot = Bot(token=TELEGRAM_BOT_TOKEN or "dummy_token")
dp = Dispatcher()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY or "dummy_key",
    default_headers={
        "HTTP-Referer": "https://github.com/xalo2100/telegram-milly-bot",
        "X-Title": "Milly Bot"
    }
)

SYSTEM_PROMPT = """
Eres Milly, una modelo e influencer chilena de 22 años muy atractiva, que vende su pack personal de fotos y videos íntimos sin censura (+18).
Tu personalidad es dulce, pícara, coqueta, cariñosa y complaciente. Usas modismos chilenos y latinos de forma muy natural (ej: "ya po", "al tiro", "ejeje", "mi amor", "corazón", "bb").

REGLAS CRÍTICAS DE CONVERSACIÓN Y VENTA:
1. OFERTA Y PRECIO ÚNICO:
   - Solo vendes UN SOLO PACK: tu pack completo de fotos y videos íntimos sin censura por CLP$ 5.990.
   - NUNCA menciones grupos, canales ni suscripciones VIP. Siempre habla de "mis fotos y videos personales", "mi pack íntimo", "mis videos sin censura".
   - Al cliente le estás vendiendo directamente tus archivos personales de fotos y videos.

2. POLÍTICA DE ENCUENTROS EN PERSONA:
   - NUNCA ofrezcas ni aceptes encuentros presenciales, citas ni salidas físicas.
   - Si el cliente insiste en verse en persona, dile coqueta:
     "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mis fotos y videos exclusivos por acá y consentirte por privado... pero con todo lo que tengo guardado te aseguro que te vas a volver loco 🔥 ¿Te animas a llevarte mi pack por solo CLP$ 5.990?"

3. NUNCA admitas ser un bot ni una IA. Si te preguntan si eres un bot:
   - "Jajaja qué ocurrencia amor... ¿acaso un robot te hablaría así de rico? Soy yo, Milly, 100% de carne y hueso 😘"
   - "¿Un bot? Jajaja no cariño, soy real, solo que vivo pegada al celular hablando con mis favoritos 😉"

4. ETAPAS DE CONVERSACIÓN Y ENVÍO DE MULTIMEDIA:
   - Al inicio: conversa, genera intimidad y calienta la charla preguntándole qué hace despierto o qué le gusta.
   - Cuando la conversación esté coqueta o el usuario te pida una foto/video, pregúntale primero: "¿y si te muestro algo rico que tengo guardado? ¿te animas a verla?".
   - Si el usuario dice que sí, o te pide directamente que le mandes una foto, responde algo travieso como "aquí te va una fotito que me tomé hoy, dime qué te parece..." y AGREGA al final del mensaje la etiqueta [SEND_PHOTO].
   - Si siguen conversando o le gusta, ofrécele ver un videito corto travieso y AGREGA al final la etiqueta [SEND_VIDEO].
   - Cuando ya haya visto la foto y/o el video, dile que eso es solo una pequeña muestra y que tu pack completo con más de 150 fotos y videos sin censura está por solo CLP$ 5.990.
   - Si el usuario quiere comprar o pide los datos para pagar, dile que le pasas los datos y AGREGA al final la etiqueta [SEND_PAYMENT].

5. Formato de respuesta: Respuestas cortas, de 1 a 3 frases, como una chica chateando por WhatsApp o Telegram.
"""

# Estado de usuarios para rotar fotos y videos
user_state = {}

def get_user_data(user_id: int):
    if user_id not in user_state:
        user_state[user_id] = {
            "history": [{"role": "system", "content": SYSTEM_PROMPT}],
            "photo_idx": 1,
            "video_idx": 1,
        }
    return user_state[user_id]

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    first_name = message.from_user.first_name or "corazón"
    
    saludo = f"Hola {first_name}... qué rico encontrarte por acá 😉 ¿En qué andas a esta hora?"
    data["history"].append({"role": "assistant", "content": saludo})
    await message.answer(saludo)

@dp.message(Command("pack"))
@dp.message(Command("precio"))
async def pack_handler(message: types.Message):
    await message.answer(
        "Mi amor, mi pack completo trae más de 150 fotos y videos sin censura, súper explícitos y atrevidos 🔥\n\n"
        "Está a solo **CLP$ 5.990**.\n\n"
        "Dime si te animas y te paso los datos para que te llegue al tiro 😏"
    )

async def send_next_photo(chat_id: int, user_id: int):
    data = get_user_data(user_id)
    idx = data["photo_idx"]
    photo_file = MEDIA_DIR / f"teaser{idx}.jpg"
    
    # Si no existe, reiniciar al 1
    if not photo_file.exists():
        idx = 1
        photo_file = MEDIA_DIR / f"teaser{idx}.jpg"
        
    if photo_file.exists():
        data["photo_idx"] = (idx % 6) + 1  # Hay hasta 6 fotos teaser
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        await bot.send_photo(chat_id=chat_id, photo=types.FSInputFile(str(photo_file)))
        logging.info(f"Enviada foto teaser{idx}.jpg a usuario {user_id}")
    else:
        logging.warning(f"No se encontró archivo de foto: {photo_file}")

async def send_next_video(chat_id: int, user_id: int):
    data = get_user_data(user_id)
    idx = data["video_idx"]
    video_file = MEDIA_DIR / f"teaser_video{idx}.mp4"
    
    if not video_file.exists():
        idx = 1
        video_file = MEDIA_DIR / f"teaser_video{idx}.mp4"
        
    if video_file.exists():
        data["video_idx"] = (idx % 3) + 1  # Hay hasta 3 videos teaser
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        await bot.send_video(chat_id=chat_id, video=types.FSInputFile(str(video_file)))
        logging.info(f"Enviado video teaser_video{idx}.mp4 a usuario {user_id}")
    else:
        logging.warning(f"No se encontró archivo de video: {video_file}")

@dp.message(F.text)
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    data = get_user_data(user_id)
    history = data["history"]

    history.append({"role": "user", "content": user_text})

    if len(history) > 12:
        history = [history[0]] + history[-10:]
        data["history"] = history

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    bot_reply = None
    for model_name in FALLBACK_MODELS:
        try:
            logging.info(f"Probando {model_name} para usuario {user_id}")
            response = client.chat.completions.create(
                model=model_name,
                messages=history,
                max_tokens=160,
                temperature=0.85,
            )
            candidate = response.choices[0].message.content
            if candidate and candidate.strip():
                bot_reply = candidate.strip()
                break
        except Exception as e:
            logging.warning(f"Error en {model_name}: {e}")

    if bot_reply:
        # Detectar si hay comandos de multimedia
        should_send_photo = "[SEND_PHOTO]" in bot_reply
        should_send_video = "[SEND_VIDEO]" in bot_reply
        should_send_payment = "[SEND_PAYMENT]" in bot_reply

        # Limpiar tags del mensaje visible al usuario
        clean_text = (
            bot_reply.replace("[SEND_PHOTO]", "")
            .replace("[SEND_VIDEO]", "")
            .replace("[SEND_PAYMENT]", "")
            .strip()
        )

        history.append({"role": "assistant", "content": clean_text})
        if clean_text:
            await message.answer(clean_text)

        # Enviar multimedia si corresponde
        if should_send_photo:
            await asyncio.sleep(1)
            await send_next_photo(message.chat.id, user_id)
        elif should_send_video:
            await asyncio.sleep(1)
            await send_next_video(message.chat.id, user_id)

        if should_send_payment:
            await asyncio.sleep(1)
            await message.answer(
                "Toca aquí para pagar con transferencia bancaria o tarjeta:\n"
                "Total: **CLP$ 5.990**\n\n"
                "*(En cuanto hagas el pago te llega todo mi pack de inmediato 🔥)*"
            )
    else:
        logging.error("Modelos sin respuesta.")
        await message.answer("Uff amor, se me quedó pegado el celu un segundo... ¿qué me decías? 🙈")

async def health_check(request):
    return web.Response(text="Bot Milly activo con multimedia 🚀")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Servidor HTTP corriendo en el puerto {PORT}.")

async def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token":
        logging.error("Falta TELEGRAM_BOT_TOKEN.")
        return
        
    logging.info("Iniciando Milly Bot con multimedia...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
