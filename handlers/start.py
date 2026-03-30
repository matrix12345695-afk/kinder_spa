from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

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

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    try:
        await state.clear()

        user_id = message.from_user.id
        lang = get_user_lang(user_id)

        # 🔥 СОЗДАЁМ ПОЛЬЗОВАТЕЛЯ ЕСЛИ НЕТ
        if lang is None:
            set_user_lang(user_id, "")
            await message.answer(
                "🌍 Выберите язык / Tilni tanlang:",
                reply_markup=language_keyboard()
            )
            return

        # если язык пустой
        if not lang:
            await message.answer(
                "🌍 Выберите язык / Tilni tanlang:",
                reply_markup=language_keyboard()
            )
            return

        await send_welcome(message, lang)

    except Exception:
        await message.answer("⚠️ Ошибка при запуске. Попробуйте ещё раз.")


# =====================================================
# LANGUAGE CHOICE
# =====================================================

@router.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O‘zbekcha"]))
async def choose_language(message: Message, state: FSMContext):
    try:
        await state.clear()

        user_id = message.from_user.id
        lang = "uz" if "O‘zbek" in message.text else "ru"

        set_user_lang(user_id, lang)

        await send_welcome(message, lang)

    except Exception:
        await message.answer("⚠️ Ошибка при выборе языка")


# =====================================================
# CHANGE LANGUAGE
# =====================================================

@router.message(F.text.in_(["🌍 Сменить язык", "🌍 Tilni o‘zgartirish"]))
async def change_language(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🌍 Выберите язык / Tilni tanlang:",
        reply_markup=language_keyboard()
    )


# =====================================================
# GLOBAL GUARD (НЕ ЛОМАЕТ booking)
# =====================================================

@router.message()
async def force_language_choice(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    text = (message.text or "").lower()

    # ❗ ПРОПУСКАЕМ ВСЕ КНОПКИ ОСНОВНОГО МЕНЮ
    if any(word in text for word in [
        "запис", "yozil",
        "контакт", "kontakt",
        "мои", "mening"
    ]):
        return

    if not lang:
        await message.answer(
            "🌍 Сначала выберите язык:",
            reply_markup=language_keyboard()
        )


# =====================================================
# WELCOME
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
