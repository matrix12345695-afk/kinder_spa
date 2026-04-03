import asyncio
import logging
import traceback
import aiohttp

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, WEBHOOK_URL

logging.basicConfig(level=logging.INFO)

BOT = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

OPERATOR_ID = 8752273443


# =========================================
# SAFE IMPORT (ЖЁСТКИЙ)
# =========================================

def safe_import(name):
    module = __import__(name, fromlist=["*"])
    logging.info(f"✅ {name} loaded")
    return module


# handlers
start = safe_import("handlers.start")
booking = safe_import("handlers.booking")
contacts = safe_import("handlers.contacts")
my_appointments = safe_import("handlers.my_appointments")
operator_appointments = safe_import("handlers.operator_appointments")
admin = safe_import("handlers.admin")

# sheets
sheets = safe_import("sheets")

# cache
cache = safe_import("cache")


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
# ERROR REPORT
# =========================================

async def notify_error(e: Exception):
    text = (
        "🚨 <b>ERROR</b>\n\n"
        f"{type(e).__name__}\n"
        f"{str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )

    if len(text) > 4000:
        text = text[:4000]

    try:
        await BOT.send_message(OPERATOR_ID, text, parse_mode="HTML")
    except Exception as send_error:
        logging.error(f"Failed to send error message: {send_error}")


# =========================================
# SELF PING
# =========================================

async def self_ping():
    await asyncio.sleep(10)

    while True:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(WEBHOOK_URL) as resp:
                    logging.info(f"Ping status: {resp.status}")

        except Exception as e:
            logging.warning(f"Self ping failed: {e}")

        await asyncio.sleep(300)


# =========================================
# PRELOAD DATA
# =========================================

async def preload_data():
    try:
        logging.info("⚡ Preloading data...")

        await asyncio.to_thread(sheets.get_active_masses)
        await asyncio.to_thread(lambda: sheets.get_therapists_for_massage(1))
        await asyncio.to_thread(sheets.get_all_appointments_full)

        logging.info("✅ Data preloaded")

    except Exception as e:
        await notify_error(e)


# =========================================
# WEBHOOK
# =========================================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        update = types.Update.model_validate(data)

        await dp.feed_update(bot=BOT, update=update)

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


# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
async def on_startup():
    logging.info("🚀 START BOT")

    await asyncio.sleep(2)

    try:
        await BOT.set_webhook(WEBHOOK_URL + "/webhook")
        logging.info("✅ Webhook set")
    except Exception as e:
        await notify_error(e)

    asyncio.create_task(preload_data())

    if cache:
        await asyncio.to_thread(cache.load_all_data, sheets)
        asyncio.create_task(cache.auto_update(sheets))

    asyncio.create_task(self_ping())


# =========================================
# SHUTDOWN
# =========================================

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
        await BOT.session.close()
    except Exception as e:
        logging.error(f"Shutdown error: {e}")
