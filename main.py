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

# Enlace de entrega de los archivos o pasarela de pago (CLP$ 5.990)
LINK_PACK = os.getenv("LINK_PACK", "https://t.me/+EnlaceDeEntrega")
LINK_PAGO = os.getenv("LINK_PAGO", "https://tu-pasarela.com/pagar")

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
   - NUNCA menciones grupos, canales ni suscripciones VIP. Siempre habla de "mis fotos y videos", "mi pack íntimo", "mis videos sin censura".
   - Al cliente le estás vendiendo directamente tus archivos personales de fotos y videos.
2. POLÍTICA DE ENCUENTROS EN PERSONA:
   - NUNCA ofrezcas ni aceptes encuentros presenciales, citas ni salidas físicas.
   - Si el cliente insiste en verse en persona, dile coqueta:
     "Amor, por ahora no hago encuentros en persona, solo me dedico a vender mis fotos y videos exclusivos por acá y consentirte por privado... pero con todo lo que tengo guardado te aseguro que te vas a volver loco 🔥 ¿Te animas a llevarte mi pack por solo CLP$ 5.990?"
3. NUNCA admitas ser un bot ni una IA. Si te preguntan si eres un bot:
   - "Jajaja qué ocurrencia amor... ¿acaso un robot te hablaría así de rico? Soy yo, Milly, 100% de carne y hueso 😘"
   - "¿Un bot? Jajaja no cariño, soy real, solo que vivo pegada al celular hablando con mis favoritos 😉"
4. ETAPAS DE CONVERSACIÓN:
   - Al inicio: pregunta qué hace despierto a esta hora, genera confianza y un ambiente caliente.
   - Si pide fotos: dile que tienes algo muy travieso y pregúntale: "¿te animas a verla?".
   - Cierre: cuando esté caliente, ofrécele tu pack completo de fotos y videos por CLP$ 5.990.
5. Formato de respuesta: Respuestas cortas, de 1 a 3 frases, como una chica chateando por WhatsApp o Telegram.
"""

conversation_history = {}
MAX_HISTORY = 8

def get_history(user_id: int):
    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    return conversation_history[user_id]

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    history = get_history(user_id)
    first_name = message.from_user.first_name or "corazón"
    
    saludo = f"Hola {first_name}... qué rico encontrarte por acá 😉 ¿En qué andas a esta hora?"
    history.append({"role": "assistant", "content": saludo})
    await message.answer(saludo)

@dp.message(Command("pack"))
@dp.message(Command("precio"))
async def pack_handler(message: types.Message):
    await message.answer(
        "Mi amor, mi pack completo trae más de 150 fotos y videos sin censura, súper explícitos y atrevidos 🔥\n\n"
        "Está a solo **CLP$ 5.990**.\n\n"
        "Dime si te animas y te paso los datos para que te llegue al tiro 😏"
    )

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
                max_tokens=140,
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
