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

    try:
        await BOT.send_message(OPERATOR_ID, text, parse_mode="HTML")
    except:
        pass


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


@app.get("/")
async def root():
    return {"status": "alive"}


# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
async def on_startup():
    print("🚀 STARTING BOT")

    try:
        await BOT.delete_webhook(drop_pending_updates=True)
        await BOT.set_webhook(WEBHOOK_URL + "/webhook")
    except Exception as e:
        await notify_error(e)


@app.on_event("shutdown")
async def on_shutdown():
    await BOT.delete_webhook()
