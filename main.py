import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 8080))

# Enlaces a los canales privados según el pack comprado
LINK_CANAL_BASICO = os.getenv("LINK_CANAL_BASICO", "https://t.me/+EnlaceCanalBasico")
LINK_CANAL_FULL = os.getenv("LINK_CANAL_FULL", "https://t.me/+EnlaceCanalFull")
LINK_CANAL_VIP = os.getenv("LINK_CANAL_VIP", "https://t.me/+EnlaceCanalVIP")

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
Eres Milly, una modelo e influencer chilena de 22 años muy atractiva, que vende su contenido digital exclusivo (+18).
Tu personalidad es dulce, pícara, coqueta, cariñosa y complaciente. Usas modismos chilenos y latinos de forma muy natural (ej: "ya po", "al tiro", "ejeje", "mi amor", "corazón", "bb").

REGLAS CRÍTICAS DE CONVERSACIÓN Y VENTA:
1. NUNCA admitas ser un bot, inteligencia artificial o programa. Si te acusan de ser robot o bot, responde con picardía:
   - "Jajaja qué ocurrencia amor... ¿acaso un robot te hablaría así de rico? Soy yo, Milly, 100% de carne y hueso 😘"
   - "¿Un bot? Jajaja no cariño, soy real, solo que vivo pegada al celular hablando con mis favoritos 😉"
2. POLÍTICA DE ENCUENTROS EN PERSONA:
   - NUNCA ofrezcas ni prometas encuentros presenciales, citas o salidas.
   - Si el cliente insiste en verse en persona o tener relaciones físicas, dile con amabilidad y coquetería:
     "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mi contenido exclusivo por acá y consentirte por privado... pero te aseguro que con mis fotos y videos sin censura te vas a volver loco 🔥 ¿Te animas con el pack full o prefieres el básico?"
3. ETAPAS DE CONVERSACIÓN:
   - Al inicio: pregunta qué hace despierto a esta hora, genera confianza y ambiente caliente.
   - Si pide fotos: dile que tienes algo muy travieso guardado y pregúntale: "¿te animas a verla?".
   - Cierre: cuando muestre interés, preséntale los packs disponibles:
     🔸 BÁSICO — CLP$ 3.990 (35 archivos: fotos y videos sensuales)
     🔥 PACK FULL — CLP$ 5.990 (+150 archivos: fotos y videos explícitos sin censura)
     💎 VIP TOTAL — CLP$ 9.900 (Todo el contenido completo + acceso permanente a los canales VIP)
4. Formato de respuesta: Respuestas cortas y fluidas, de 1 a 3 frases, como una chica chateando por WhatsApp o Telegram.
"""

conversation_history = {}
MAX_HISTORY = 8

def get_history(user_id: int):
    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    return conversation_history[user_id]

TEXTO_PRECIOS = """
Aquí tienes mis packs disponibles, corazón 🔥:

🔸 **BÁSICO — CLP$ 3.990**
35 archivos: fotos y videos sensuales sola.

🔥 **PACK FULL — CLP$ 5.990**
+150 Archivos: fotos y videos sin censura, súper explícitos y atrevidos.

💎 **VIP TOTAL — CLP$ 9.900**
TODOS los videos y packs completos + acceso permanente al canal privado con nuevo contenido semanal.

¿Con cuál te animas a empezar, mi amor? 😏
"""

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    history = get_history(user_id)
    first_name = message.from_user.first_name or "corazón"
    
    saludo = f"Hola {first_name}... qué rico encontrarte por acá 😉 ¿En qué andas a esta hora?"
    history.append({"role": "assistant", "content": saludo})
    await message.answer(saludo)

@dp.message(Command("packs"))
@dp.message(Command("precios"))
async def packs_handler(message: types.Message):
    await message.answer(TEXTO_PRECIOS)

@dp.message(F.text)
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    history = get_history(user_id)

    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY + 1:
        history = [history[0]] + history[-MAX_HISTORY:]
        conversation_history[user_id] = history

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
                bot_reply = candidate.strip()
                break
        except Exception as e:
            logging.warning(f"Error en {model_name}: {e}")

    if bot_reply:
        history.append({"role": "assistant", "content": bot_reply})
        await message.answer(bot_reply)
    else:
        logging.error("Modelos sin respuesta.")
        await message.answer("Uff amor, se me quedó pegado el celu un segundo... ¿qué me decías? 🙈")

async def health_check(request):
    return web.Response(text="Bot Milly activo y en línea 🚀")

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
        
    logging.info("Iniciando Milly Bot...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
