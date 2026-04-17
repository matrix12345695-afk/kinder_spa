from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import asyncio

router = Router()


async def send_contact_keyboard(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # 💥 сброс старой клавиатуры
    await message.answer("⌛", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.4)

    # 💥 новая клавиатура
    await message.answer(
        "📱 Нажмите кнопку ниже 👇",
        reply_markup=kb
    )
