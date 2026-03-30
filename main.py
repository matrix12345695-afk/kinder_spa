import asyncio
import logging
import traceback
import httpx
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
# 🔥 ASYNC SELF PING (НЕ БЛОКИРУЕТ)
# =========================================

async def self_ping():
    url = os.getenv("SELF_PING_URL")

    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(url)
        except:
            pass

        await asyncio.sleep(120)


# =========================================
# WEBHOOK CONTROL
# =========================================

async def ensure_webhook(force=False):
    try:
        info = await BOT.get_webhook_info()
        correct_url = WEBHOOK_URL + "/webhook"

        if force or info.url != correct_url:
            await BOT.set_webhook(correct_url)

            await BOT.send_message(
                OPERATOR_ID,
                f"🔧 Webhook установлен:\n{correct_url}"
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
    logging.info("🚀 STARTING KINDER SPA BOT")

    try:
        # 💣 ЖЁСТКО СТАВИМ webhook при старте
        await ensure_webhook(force=True)
    except Exception as e:
        await notify_error(e)

    asyncio.create_task(webhook_watcher())
    asyncio.create_task(self_ping())


# =========================================
# SHUTDOWN
# =========================================

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
    except:
        pass
