from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from sheets import get_user_lang, set_user_lang

router = Router()


# =========================================
# INLINE MENU (УЛУЧШЕННЫЙ UI)
# =========================================
def main_menu(lang: str):
    try:
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
    except:
        return InlineKeyboardMarkup(inline_keyboard=[])


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
    try:
        await state.clear()

        user_id = message.from_user.id
        lang = get_user_lang(user_id)

        if lang not in ["ru", "uz"]:
            set_user_lang(user_id, "ru")

            await message.answer(
                "🌍 <b>Выберите язык</b>\nTilni tanlang 👇",
                reply_markup=language_keyboard(),
                parse_mode="HTML"
            )
            return

        await send_welcome(message, lang)

    except Exception:
        await message.answer("⚠️ Ошибка запуска. Попробуйте позже.")


# =========================================
# LANGUAGE
# =========================================
@router.callback_query(F.data.startswith("lang_"))
async def choose_language(cb: CallbackQuery, state: FSMContext):
    try:
        await cb.answer()

        lang = "uz" if cb.data == "lang_uz" else "ru"
        set_user_lang(cb.from_user.id, lang)

        try:
            await cb.message.delete()
        except:
            pass

        await send_welcome(cb.message, lang)

    except:
        await cb.message.answer("⚠️ Ошибка выбора языка")


# =========================================
# MENU ACTIONS
# =========================================
@router.callback_query(F.data == "menu_lang")
async def change_lang(cb: CallbackQuery):
    try:
        await cb.answer()

        await cb.message.answer(
            "🌍 <b>Выберите язык</b>",
            reply_markup=language_keyboard(),
            parse_mode="HTML"
        )
    except:
        pass


@router.callback_query(F.data == "menu_booking")
async def open_booking(cb: CallbackQuery, state: FSMContext):
    try:
        await cb.answer()

        from sheets import get_active_masses

        lang = get_user_lang(cb.from_user.id) or "ru"
        massages = get_active_masses(lang)

        if not massages:
            if lang == "uz":
                await cb.message.answer("❌ Hozircha xizmatlar mavjud emas")
            else:
                await cb.message.answer("❌ Пока нет доступных услуг")
            return

        for m in massages:
            try:
                m_id = int(m.get("id", 0))
                name = m.get("name", "—")
                price = m.get("price", "—")

                kb = InlineKeyboardMarkup(inline_keyboard=[[  
                    InlineKeyboardButton(
                        text="Выбрать" if lang == "ru" else "Tanlash",
                        callback_data=f"massage_{m_id}"
                    )
                ]])

                age_text = ""
                if m.get("age_from") or m.get("age_to"):
                    age_text = f"\n👶 {m.get('age_from', '')} - {m.get('age_to', '')}"

                await cb.message.answer(
                    f"💆 <b>{name}</b>\n"
                    f"{age_text}\n"
                    f"💰 {price} сум",
                    reply_markup=kb,
                    parse_mode="HTML"
                )

            except:
                continue

    except:
        await cb.message.answer("⚠️ Ошибка загрузки услуг")


# =========================================
# WELCOME (ПРЕМИУМ)
# =========================================
async def send_welcome(message: Message, lang: str):
    try:
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

    except:
        await message.answer("👋 Добро пожаловать!")
