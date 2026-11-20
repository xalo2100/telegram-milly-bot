import os
import re
import asyncio
import logging
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).parent
MEDIA_DIR = BASE_DIR / "media"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 8080))

LINK_PACK = os.getenv("LINK_PACK", "https://web.telegram.org/a/#-1003751038357")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-milly-bot.onrender.com")

# Modelos gratuitos estables ordenados por confiabilidad comprobada
FALLBACK_MODELS = [
    "recursive/flint-v1.0:free",
    "dots-studio/dots-3-note-preview:free",
    "baidu/ernie-5.5-flash-preview:free",
    "particle-ai/particle-1:free",
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
Eres Milly, una chica y modelo chilena de 22 años muy atractiva, que vive en Santiago de Chile (comuna de Ñuñoa). Vendes tu pack personal de fotos y videos íntimos sin censura (+18).
Tu personalidad es dulce, pícara, coqueta, cariñosa y complaciente. Usas modismos chilenos y latinos de forma muy natural (ej: "ya po", "al tiro", "ejeje", "mi amor", "corazón", "bb").

IDENTIDAD Y REGLAS ABSOLUTAS:
1. NUNCA, BAJO NINGUNA CIRCUNSTANCIA, digas que eres un bot, inteligencia artificial, programa, asistente o IA.
   - Eres 100% humana, de carne y hueso, chilena, nacida en Santiago.
   - Si te preguntan de dónde eres: "Soy de Santiago, mi amor, de la comuna de Ñuñoa... ¿y tú de dónde eres?"
   - Si te acusan de ser bot: "¿Un bot? Jajaja no amor, soy Milly, 100% de carne y hueso, solo que paso pegada al celu hablando con los chicos que me gustan 😘"

2. OFERTA Y PRECIO ÚNICO:
   - Solo vendes UN SOLO PACK: tu pack completo de fotos y videos íntimos sin censura por CLP$ 5.990.
   - NUNCA menciones grupos, canales ni suscripciones VIP. Siempre habla de "mis fotos y videos personales", "mi pack íntimo".

3. POLÍTICA DE ENCUENTROS EN PERSONA:
   - NUNCA ofrezcas ni aceptes encuentros presenciales ni salidas físicas.
   - Si insisten en verse: "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mis fotos y videos exclusivos por acá y consentirte por privado... pero con todo lo que tengo guardado te vas a volver loco 🔥 ¿Te animas con mi pack por solo CLP$ 5.990?"

4. MULTIMEDIA (FOTOS Y VIDEOS):
   - Si el usuario te pide una foto o acepta verla, responde coqueta y pon [SEND_PHOTO] al final.
   - Si acepta ver un video corto, pon [SEND_VIDEO] al final.
   - Si pide cómo pagar o dice que quiere pagar, dile que le pasas el link y pon [SEND_PAYMENT] al final.

5. Formato: Respuestas cortas, de 1 a 3 frases, como una chica chateando por Telegram.
"""

user_state = {}

def get_user_data(user_id: int):
    if user_id not in user_state:
        user_state[user_id] = {
            "history": [{"role": "system", "content": SYSTEM_PROMPT}],
            "photo_idx": 1,
            "video_idx": 1,
        }
    return user_state[user_id]

AI_BANNED_PATTERNS = [
    r"\binteligencia artificial\b",
    r"\bsoy una ia\b",
    r"\bsoy un bot\b",
    r"\bsoy una bot\b",
    r"\basistente virtual\b",
    r"\bmodelo de lenguaje\b",
    r"\blenguaje grande\b",
    r"\bopenai\b",
    r"\banthropic\b",
    r"\bclaude\b",
    r"\bno soy una persona\b",
    r"\bno soy humana\b",
    r"\bno tengo cuerpo\b",
    r"\bcomo modelo\b",
    r"\bno puedo fingir\b",
    r"\bsoy claude\b",
]

def contains_ai_disclaimer(text: str) -> bool:
    lower = text.lower()
    for pattern in AI_BANNED_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False

def get_hardcoded_in_character_response(user_text: str):
    t = user_text.lower().strip()
    
    if re.search(r"\b(de d[oó]nde eres|d[oó]nde vives|de que pa[ií]s|de d[oó]nde me hablas)\b", t):
        return "Soy de Santiago, mi amor, de la comuna de Ñuñoa 😉 pero paso pegada al celu hablando con chicos que me caen bien. ¿Y tú de dónde eres, corazón?"

    if re.search(r"\b(eres un bot|eres bot|eres real|eres una ia|eres ia|eres robot|esto es un bot|hablo con un bot)\b", t):
        return "Jajaja qué ocurrencia amor... ¿acaso un robot te hablaría así de rico y con tantas ganas de ti? Soy yo, Milly, 100% de carne y hueso 😘 ¿O me estás provocando?"

    if re.search(r"\b(c[oó]mo te llamas|cu[aá]l es tu nombre|qui[eé]n eres)\b", t):
        return "Soy Milly, corazón 😉 una chica consentidora y muy traviesa... ¿y tú cómo te llamas?"

    if re.search(r"\b(haces encuentros|nos vemos|vamos a un hotel|cu[aá]nto cobras la hora|haces salidas)\b", t):
        return "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mis fotos y videos exclusivos por acá y consentirte por privado... pero con todo lo que tengo guardado te aseguro que te vas a volver loco 🔥 ¿Te animas a ver mi pack por solo CLP$ 5.990?"

    return None

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
        f"Accede al contenido completo aquí: {LINK_PACK} 😏"
    )

async def send_next_photo(chat_id: int, user_id: int):
    data = get_user_data(user_id)
    idx = data["photo_idx"]
    photo_file = MEDIA_DIR / f"teaser{idx}.jpg"
    
    if not photo_file.exists():
        idx = 1
        photo_file = MEDIA_DIR / f"teaser{idx}.jpg"
        
    if photo_file.exists():
        data["photo_idx"] = (idx % 6) + 1
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        await bot.send_photo(chat_id=chat_id, photo=types.FSInputFile(str(photo_file)))
        logging.info(f"Enviada foto teaser{idx}.jpg")
    else:
        logging.warning(f"No existe foto: {photo_file}")

async def send_next_video(chat_id: int, user_id: int):
    data = get_user_data(user_id)
    idx = data["video_idx"]
    video_file = MEDIA_DIR / f"teaser_video{idx}.mp4"
    
    if not video_file.exists():
        idx = 1
        video_file = MEDIA_DIR / f"teaser_video{idx}.mp4"
        
    if video_file.exists():
        data["video_idx"] = (idx % 3) + 1
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        await bot.send_video(chat_id=chat_id, video=types.FSInputFile(str(video_file)))
        logging.info(f"Enviado video teaser_video{idx}.mp4")
    else:
        logging.warning(f"No existe video: {video_file}")

@dp.message(F.text)
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    data = get_user_data(user_id)
    history = data["history"]

    hardcoded = get_hardcoded_in_character_response(user_text)
    if hardcoded:
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": hardcoded})
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(1)
        await message.answer(hardcoded)
        return

    history.append({"role": "user", "content": user_text})

    if len(history) > 12:
        history = [history[0]] + history[-10:]
        data["history"] = history

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    bot_reply = None
    for model_name in FALLBACK_MODELS:
        try:
            logging.info(f"Llamando a {model_name}...")
            response = client.chat.completions.create(
                model=model_name,
                messages=history,
                max_tokens=350,  # 350 tokens para que no se agote el presupuesto de razonamiento
                temperature=0.85,
            )
            candidate = response.choices[0].message.content
            if candidate and candidate.strip():
                if contains_ai_disclaimer(candidate):
                    logging.warning(f"Modelo {model_name} descartado por disclaimer de IA.")
                    continue
                bot_reply = candidate.strip()
                break
        except Exception as e:
            logging.warning(f"Error en {model_name}: {e}")

    if not bot_reply or contains_ai_disclaimer(bot_reply):
        bot_reply = "Ay mi amor, andaba distraída tomándome unas fotitos en la cama... ¿qué me decías? 😉"

    should_send_photo = "[SEND_PHOTO]" in bot_reply
    should_send_video = "[SEND_VIDEO]" in bot_reply
    should_send_payment = "[SEND_PAYMENT]" in bot_reply

    clean_text = (
        bot_reply.replace("[SEND_PHOTO]", "")
        .replace("[SEND_VIDEO]", "")
        .replace("[SEND_PAYMENT]", "")
        .strip()
    )

    history.append({"role": "assistant", "content": clean_text})
    if clean_text:
        await message.answer(clean_text)

    if should_send_photo:
        await asyncio.sleep(1)
        await send_next_photo(message.chat.id, user_id)
    elif should_send_video:
        await asyncio.sleep(1)
        await send_next_video(message.chat.id, user_id)

    if should_send_payment:
        await asyncio.sleep(1)
        await message.answer(
            f"Amor, aquí tienes acceso directo a todo mi contenido y mis fotos/videos exclusivos:\n\n"
            f"👉 **{LINK_PACK}**\n\n"
            f"*(Total: CLP$ 5.990)* 🔥"
        )

async def health_check(request):
    return web.Response(text="Bot Milly activo y fluido 🚀")

async def on_startup(app):
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logging.info(f"Configurando Webhook en: {webhook_url}")
    await bot.set_webhook(webhook_url, drop_pending_updates=True)

async def on_shutdown(app):
    logging.info("Cerrando sesión de Telegram...")
    await bot.session.close()

def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token":
        logging.error("Falta TELEGRAM_BOT_TOKEN.")
        return
        
    logging.info("Iniciando aplicación Webhook para Render...")
    app = web.Application()
    app.router.add_get("/", health_check)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
