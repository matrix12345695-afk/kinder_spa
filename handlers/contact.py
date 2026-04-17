from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

router = Router()


# 🔥 Универсальная функция вызова кнопки
async def send_contact_keyboard(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # 💥 очищаем старую клаву
    await message.answer("⌛", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.4)

    # 💥 отправляем кнопку
    await message.answer(
        "📱 Нажмите кнопку ниже 👇",
        reply_markup=kb
    )
