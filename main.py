import asyncio
import logging
import httpx

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

from config import BOT_TOKEN, WEBHOOK_URL
from handlers import start, booking, contacts, my_appointments, operator_appointments, admin

# ❌ УБРАЛИ scheduler (ломал запуск)
# from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

# 💥 Проверка ENV
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан")

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()


# 🔹 роутеры
dp.include_router(start.router)
dp.include_router(booking.router)
dp.include_router(contacts.router)
dp.include_router(my_appointments.router)
dp.include_router(operator_appointments.router)
dp.include_router(admin.router)


# 🔹 webhook
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}


# 🔹 проверка сервера
@app.get("/")
async def root():
    return {"status": "alive 🚀"}


# 🔥 анти-сон (Render любит усыплять)
async def self_ping():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(WEBHOOK_URL)
        except Exception as e:
            print("Ping error:", e)
        await asyncio.sleep(300)


@app.on_event("startup")
async def on_startup():
    print("🚀 STARTING BOT...")

    await bot.set_webhook(WEBHOOK_URL + "/webhook")
    print("✅ Webhook установлен:", WEBHOOK_URL)

    # ❌ временно отключено (чтобы не падало)
    # start_scheduler(bot)

    asyncio.create_task(self_ping())


@app.on_event("shutdown")
async def on_shutdown():
    print("🛑 BOT STOPPED")
    await bot.delete_webhook()
