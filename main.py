import asyncio
import logging
import traceback
import os

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


# =========================================
# ROUTERS SAFE
# =========================================

try:
    if start: dp.include_router(start.router)
    if booking: dp.include_router(booking.router)
    if contacts: dp.include_router(contacts.router)
    if my_appointments: dp.include_router(my_appointments.router)
    if operator_appointments: dp.include_router(operator_appointments.router)
    if admin: dp.include_router(admin.router)
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
    except:
        pass


# =========================================
# WEBHOOK
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


# =========================================
# SHUTDOWN
# =========================================

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await BOT.delete_webhook()
    except:
        pass
