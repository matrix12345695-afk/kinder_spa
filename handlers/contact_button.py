from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


async def send_contact_keyboard(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True
    )

    # ✅ ОДНО сообщение = ОДНА клавиатура (это ключ)
    await message.answer(
        "📱 Нажмите кнопку ниже чтобы отправить номер 👇",
        reply_markup=kb
    )
