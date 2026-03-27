from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from sheets import get_user_lang, set_user_lang

router = Router()


# =====================================================
# KEYBOARDS
# =====================================================

def language_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🇷🇺 Русский"),
                KeyboardButton(text="🇺🇿 O‘zbekcha"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def main_menu(lang: str):
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="😺 Yozilish")],
                [KeyboardButton(text="📋 Mening yozuvlarim")],
                [KeyboardButton(text="📞 Kontaktlar")],
                [KeyboardButton(text="🌍 Tilni o‘zgartirish")],
            ],
            resize_keyboard=True
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="😺 Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
            [KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="🌍 Сменить язык")],
        ],
        resize_keyboard=True
    )


# =====================================================
# /start
# =====================================================

@router.message(F.text == "/start")
async def start(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    # если язык ещё не выбран — сначала выбор языка
    if not lang:
        await message.answer(
            "🌍 Выберите язык / Tilni tanlang:",
            reply_markup=language_keyboard()
        )
        return

    await send_welcome(message, lang)


# =====================================================
# LANGUAGE CHOICE (FIRST TIME OR AFTER CHANGE)
# =====================================================

@router.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O‘zbekcha"]))
async def choose_language(message: Message):
    user_id = message.from_user.id

    lang = "uz" if "O‘zbek" in message.text else "ru"
    set_user_lang(user_id, lang)

    await send_welcome(message, lang)


# =====================================================
# CHANGE LANGUAGE BUTTON
# (устойчиво к o‘ / o' и любым правкам текста)
# =====================================================

@router.message(
    (F.text.contains("Сменить язык")) |
    (F.text.contains("Tilni"))
)
async def change_language(message: Message):
    await message.answer(
        "🌍 Выберите язык / Tilni tanlang:",
        reply_markup=language_keyboard()
    )


# =====================================================
# WELCOME MESSAGE
# =====================================================

async def send_welcome(message: Message, lang: str):
    if lang == "uz":
        text = (
            "👋 Kinder Spa ga xush kelibsiz!\n\n"
            "Biz — bolalar sog‘lomlashtirish markazimiz 💚\n"
            "Bolalarning sog‘lom va baxtli ulg‘ayishiga yordam beramiz.\n\n"
            "Quyidan kerakli bo‘limni tanlang 👇"
        )
    else:
        text = (
            "👋 Добро пожаловать в Kinder Spa!\n\n"
            "Мы — детский оздоровительный центр 💚\n"
            "Помогаем малышам расти здоровыми и счастливыми.\n\n"
            "Выберите действие ниже 👇"
        )

    await message.answer(text, reply_markup=main_menu(lang))
