import logging
import os

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, WEBHOOK_URL

# 🔥 HANDLERS
dp.include_router(start_router)
dp.include_router(contacts_router)
dp.include_router(my_router)
dp.include_router(admin_router)

# 🔥 booking ПЕРЕД operator
dp.include_router(booking_router)

# ❗ operator САМЫЙ ПОСЛЕДНИЙ
dp.include_router(operator_router)

# ❌ УБРАЛИ router отсюда (он не нужен)
# from handlers.contact_button import router as contact_button_router

from sheets import get_all_appointments_full


# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =====================================================
# TOKEN CHECK
# =====================================================
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is invalid or missing!")


# =====================================================
# INIT
# =====================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = FastAPI()


# =====================================================
# ROUTERS (🔥 ПРАВИЛЬНЫЙ ПОРЯДОК)
# =====================================================

dp.include_router(start_router)
dp.include_router(contacts_router)
dp.include_router(my_router)
dp.include_router(admin_router)
dp.include_router(operator_router)

# ✅ ВСЕГДА ПОСЛЕДНИМ
dp.include_router(booking_router)

logger.info("✅ All routers connected")


# =====================================================
# WEBHOOK
# =====================================================
@app.on_event("startup")
async def on_startup():
    try:
        logger.info("🚀 START BOT")

        # 🔗 Устанавливаем webhook
        await bot.set_webhook(WEBHOOK_URL)
        logger.info("✅ Webhook set")

        # ⚡ Прогрев данных
        logger.info("⚡ Preloading data...")
        get_all_appointments_full()

        logger.info("🔥 BOT READY")

    except Exception as e:
        logger.exception(f"❌ Startup error: {e}")


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp.feed_update(bot=bot, update=update)
        return {"ok": True}

    except Exception as e:
        logger.exception(f"❌ Webhook error: {e}")
        return {"ok": False}


# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/")
async def root():
    return {"status": "alive 🚀"}
