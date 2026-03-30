from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta, datetime
import asyncio
import calendar

from sheets import (
    get_user_lang,
    get_active_masses,
    get_therapists_for_massage,
    get_free_times,
    create_appointment,
    get_massage_name,
    get_therapist_name,
    notify_error,
)

router = Router()

OPERATOR_ID = 8752273443


# =========================================
# АНТИЛАГ
# =========================================
async def run_blocking(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args))


# =========================================
# КАЛЕНДАРЬ
# =========================================
def get_calendar(year: int, month: int, selected_day: int = None):
    kb = InlineKeyboardMarkup(row_width=7)
    today = date.today()

    kb.row(
        InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}",
            callback_data="ignore"
        )
    )

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    kb.row(*[InlineKeyboardButton(text=d, callback_data="ignore") for d in days])

    cal = calendar.monthcalendar(year, month)

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            current_date = date(year, month, day)
            date_str = current_date.isoformat()

            # ❌ прошлые даты
            if current_date < today:
                row.append(InlineKeyboardButton(text="❌", callback_data="ignore"))
                continue

            # 🔒 воскресенье
            if current_date.weekday() == 6:
                row.append(InlineKeyboardButton(text=f"{day} 🔒", callback_data="ignore"))
                continue

            # 🔵 выбранный день
            if selected_day == day:
                row.append(
                    InlineKeyboardButton(
                        text=f"🔵 {day}",
                        callback_data=f"date_{date_str}"
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"date_{date_str}"
                    )
                )

        kb.row(*row)

    kb.row(
        InlineKeyboardButton(text="<", callback_data=f"prev_{year}_{month}"),
        InlineKeyboardButton(text=">", callback_data=f"next_{year}_{month}")
    )

    return kb


# =========================================
# STATES
# =========================================
class BookingState(StatesGroup):
    massage = State()
    therapist = State()
    date = State()
    time = State()
    parent = State()
    child = State()
    child_age = State()
    phone = State()


# =========================================
# PARSE AGE
# =========================================
def parse_age(text: str) -> int:
    text = text.lower().replace(" ", "").replace(",", ".")

    if "г" in text:
        return int(float(text.replace("г", "")) * 12)

    if "м" in text:
        return int(text.replace("м", ""))

    return int(float(text))


# =========================================
# MASSAGE SELECT
# =========================================
@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    massage_id = int(cb.data.split("_")[1])

    lang = await run_blocking(get_user_lang, cb.from_user.id) or "ru"
    masses = await run_blocking(get_active_masses, lang)

    for m in masses:
        if m["id"] == massage_id:
            await state.update_data(
                massage_id=massage_id,
                massage_duration=m.get("duration", 30)
            )

    therapists = await run_blocking(get_therapists_for_massage, massage_id)

    await state.set_state(BookingState.therapist)

    for t in therapists:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"therapist_{t.get('id')}"
            )
        ]])

        await cb.message.answer(
            f"👩‍⚕️ {t.get('name')}\n🧠 {t.get('experience')}",
            reply_markup=kb
        )


# =========================================
# THERAPIST → КАЛЕНДАРЬ
# =========================================
@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    therapist_id = int(cb.data.split("_")[1])

    await state.update_data(therapist_id=therapist_id)
    await state.set_state(BookingState.date)

    now = datetime.now()

    await cb.message.answer(
        "📅 Выберите дату:",
        reply_markup=get_calendar(now.year, now.month)
    )


# =========================================
# ПЕРЕЛИСТЫВАНИЕ
# =========================================
@router.callback_query(F.data.startswith("prev_"))
async def prev_month(cb: CallbackQuery):
    _, year, month = cb.data.split("_")
    year, month = int(year), int(month)

    month -= 1
    if month == 0:
        month = 12
        year -= 1

    await cb.message.edit_reply_markup(
        reply_markup=get_calendar(year, month)
    )


@router.callback_query(F.data.startswith("next_"))
async def next_month(cb: CallbackQuery):
    _, year, month = cb.data.split("_")
    year, month = int(year), int(month)

    month += 1
    if month == 13:
        month = 1
        year += 1

    await cb.message.edit_reply_markup(
        reply_markup=get_calendar(year, month)
    )


@router.callback_query(F.data == "ignore")
async def ignore(cb: CallbackQuery):
    await cb.answer()


# =========================================
# DATE → ВРЕМЯ
# =========================================
@router.callback_query(BookingState.date, F.data.startswith("date_"))
async def choose_date(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    selected_date = cb.data.replace("date_", "")
    dt = datetime.fromisoformat(selected_date)

    await cb.message.edit_reply_markup(
        reply_markup=get_calendar(dt.year, dt.month, dt.day)
    )

    data = await state.get_data()

    times = await run_blocking(
        get_free_times,
        data["therapist_id"],
        selected_date,
        data.get("massage_duration", 30)
    )

    if not times:
        await cb.message.answer("❌ Нет свободного времени")
        return

    # плитка времени
    buttons = []
    row = []
    for i, t in enumerate(times, 1):
        row.append(InlineKeyboardButton(text=t, callback_data=f"time_{t}"))
        if i % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.update_data(date=selected_date)
    await state.set_state(BookingState.time)

    await cb.message.answer("⏰ Выберите время:", reply_markup=kb)


# =========================================
# TIME
# =========================================
@router.callback_query(BookingState.time)
async def choose_time(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    await state.update_data(time=cb.data.replace("time_", ""))
    await state.set_state(BookingState.parent)

    await cb.message.answer("👨‍👩‍👧 Введите имя родителя")


# =========================================
# PARENT
# =========================================
@router.message(BookingState.parent)
async def parent_name(message: Message, state: FSMContext):
    await state.update_data(parent_name=message.text)
    await state.set_state(BookingState.child)

    await message.answer("👶 Имя ребенка")


# =========================================
# CHILD
# =========================================
@router.message(BookingState.child)
async def child_name(message: Message, state: FSMContext):
    await state.update_data(child_name=message.text)
    await state.set_state(BookingState.child_age)

    await message.answer("📊 Введите возраст (2г / 1.5г / 18)")


# =========================================
# AGE
# =========================================
@router.message(BookingState.child_age)
async def child_age(message: Message, state: FSMContext):
    try:
        age = parse_age(message.text)

        await state.update_data(child_age=age)
        await state.set_state(BookingState.phone)

        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
            resize_keyboard=True
        )

        await message.answer("📱 Отправьте номер", reply_markup=kb)

    except:
        await message.answer("❌ Неверный формат")


# =========================================
# PHONE
# =========================================
@router.message(BookingState.phone, F.contact)
async def phone(message: Message, state: FSMContext):
    try:
        data = await state.get_data()

        await run_blocking(
            create_appointment,
            message.from_user.id,
            data["massage_id"],
            data["therapist_id"],
            f"{data['date']} {data['time']}",
            data["parent_name"],
            data["child_name"],
            data["child_age"],
            message.contact.phone_number,
        )

        from sheets import get_spreadsheet
        ss = get_spreadsheet()
        ws = ss.worksheet("appointments")
        row = len(ws.get_all_values())

        bot = message.bot

        massage_name = await run_blocking(get_massage_name, data["massage_id"])
        therapist_name = await run_blocking(get_therapist_name, data["therapist_id"])

        text = (
            "🆕 <b>Новая запись</b>\n\n"
            f"💆 {massage_name}\n"
            f"👩‍⚕️ {therapist_name}\n"
            f"📅 {data['date']} {data['time']}\n"
            f"👨 {data['parent_name']}\n"
            f"👶 {data['child_name']}\n"
            f"📊 {data['child_age']}\n"
            f"📞 {message.contact.phone_number}\n"
            f"🆔 {message.from_user.id}\n"
            f"📌 ROW: {row}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"admin_confirm_{row}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin_cancel_{row}"
                )
            ]
        ])

        await bot.send_message(
            OPERATOR_ID,
            text,
            parse_mode="HTML",
            reply_markup=kb
        )

        await state.clear()

        lang = await run_blocking(get_user_lang, message.from_user.id) or "ru"
        from handlers.start import main_menu

        await message.answer("✅ Заявка отправлена", reply_markup=main_menu(lang))

    except Exception as e:
        notify_error(e)
        await message.answer("❌ Ошибка")
