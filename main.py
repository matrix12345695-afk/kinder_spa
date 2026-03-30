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
    except:
        pass


# =========================================
# SELF PING
# =========================================

def self_ping():
    url = os.getenv("SELF_PING_URL")

    while True:
        try:
            with httpx.Client(timeout=10) as client:
                client.get(url)
        except:
            pass

        time.sleep(120)


def start_self_ping():
    threading.Thread(target=self_ping, daemon=True).start()


# =========================================
# WEBHOOK CONTROL
# =========================================

async def ensure_webhook():
    try:
        info = await BOT.get_webhook_info()
        correct_url = WEBHOOK_URL + "/webhook"

        if info.url != correct_url:
            await BOT.set_webhook(correct_url)

            await BOT.send_message(
                OPERATOR_ID,
                f"🔧 Webhook восстановлен:\n{correct_url}"
            )

    except Exception as e:
        await notify_error(e)


async def webhook_watcher():
    while True:
        await ensure_webhook()
        await asyncio.sleep(60)


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
# WEBHOOK (БЫСТРЫЙ ОТВЕТ)
# =========================================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update(**data)

        asyncio.create_task(dp.feed_update(bot=BOT, update=update))

        return {"ok": True}

    except Exception as e:
        await notify_error(e)
        return {"ok": False}


# =========================================
# HEALTH
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
        await BOT.set_webhook(WEBHOOK_URL + "/webhook")
    except Exception as e:
        await notify_error(e)

    asyncio.create_task(webhook_watcher())

    start_self_ping()


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
    except:
        pass
