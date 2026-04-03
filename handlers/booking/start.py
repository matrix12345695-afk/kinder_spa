
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sheets import get_active_masses

router = Router()

@router.message(F.text == "📋 Записаться")
async def start(message: Message):
    masses = get_active_masses("ru")
    for m in masses:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Выбрать", callback_data=f"massage_{m['id']}")
        ]])
        await message.answer(f"{m['name']} - {m.get('price')}", reply_markup=kb)
