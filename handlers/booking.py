from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta

from sheets import *
from handlers.start import main_menu

router = Router()


class BookingState(StatesGroup):
    massage = State()
    therapist = State()
    date = State()
    time = State()
    parent = State()
    child = State()
    child_age = State()
    phone = State()


def operator_keyboard(row: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{row}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{row}")
        ]]
    )


# =========================================
# AGE PARSER
# =========================================

def parse_age(text: str) -> int:
    text = text.lower().replace(" ", "")

    if "г" in text:
        num = text.replace("г", "").replace("лет", "")
        return int(float(num) * 12)

    if "м" in text:
        num = text.replace("м", "")
        return int(num)

    return int(text)


# =========================================
# START BOOKING
# =========================================

@router.message(F.text.in_(["😺 Записаться", "😺 Yozilish"]))
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    lang = get_user_lang(message.from_user.id) or "ru"

    massages = get_active_masses(lang)

    if not massages:
        await message.answer("❌ Нет доступных услуг")
        return

    for m in massages:
        text = (
            f"💆‍♂️ {m.get('name', 'Без названия')}\n"
            f"👶 {m.get('age_from', '?')}-{m.get('age_to', '?')} лет\n"
            f"⏱ {m.get('duration_min', m.get('duration', '?'))} мин\n"
            f"💰 {m.get('price', '?')} сум"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Выбрать",
                    callback_data=f"massage_{m.get('id')}"
                )
            ]]
        )

        await message.answer(text, reply_markup=kb)


# =========================================
# MASSAGE
# =========================================

@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    try:
        massage_id = int(cb.data.replace("massage_", ""))

        for m in get_active_masses():
            if m.get("id") == massage_id:
                await state.update_data(
                    massage_id=massage_id,
                    massage_duration=m.get("duration_min", 30)
                )

        await state.set_state(BookingState.therapist)

        therapists = get_therapists_for_massage(massage_id)

        if not therapists:
            await cb.message.answer("❌ Нет специалистов")
            return

        for t in therapists:
            text = (
                f"👩‍⚕️ {t.get('name', 'Без имени')}\n"
                f"🧠 Опыт: {t.get('experience', 'нет данных')}"
            )

            kb = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Выбрать",
                        callback_data=f"therapist_{t.get('id')}"
                    )
                ]]
            )

            await cb.message.answer(text, reply_markup=kb)

        await cb.answer()

    except Exception as e:
        notify_error(e)
        await cb.message.answer("❌ Ошибка")


# =========================================
# THERAPIST
# =========================================

@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    therapist_id = int(cb.data.replace("therapist_", ""))

    await state.update_data(therapist_id=therapist_id)
    await state.set_state(BookingState.date)

    today = date.today()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=(today + timedelta(days=i)).strftime("%d.%m"),
                callback_data=(today + timedelta(days=i)).isoformat()
            )
        ] for i in range(7)]
    )

    await cb.message.answer("📅 Выберите дату:", reply_markup=kb)
    await cb.answer()


# =========================================
# DATE
# =========================================

@router.callback_query(BookingState.date)
async def choose_date(cb: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()

        times = get_free_times(
            therapist_id=data.get("therapist_id"),
            date_str=cb.data,
            duration_min=data.get("massage_duration", 30),
        )

        if not times:
            await cb.message.answer("❌ Нет свободного времени")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=t, callback_data=f"time_{t}")
            ] for t in times]
        )

        await state.update_data(date=cb.data)
        await state.set_state(BookingState.time)

        await cb.message.answer("⏰ Выберите время:", reply_markup=kb)
        await cb.answer()

    except Exception as e:
        notify_error(e)
        await cb.message.answer("❌ Ошибка")


# =========================================
# TIME
# =========================================

@router.callback_query(BookingState.time)
async def choose_time(cb: CallbackQuery, state: FSMContext):
    await state.update_data(time=cb.data.replace("time_", ""))
    await state.set_state(BookingState.parent)

    await cb.message.answer("👨‍👩‍👧 Введите имя родителя")
    await cb.answer()


# =========================================
# FORM
# =========================================

@router.message(BookingState.parent)
async def parent_name(message: Message, state: FSMContext):
    await state.update_data(parent_name=message.text)
    await state.set_state(BookingState.child)
    await message.answer("👶 Имя ребенка")


@router.message(BookingState.child)
async def child_name(message: Message, state: FSMContext):
    await state.update_data(child_name=message.text)
    await state.set_state(BookingState.child_age)

    await message.answer(
        "📊 Введите возраст\n\n"
        "Примеры:\n"
        "• 2г\n• 1.5г\n• 18"
    )


@router.message(BookingState.child_age)
async def child_age(message: Message, state: FSMContext):
    try:
        age_months = parse_age(message.text)

        await state.update_data(child_age=age_months)
        await state.set_state(BookingState.phone)

        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
            resize_keyboard=True
        )

        await message.answer("📱 Отправьте номер", reply_markup=kb)

    except:
        await message.answer("❌ Неверный формат возраста")


# =========================================
# FINAL
# =========================================

@router.message(BookingState.phone, F.contact)
async def phone(message: Message, state: FSMContext):
    try:
        data = await state.get_data()

        create_appointment(
            user_id=message.from_user.id,
            massage_id=data.get("massage_id"),
            therapist_id=data.get("therapist_id"),
            datetime_str=f"{data.get('date')} {data.get('time')}",
            parent_name=data.get("parent_name"),
            child_name=data.get("child_name"),
            child_age=data.get("child_age"),
            phone=message.contact.phone_number,
        )

        ws = get_spreadsheet().worksheet("appointments")
        row = len(ws.col_values(1))

        admins = get_spreadsheet().worksheet("admins").get_all_records()

        for a in admins:
            if a.get("role") == "operator":
                try:
                    await message.bot.send_message(
                        int(a.get("user_id")),
                        "📥 Новая заявка!",
                        reply_markup=operator_keyboard(row)
                    )
                except Exception as e:
                    notify_error(e)

        await state.clear()

        lang = get_user_lang(message.from_user.id) or "ru"

        await message.answer(
            "✅ Заявка отправлена!",
            reply_markup=main_menu(lang)
        )

    except Exception as e:
        notify_error(e)
        await message.answer("❌ Ошибка")


@router.message(BookingState.phone)
async def fallback(message: Message):
    await message.answer("Нажмите кнопку отправки номера")
