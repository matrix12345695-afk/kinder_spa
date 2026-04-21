
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📞 Контакты")]
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer("🌸 Добро пожаловать в Kinder Spa!", reply_markup=kb)

@router.message(lambda m: m.text == "📞 Контакты")
async def contacts(msg: types.Message):
    await msg.answer("📍 Адрес...
📞 +998...")
