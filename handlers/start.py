from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from sheets import get_user_lang, set_user_lang

router = Router()


# =========================================
# INLINE MENU
# =========================================
def main_menu(lang: str):
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="😺 Yozilish", callback_data="menu_booking")],
            [InlineKeyboardButton(text="📋 Mening yozuvlarim", callback_data="menu_my")],
            [InlineKeyboardButton(text="📞 Kontaktlar", callback_data="menu_contacts")],
            [InlineKeyboardButton(text="🌍 Tilni o‘zgartirish", callback_data="menu_lang")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="😺 Записаться", callback_data="menu_booking")],
            [InlineKeyboardButton(text="📋 Мои записи", callback_data="menu_my")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts")],
            [InlineKeyboardButton(text="🌍 Сменить язык", callback_data="menu_lang")]
        ])


def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang_uz"),
        ]
    ])


# =========================================
# START
# =========================================
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if lang is None or not lang:
        set_user_lang(user_id, "")
        await message.answer("🌍 Выберите язык / Tilni tanlang:", reply_markup=language_keyboard())
        return

    await send_welcome(message, lang)


# =========================================
# LANGUAGE
# =========================================
@router.callback_query(F.data.startswith("lang_"))
async def choose_language(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    lang = "uz" if cb.data == "lang_uz" else "ru"
    set_user_lang(cb.from_user.id, lang)

    await send_welcome(cb.message, lang)


# =========================================
# MENU ACTIONS
# =========================================
@router.callback_query(F.data == "menu_lang")
async def change_lang(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("🌍 Выберите язык:", reply_markup=language_keyboard())


@router.callback_query(F.data == "menu_booking")
async def open_booking(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    from sheets import get_active_masses

    lang = get_user_lang(cb.from_user.id) or "ru"
    massages = get_active_masses(lang)

    if not massages:
        await cb.message.answer("❌ Нет услуг")
        return

    for m in massages:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Выбрать", callback_data=f"massage_{m['id']}")
        ]])

        await cb.message.answer(
            f"💆 {m['name']}\n💰 {m['price']} сум",
            reply_markup=kb
        )


# =========================================
# WELCOME
# =========================================
async def send_welcome(message: Message, lang: str):
    if lang == "uz":
        text = "👋 Kinder Spa ga xush kelibsiz!\nQuyidan tanlang 👇"
    else:
        text = "👋 Добро пожаловать в Kinder Spa!\nВыберите действие 👇"

    await message.answer(text, reply_markup=main_menu(lang))
