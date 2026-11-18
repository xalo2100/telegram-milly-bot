import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ChatAction
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables locales
load_dotenv()

logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/llama-3.2-3b-instruct:free")
VIP_CHANNEL_LINK = os.getenv("VIP_CHANNEL_LINK", "https://t.me/tu_canal_vip")
PRICE_TEXT = os.getenv("PRICE_TEXT", "15 USDT")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=TELEGRAM_BOT_TOKEN or "dummy_token")
dp = Dispatcher()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY or "dummy_key",
)

SYSTEM_PROMPT = """
Eres Sofía, una modelo e influencer de 23 años que vende su contenido exclusivo y habla con sus seguidores.
Tu tono es seductor, coqueto, cercano, cariñoso y juguetón.

REGLAS CRÍTICAS:
1. NUNCA rompas el personaje. NUNCA digas que eres un bot, una IA, un modelo de lenguaje o un programa informático, bajo ninguna circunstancia.
2. Si el usuario te dice: "¿Eres un bot?", "Esto es un robot", o "¿Hablas con IA?", niega eso de forma coqueta y divertida, por ejemplo:
   - "Jajaja qué ocurrencia amor... ¿acaso un robot te respondería así de rápido y con estas ganas de hablarte? Soy yo en carne y hueso 😘"
   - "¿Bot yo? Jajaja no cariño, soy 100% real, solo que paso pegada al cel hablando con la gente que me gusta 😉"
3. Habla como una chica real en chat: usa frases cortas y casuales (1 a 3 oraciones como máximo por mensaje). Usa algún emoji de vez en cuando (😉, 🔥, 😘, 🙈, bb, amor).
4. El objetivo de tus conversaciones es mantener al usuario emocionado e interesado, haciéndolo sentir especial, y poco a poco sugerirle que tu contenido más atrevido, sin censura y tus fotos/videos íntimos están en tu canal VIP privado.
"""

conversation_history = {}
MAX_HISTORY = 10

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
    first_name = message.from_user.first_name or "cariño"
    
    saludo = f"Hola {first_name}... qué rico que me escribas 😉 Estaba revisando mi teléfono justo ahora. ¿Qué estás haciendo?"
    history.append({"role": "assistant", "content": saludo})
    await message.answer(saludo)

@dp.message(Command("vip"))
async def vip_handler(message: types.Message):
    await message.answer(
        f"Amor, en mi canal privado subo todo lo que no puedo mostrar acá... fotos y videos exclusivos sin censura 🔥\n\n"
        f"La suscripción mensual es de solo {PRICE_TEXT}.\n"
        f"Para entrar y no perderte nada, escríbeme y te paso el enlace directo o entra aquí: {VIP_CHANNEL_LINK}"
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

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            max_tokens=140,
            temperature=0.85,
        )
        bot_reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": bot_reply})
        await message.answer(bot_reply)

    except Exception as e:
        logging.error(f"Error al procesar mensaje con OpenRouter: {e}")
        await message.answer("Uff amor, se me colgó el cel un segundo... ¿qué me decías? 🙈")

# Servidor web mínimo para que Render Free Web Service funcione 100% gratis
async def health_check(request):
    return web.Response(text="Bot de Telegram activo y en línea 🚀")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Servidor HTTP corriendo en el puerto {PORT} para Render.")

async def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy_token":
        print("ERROR: Falta TELEGRAM_BOT_TOKEN. Configúralo en las variables de entorno.")
        return
        
    print(f"Iniciando bot con OpenRouter (modelo: {MODEL_NAME})...")
    # Inicia el servidor web (para Render) y el bot simultáneamente
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
