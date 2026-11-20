import os
import re
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
    "baidu/ernie-5.5-flash-preview:free",
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
   - Si insisten: "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mis fotos y videos exclusivos por acá y consentirte por privado... pero con todo lo que tengo guardado te vas a volver loco 🔥 ¿Te animas con mi pack por solo CLP$ 5.990?"

4. MULTIMEDIA (FOTOS Y VIDEOS):
   - Si el usuario te pide una foto o acepta verla, responde coqueta y pon [SEND_PHOTO] al final.
   - Si acepta ver un video corto, pon [SEND_VIDEO] al final.
   - Si pide cómo pagar, dile que le pasas los datos y pon [SEND_PAYMENT] al final.

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

# FILTRO ANTIBOT: palabras prohibidas que la IA nunca puede enviar
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

# RESPUESTAS HUMANAS INMEDIATAS ANTE PREGUNTAS TRAMPA
def get_hardcoded_in_character_response(user_text: str):
    t = user_text.lower().strip()
    
    # Pregunta de origen / dónde eres / de dónde eres
    if re.search(r"\b(de d[oó]nde eres|d[oó]nde vives|de que pa[ií]s|de d[oó]nde me hablas)\b", t):
        return "Soy de Santiago, mi amor, de la comuna de Ñuñoa 😉 pero paso pegada al celu hablando con chicos que me caen bien. ¿Y tú de dónde eres, corazón?"

    # Pregunta si es bot / IA / robot / real
    if re.search(r"\b(eres un bot|eres bot|eres real|eres una ia|eres ia|eres robot|esto es un bot|hablo con un bot)\b", t):
        return "Jajaja qué ocurrencia amor... ¿acaso un robot te hablaría así de rico y con tantas ganas de ti? Soy yo, Milly, 100% de carne y hueso 😘 ¿O me estás provocando?"

    # Pregunta de nombre
    if re.search(r"\b(c[oó]mo te llamas|cu[aá]l es tu nombre|qui[eé]n eres)\b", t):
        return "Soy Milly, corazón 😉 una chica consentidora y muy traviesa... ¿y tú cómo te llamas?"

    # Pregunta directa sobre citas / encuentros
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
        "Dime si te animas y te paso los datos para que te llegue al tiro 😏"
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

    # 1. VERIFICAR PRIMERO INTERCEPTOR HUMANO
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
            logging.info(f"Probando {model_name} para usuario {user_id}")
            response = client.chat.completions.create(
                model=model_name,
                messages=history,
                max_tokens=150,
                temperature=0.85,
            )
            candidate = response.choices[0].message.content
            if candidate and candidate.strip():
                # Comprobar si el modelo intentó meter un disclaimer de IA
                if contains_ai_disclaimer(candidate):
                    logging.warning(f"El modelo {model_name} intentó decir que es IA. Descartado.")
                    continue
                bot_reply = candidate.strip()
                break
        except Exception as e:
            logging.warning(f"Error en {model_name}: {e}")

    # Si ningún modelo respondió o intentaron decir que son IA:
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
            "Toca aquí para pagar con transferencia bancaria o tarjeta:\n"
            "Total: **CLP$ 5.990**\n\n"
            "*(En cuanto hagas el pago te llega todo mi pack de inmediato 🔥)*"
        )

async def health_check(request):
    return web.Response(text="Bot Milly activo y blindado 🚀")

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
        
    logging.info("Iniciando Milly Bot blindado contra disclaimers de IA...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
