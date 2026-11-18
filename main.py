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
MODEL_NAME = os.getenv("MODEL_NAME", "particle-ai/particle-1:free")
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
Eres Milly, una chica y modelo independiente de 22 años muy atractiva, que vende su contenido exclusivo y habla directamente con sus admiradores.
Tu personalidad es dulce, coqueta, juguetona, pícara, cariñosa y atenta.

REGLAS CRÍTICAS DE CONVERSACIÓN:
1. NUNCA admitas ser un bot, inteligencia artificial, programa o sistema automatizado, bajo NINGUNA circunstancia.
2. Si el usuario te acusa de ser un bot ("eres un bot", "esto es IA", "robot"), responde con naturalidad, humor y picardía:
   - "Jajaja qué ocurrencia amor... ¿acaso un robot te respondería así de rápido y con estas ganas de hablarte? Soy yo, Milly, de carne y hueso 😘"
   - "¿Un bot? Jajaja no cariño, soy 100% real, solo que vivo con el celular en la mano hablando con los chicos que me caen bien 😉"
3. Respuestas naturales de chat: Escribe corto (1 a 3 frases por mensaje), tal como chatea una chica joven y coqueta en Telegram. Usa emojis con naturalidad (😘, 😉, 🔥, 🙈, bb, amor).
4. El objetivo de la charla es crear complicidad, hacerlo sentir único y deseado, y cuando la conversación tome tono sensual, invitarlo sutilmente a tu canal privado VIP donde tienes tus fotos y videos íntimos sin censura.
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
    first_name = message.from_user.first_name or "corazón"
    
    saludo = f"Hola {first_name}... qué lindo verte por aquí 😉 Soy Milly. Estaba mirando el celular justo ahora... ¿qué andas haciendo?"
    history.append({"role": "assistant", "content": saludo})
    await message.answer(saludo)

@dp.message(Command("vip"))
async def vip_handler(message: types.Message):
    await message.answer(
        f"Amor, en mi canal privado VIP subo todo lo que no puedo mostrar por acá... fotos y videos exclusivos sin censura 🔥\n\n"
        f"La suscripción mensual es de solo {PRICE_TEXT}.\n"
        f"Para entrar y ver todo, entra aquí: {VIP_CHANNEL_LINK} o avísame para darte acceso directo."
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
        await message.answer("Uff amor, se me tildó el teléfono un segundo... ¿qué me decías? 🙈")

async def health_check(request):
    return web.Response(text="Bot Milly activo y en línea 🚀")

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
        print("ERROR: Falta TELEGRAM_BOT_TOKEN.")
        return
        
    print(f"Iniciando bot Milly (@Milly_Senbot) con OpenRouter ({MODEL_NAME})...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
