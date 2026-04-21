
import asyncio
import logging
from aiogram import Bot, Dispatcher
import os

from handlers import start, booking

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# register routers
dp.include_router(start.router)
dp.include_router(booking.router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
