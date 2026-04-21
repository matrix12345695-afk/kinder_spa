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
            [InlineKeyboardButton(text="✨ Yozilish", callback_data="menu_booking")],
            [InlineKeyboardButton(text="📋 Yozuvlarim", callback_data="menu_my")],
            [
                InlineKeyboardButton(text="📞 Kontaktlar", callback_data="menu_contacts"),
                InlineKeyboardButton(text="🌍 Til", callback_data="menu_lang")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Записаться", callback_data="menu_booking")],
            [InlineKeyboardButton(text="📋 Мои записи", callback_data="menu_my")],
            [
                InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts"),
                InlineKeyboardButton(text="🌍 Язык", callback_data="menu_lang")
            ]
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

    print(f"START user={user_id} lang={lang}")

    if lang not in ["ru", "uz"]:
        set_user_lang(user_id, "ru")

        await message.answer(
            "🌍 <b>Выберите язык</b>\nTilni tanlang 👇",
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )
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

    try:
        await cb.message.delete()
    except:
        pass

    await send_welcome(cb.message, lang)


# =========================================
# 🔥 ПЕРЕДАЧА В BOOKING
# =========================================
@router.callback_query(F.data == "menu_booking")
async def open_booking(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # ❗ просто отправляем кнопку как текст
    await cb.message.answer("📋 Записаться")


# =========================================
# MENU
# =========================================
@router.callback_query(F.data == "menu_lang")
async def change_lang(cb: CallbackQuery):
    await cb.answer()

    await cb.message.answer(
        "🌍 <b>Выберите язык</b>",
        reply_markup=language_keyboard(),
        parse_mode="HTML"
    )


# =========================================
# WELCOME
# =========================================
async def send_welcome(message: Message, lang: str):
    if lang == "uz":
        text = (
            "👋 <b>Kinder Spa ga xush kelibsiz!</b>\n\n"
            "✨ Bolangiz uchun eng yaxshi parvarish\n"
            "💚 Sifatli va xavfsiz xizmat\n\n"
            "👇 Kerakli bo‘limni tanlang"
        )
    else:
        text = (
            "👋 <b>Добро пожаловать в Kinder Spa!</b>\n\n"
            "✨ Забота и комфорт для вашего малыша\n"
            "💚 Профессиональные специалисты\n\n"
            "👇 Выберите нужный раздел"
        )

    await message.answer(
        text,
        reply_markup=main_menu(lang),
        parse_mode="HTML"
    )
