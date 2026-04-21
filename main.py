import logging, asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, WEBHOOK_URL

from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.operator import router as operator_router
from handlers.admin import router as admin_router
from services.reminders import start_reminder_loop

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

dp.include_router(start_router)
dp.include_router(booking_router)
dp.include_router(operator_router)
dp.include_router(admin_router)

@app.on_event("startup")
async def startup():
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(start_reminder_loop(bot))

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}
