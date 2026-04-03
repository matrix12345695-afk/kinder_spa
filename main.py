
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, WEBHOOK_URL

from handlers.booking import router as booking_router
from handlers.operator import router as operator_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()

dp.include_router(booking_router)
dp.include_router(operator_router)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "alive"}
