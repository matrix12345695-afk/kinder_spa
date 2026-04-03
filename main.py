import asyncio
import logging
import traceback
import os
import aiohttp
import time  # 🔥 добавлено

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, WEBHOOK_URL

logging.basicConfig(level=logging.INFO)

BOT = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

OPERATOR_ID = 8752273443

# 🔥 анти-спам
USER_LAST_ACTION = {}


# =========================================
# SELF PING 🔥 (НЕ ДАЁТ RENDER СПАТЬ)
# =========================================

async def self_ping():
    await asyncio.sleep(10)

    url = WEBHOOK_URL

    while True:
        try:
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    logging.info(f"Ping status: {resp.status}")

        except Exception as e:
            logging.warning(f"Self ping failed: {e}")

        await asyncio.sleep(240)


# =========================================
# DEBUG IMPORT SYSTEM 🔥
# =========================================

def safe_import(name):
    try:
        module = __import__(name, fromlist=["*"])
        print(f"✅ {name} OK")
        return module
    except Exception as e:
        print(f"❌ ERROR importing {name}: {e}")
        traceback.print_exc()
        return None


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
# 🔥 PRELOAD DATA
# =========================================

async def preload_data():
    try:
        if not sheets:
            return

        print("⚡ Preloading data...")

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(None, sheets.get_active_masses)
        await loop.run_in_executor(None, lambda: sheets.get_therapists_for_massage(1))
        await loop.run_in_executor(None, sheets.get_all_appointments_full)

        print("✅ Data preloaded")

    except Exception as e:
        await notify_error(e)


# =========================================
# ROUTERS SAFE
# =========================================

try:
    if start and hasattr(start, "router"):
        dp.include_router(start.router)

    if booking and hasattr(booking, "router"):
        dp.include_router(booking.router)

    if contacts and hasattr(contacts, "router"):
        dp.include_router(contacts.router)

    if my_appointments and hasattr(my_appointments, "router"):
        dp.include_router(my_appointments.router)

    if operator_appointments and hasattr(operator_appointments, "router"):
        dp.include_router(operator_appointments.router)

    if admin and hasattr(admin, "router"):
        dp.include_router(admin.router)

except Exception as e:
    print("❌ ROUTER ERROR:", e)
    traceback.print_exc()


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
    except Exception:
        pass


# =========================================
# 🔥 ОБРАБОТКА UPDATE С ЗАЩИТОЙ
# =========================================

async def process_update(update):
    try:
        await dp.feed_update(bot=BOT, update=update)
    except Exception as e:
        await notify_error(e)


# =========================================
# WEBHOOK
# =========================================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        # 🔥 анти-спам
        user_id = data.get("message", {}).get("from", {}).get("id")

        if user_id:
            now = time.time()
            last = USER_LAST_ACTION.get(user_id, 0)

            if now - last < 0.5:
                return {"ok": True}

            USER_LAST_ACTION[user_id] = now

        try:
            update = types.Update.model_validate(data)
        except Exception:
            update = types.Update(**data)

        asyncio.create_task(process_update(update))

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
    print("🚀 START BOT")

    await asyncio.sleep(2)

    try:
        await BOT.set_webhook(WEBHOOK_URL + "/webhook")
        print("✅ Webhook set")
    except Exception as e:
        await notify_error(e)

    # preload
    asyncio.create_task(preload_data())

    # cache
    if cache and sheets:
        await asyncio.to_thread(cache.load_all_data, sheets)
        asyncio.create_task(cache.auto_update(sheets))

    # self ping
    asyncio.create_task(self_ping())


# =========================================
# SHUTDOWN
# =========================================

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
        await BOT.session.close()
    except Exception:
        pass
