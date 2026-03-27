import asyncio
import logging
import httpx
import traceback

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

from config import BOT_TOKEN, WEBHOOK_URL
from handlers import start, booking, contacts, my_appointments, operator_appointments, admin

logging.basicConfig(level=logging.INFO)

# 👇 ВСТАВЬ СВОЙ ID
OPERATOR_ID = 502438855

# 💥 Проверка ENV
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан")

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()


# =====================================================
# 🔥 ERROR HANDLER
# =====================================================

async def notify_error(e: Exception):
    error_text = (
        "🚨 <b>Ошибка в боте</b>\n\n"
        f"<b>Тип:</b> {type(e).__name__}\n"
        f"<b>Ошибка:</b> {str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )

    try:
        await bot.send_message(OPERATOR_ID, error_text, parse_mode="HTML")
    except:
        pass


# =====================================================
# 🔹 роутеры
# =====================================================

dp.include_router(start.router)
dp.include_router(booking.router)
dp.include_router(contacts.router)
dp.include_router(my_appointments.router)
dp.include_router(operator_appointments.router)
dp.include_router(admin.router)


# =====================================================
# 🔥 WEBHOOK (ЗАЩИЩЁН)
# =====================================================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    except Exception as e:
        await notify_error(e)
        return {"ok": False}


# =====================================================
# 🔹 проверка сервера
# =====================================================

@app.get("/")
async def root():
    return {"status": "alive 🚀"}


# =====================================================
# 🔥 анти-сон (Render)
# =====================================================

async def self_ping():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(WEBHOOK_URL)
        except Exception as e:
            await notify_error(e)

        await asyncio.sleep(300)


# =====================================================
# 🔥 STARTUP
# =====================================================

@app.on_event("startup")
async def on_startup():
    print("🚀 STARTING BOT...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL + "/webhook")

        print("✅ Webhook установлен:", WEBHOOK_URL)

    except Exception as e:
        print("❌ START ERROR:", e)


# =====================================================
# 🔥 SHUTDOWN
# =====================================================

@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 BOT STOPPED")

    try:
        await bot.delete_webhook()
    except Exception as e:
        await notify_error(e)
