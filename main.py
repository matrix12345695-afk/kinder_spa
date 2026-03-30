import asyncio
import logging
import traceback
import httpx
import threading
import time
import os

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
    except Exception as err:
        logging.error(f"Notify error failed: {err}")


# =========================================
# SELF PING (ANTI-SLEEP)
# =========================================

def self_ping():
    url = os.getenv("SELF_PING_URL", "https://kinder-spa.onrender.com/ping")

    while True:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(url)
                logging.info(f"🔄 Self ping: {r.status_code}")
        except Exception as e:
            logging.error(f"Self ping error: {e}")

        time.sleep(120)


def start_self_ping():
    thread = threading.Thread(target=self_ping)
    thread.daemon = True
    thread.start()


# =========================================
# WEBHOOK CONTROL (🔥 НОВОЕ)
# =========================================

async def webhook_watcher():
    while True:
        try:
            info = await BOT.get_webhook_info()
            correct_url = WEBHOOK_URL + "/webhook"

            if not info.url:
                await BOT.set_webhook(correct_url)

                await BOT.send_message(
                    OPERATOR_ID,
                    f"🚨 Webhook отсутствовал\n\nУстановлен:\n{correct_url}"
                )

            elif info.url != correct_url:
                await BOT.set_webhook(correct_url)

                await BOT.send_message(
                    OPERATOR_ID,
                    f"🔧 Webhook исправлен\n\n{info.url} → {correct_url}"
                )

        except Exception as e:
            await notify_error(e)

        await asyncio.sleep(60)  # 🔥 быстрее реакция

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
# HEALTH / PING
# =========================================

@app.get("/")
async def root():
    return {"status": "alive"}


@app.get("/ping")
async def ping():
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

    # 🔥 проверка webhook
    await ensure_webhook()
    asyncio.create_task(webhook_watcher())

    # 🔥 self ping
    try:
        start_self_ping()
    except Exception as e:
        logging.error(f"Self ping start error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
        logging.info("🛑 Bot stopped")
    except Exception as e:
        logging.error(f"Shutdown error: {e}")
