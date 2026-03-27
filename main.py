import asyncio
import logging
import traceback
import httpx

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

from config import BOT_TOKEN, WEBHOOK_URL
from handlers import start, booking, contacts, my_appointments, operator_appointments, admin

logging.basicConfig(level=logging.INFO)

BOT = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()

OPERATOR_ID = 502438855


# =========================================
# ERROR REPORT
# =========================================

async def notify_error(e: Exception):
    text = (
        "🚨 <b>Ошибка</b>\n\n"
        f"{type(e).__name__}\n"
        f"{str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )

    if len(text) > 4000:
        text = text[:4000]

    try:
        await BOT.send_message(OPERATOR_ID, text, parse_mode="HTML")
    except Exception as send_err:
        logging.error(f"Error sending error message: {send_err}")


# =========================================
# KEEP ALIVE (FIXED 🔥)
# =========================================

async def keep_alive():
    base_url = WEBHOOK_URL.replace("/webhook", "")
    url = f"{base_url}/health"

    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(url)
                logging.info("🔄 Keep-alive ping sent")
        except Exception as e:
            logging.error(f"KeepAlive error: {e}")

        await asyncio.sleep(600)


# =========================================
# ROUTERS
# =========================================

dp.include_router(start.router)
dp.include_router(booking.router)
dp.include_router(contacts.router)
dp.include_router(my_appointments.router)
dp.include_router(operator_appointments.router)
dp.include_router(admin.router)


# =========================================
# WEBHOOK
# =========================================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot=BOT, update=update)
        return {"ok": True}
    except Exception as e:
        await notify_error(e)
        return {"ok": False}


# =========================================
# HEALTH CHECK (ВАЖНО)
# =========================================

@app.get("/")
async def root():
    return {"status": "alive"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
async def on_startup():
    logging.info("🚀 STARTING BOT")

    try:
        await BOT.delete_webhook(drop_pending_updates=True)
        await BOT.set_webhook(WEBHOOK_URL + "/webhook")
        logging.info("✅ Webhook set")
    except Exception as e:
        await notify_error(e)

    # 🔥 запускаем keep_alive
    try:
        asyncio.create_task(keep_alive())
    except Exception as e:
        logging.error(f"KeepAlive start error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
        logging.info("🛑 Bot stopped")
    except Exception as e:
        logging.error(f"Shutdown error: {e}")
