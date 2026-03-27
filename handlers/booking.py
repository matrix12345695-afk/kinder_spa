from aiogram import Router, F
from sheets import notify_error
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta

from sheets import (
    get_active_masses,
    get_therapists_for_massage,
    get_free_times,
    create_appointment,
    get_user_lang,
    get_massage_name,
    get_therapist_name,
    get_spreadsheet,
)
from handlers.start import main_menu

router = Router()

# =====================================================
# TEXTS
# =====================================================

TEXT_AFTER_BOOKING = {
    "ru": (
        "⏳ <b>Ваша заявка отправлена на подтверждение.</b>\n"
        "Мы уведомим вас после решения оператора 💚"
    ),
    "uz": (
        "⏳ <b>Arizangiz tasdiqlash uchun yuborildi.</b>\n"
        "Operator qaroridan so‘ng sizga xabar beramiz 💚"
    ),
}

TEXTS = {
    "choose_date": {
        "ru": "📅 Выберите дату:",
        "uz": "📅 Sanani tanlang:",
    },
    "choose_time": {
        "ru": "⏰ Выберите время:",
        "uz": "⏰ Vaqtni tanlang:",
    },
    "parent": {
        "ru": "👤 Введите имя родителя:",
        "uz": "👤 Ota-onaning ismini kiriting:",
    },
    "child": {
        "ru": "🧸 Введите имя ребёнка:",
        "uz": "🧸 Bolaning ismini kiriting:",
    },
    "child_age": {
        "ru": "👶 Введите возраст ребёнка в месяцах (например: 6):",
        "uz": "👶 Bolaning yoshini oyda kiriting (masalan: 6):",
    },
    "phone": {
        "ru": "📞 Отправьте номер телефона:",
        "uz": "📞 Telefon raqamingizni yuboring:",
    },
}

# =====================================================
# STATES
# =====================================================

class BookingState(StatesGroup):
    massage = State()
    therapist = State()
    date = State()
    time = State()
    parent = State()
    child = State()
    child_age = State()
    phone = State()


# =====================================================
# OPERATOR KEYBOARD
# =====================================================

def operator_keyboard(row: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{row}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{row}")
        ]]
    )


# =====================================================
# START BOOKING
# =====================================================

@router.message(F.text.in_(["😺 Записаться", "😺 Yozilish"]))
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    lang = get_user_lang(message.from_user.id) or "ru"

    for m in get_active_masses(lang):
        text = (
            f"💆 <b>{m['name']}</b>\n"
            f"👶 {m['age_from']}–{m['age_to']} мес\n"
            f"⏱ {m['duration']} мин\n"
            f"💰 {m['price']} сум"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"massage_{m['id']}"
            )]]
        )

        await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =====================================================
# MASSAGE
# =====================================================

@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    massage_id = int(cb.data.replace("massage_", ""))
    lang = get_user_lang(cb.from_user.id) or "ru"

    for m in get_active_masses(lang):
        if m["id"] == massage_id:
            await state.update_data(
                massage_id=massage_id,
                massage_duration=m["duration"]
            )
            break

    await state.set_state(BookingState.therapist)

    for t in get_therapists_for_massage(massage_id):
        text = (
            f"🧑‍⚕️ <b>{t.get('name')}</b>\n"
            f"⏳ Стаж: {t.get('experience', '—')}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"therapist_{t.get('id') or t.get('therapist_id')}"
            )]]
        )

        await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await cb.answer()


# =====================================================
# THERAPIST
# =====================================================

@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    therapist_id = int(cb.data.replace("therapist_", ""))
    await state.update_data(therapist_id=therapist_id)
    await state.set_state(BookingState.date)

    lang = get_user_lang(cb.from_user.id) or "ru"
    today = date.today()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text=(today + timedelta(days=i)).strftime("%d.%m.%Y"),
            callback_data=(today + timedelta(days=i)).isoformat()
        )] for i in range(14)]
    )

    await cb.message.answer(TEXTS["choose_date"][lang], reply_markup=kb)
    await cb.answer()


# =====================================================
# DATE
# =====================================================

@router.callback_query(BookingState.date)
async def choose_date(cb: CallbackQuery, state: FSMContext):
    lang = get_user_lang(cb.from_user.id) or "ru"
    date_str = cb.data
    data = await state.get_data()

    times = get_free_times(
        therapist_id=data["therapist_id"],
        date_str=date_str,
        duration_min=data["massage_duration"],
    )

    if not times:
        await cb.answer("Нет доступного времени", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text=t, callback_data=f"time_{t}"
        )] for t in times]
    )

    await state.update_data(date=date_str)
    await state.set_state(BookingState.time)
    await cb.message.answer(TEXTS["choose_time"][lang], reply_markup=kb)
    await cb.answer()


# =====================================================
# TIME
# =====================================================

@router.callback_query(BookingState.time, F.data.startswith("time_"))
async def choose_time(cb: CallbackQuery, state: FSMContext):
    lang = get_user_lang(cb.from_user.id) or "ru"
    await state.update_data(time=cb.data.replace("time_", ""))
    await state.set_state(BookingState.parent)
    await cb.message.answer(TEXTS["parent"][lang])
    await cb.answer()


# =====================================================
# PARENT / CHILD / AGE
# =====================================================

@router.message(BookingState.parent)
async def parent_name(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id) or "ru"
    await state.update_data(parent_name=message.text)
    await state.set_state(BookingState.child)
    await message.answer(TEXTS["child"][lang])


@router.message(BookingState.child)
async def child_name(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id) or "ru"
    await state.update_data(child_name=message.text)
    await state.set_state(BookingState.child_age)
    await message.answer(TEXTS["child_age"][lang])


@router.message(BookingState.child_age)
async def child_age(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id) or "ru"

    if not message.text.isdigit():
        await message.answer("❌ Введите возраст числом")
        return

    age = int(message.text)
    await state.update_data(child_age=age)
    await state.set_state(BookingState.phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(TEXTS["phone"][lang], reply_markup=kb)


# =====================================================
# PHONE / SAVE
# =====================================================

@router.message(BookingState.phone, F.contact)
async def phone(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        phone = message.contact.phone_number
        lang = get_user_lang(message.from_user.id) or "ru"

        print("🔥 ДОШЛИ ДО СОХРАНЕНИЯ")

        # ✅ сохраняем
        create_appointment(
            user_id=message.from_user.id,
            massage_id=data["massage_id"],
            therapist_id=data["therapist_id"],
            datetime_str=f"{data['date']} {data['time']}",
            parent_name=data["parent_name"],
            child_name=data["child_name"],
            child_age=data["child_age"],
            phone=phone,
        )

        # ✅ ПРАВИЛЬНО получаем последнюю строку
        ws = get_spreadsheet().worksheet("appointments")
        row = len(ws.col_values(1))  # 🔥 ВОТ ФИКС

        massage_name = get_massage_name(data["massage_id"], lang)
        therapist_name = get_therapist_name(data["therapist_id"])

        operator_text = (
            "🆕 <b>Новая заявка</b>\n\n"
            f"💆 Массаж: {massage_name}\n"
            f"🧑‍⚕️ Специалист: {therapist_name}\n"
            f"📅 Дата: {data['date']} {data['time']}\n"
            f"👶 Ребёнок: {data['child_name']} ({data['child_age']} мес)\n"
            f"📞 Телефон: {phone}"
        )

        # ✅ отправка операторам
        admins_ws = get_spreadsheet().worksheet("admins")
        sent = False

        for r in admins_ws.get_all_records():
            if r.get("role") == "operator":
                try:
                    await message.bot.send_message(
                        int(r["user_id"]),
                        operator_text,
                        parse_mode="HTML",
                        reply_markup=operator_keyboard(row)
                    )
                    sent = True
                except Exception as e:
                    notify_error(e)

        if not sent:
            print("❌ ОПЕРАТОР НЕ НАЙДЕН")

        # ✅ ответ пользователю
        await message.answer(
            TEXT_AFTER_BOOKING.get(lang, TEXT_AFTER_BOOKING["ru"]),
            parse_mode="HTML",
            reply_markup=main_menu(lang),
        )

        await state.clear()

    except Exception as e:
        print("💥 ОШИБКА В BOOKING:", e)
        notify_error(e)
        await message.answer("❌ Ошибка при записи")

    await state.clear()
