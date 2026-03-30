from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, datetime
import asyncio
import calendar
import time

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
# ⚡ КЕШ
# =========================================
CACHE_TTL = 60
free_times_cache = {}


def get_cache(key):
    if key in free_times_cache:
        t, value = free_times_cache[key]
        if time.time() - t < CACHE_TTL:
            return value
    return None


def set_cache(key, value):
    free_times_cache[key] = (time.time(), value)


async def run_blocking(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args))


async def cached_free_times(therapist_id, date_str, duration):
    key = (therapist_id, date_str)

    cached = get_cache(key)
    if cached is not None:
        return cached

    result = await run_blocking(
        get_free_times,
        therapist_id,
        date_str,
        duration
    )

    set_cache(key, result)
    return result


# =========================================
# 🔥 КАЛЕНДАРЬ (FIX AIROGRAM 3)
# =========================================
async def build_calendar(year, month, therapist_id, duration, selected_day=None):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    today = date.today()

    # заголовок
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}",
            callback_data="ignore"
        )
    ])

    # дни недели
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=d, callback_data="ignore")
        for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    ])

    cal = calendar.monthcalendar(year, month)

    tasks = {}
    for week in cal:
        for day in week:
            if day == 0:
                continue

            d = date(year, month, day)

            if d < today or d.weekday() == 6:
                continue

            tasks[day] = asyncio.create_task(
                cached_free_times(
                    therapist_id,
                    d.isoformat(),
                    duration
                )
            )

    results = {}
    for day, task in tasks.items():
        results[day] = await task

    for week in cal:
        row = []

        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                continue

            d = date(year, month, day)

            if d < today:
                row.append(InlineKeyboardButton(text="❌", callback_data="ignore"))
                continue

            if d.weekday() == 6:
                row.append(InlineKeyboardButton(text=f"{day} 🔒", callback_data="ignore"))
                continue

            times = results.get(day, [])

            if not times:
                row.append(InlineKeyboardButton(text=f"{day} 🔒", callback_data="ignore"))
                continue

            if selected_day == day:
                row.append(
                    InlineKeyboardButton(
                        text=f"🔵 {day}",
                        callback_data=f"date_{d.isoformat()}"
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"date_{d.isoformat()}"
                    )
                )

        kb.inline_keyboard.append(row)

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="<", callback_data=f"prev_{year}_{month}"),
        InlineKeyboardButton(text=">", callback_data=f"next_{year}_{month}")
    ])

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
# MASSAGE
# =========================================
@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    massage_id = int(cb.data.split("_")[1])
    masses = await run_blocking(get_active_masses, "ru")

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
            InlineKeyboardButton(text="Выбрать", callback_data=f"therapist_{t['id']}")
        ]])

        await cb.message.answer(
            f"👩‍⚕️ {t['name']}\n🧠 {t['experience']}",
            reply_markup=kb
        )


# =========================================
# THERAPIST
# =========================================
@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    therapist_id = int(cb.data.split("_")[1])

    await state.update_data(therapist_id=therapist_id)
    await state.set_state(BookingState.date)

    data = await state.get_data()
    now = datetime.now()

    kb = await build_calendar(
        now.year,
        now.month,
        therapist_id,
        data.get("massage_duration", 30)
    )

    await cb.message.answer("📅 Выберите дату:", reply_markup=kb)


# =========================================
# ПЕРЕЛИСТЫВАНИЕ
# =========================================
@router.callback_query(F.data.startswith("prev_"))
async def prev_month(cb: CallbackQuery, state: FSMContext):
    _, y, m = cb.data.split("_")
    y, m = int(y), int(m)

    m -= 1
    if m == 0:
        m = 12
        y -= 1

    data = await state.get_data()

    kb = await build_calendar(y, m, data["therapist_id"], data.get("massage_duration", 30))
    await cb.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(F.data.startswith("next_"))
async def next_month(cb: CallbackQuery, state: FSMContext):
    _, y, m = cb.data.split("_")
    y, m = int(y), int(m)

    m += 1
    if m == 13:
        m = 1
        y += 1

    data = await state.get_data()

    kb = await build_calendar(y, m, data["therapist_id"], data.get("massage_duration", 30))
    await cb.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(F.data == "ignore")
async def ignore(cb: CallbackQuery):
    await cb.answer()


# =========================================
# DATE → TIME
# =========================================
@router.callback_query(BookingState.date, F.data.startswith("date_"))
async def choose_date(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    selected_date = cb.data.replace("date_", "")
    data = await state.get_data()

    times = await cached_free_times(
        data["therapist_id"],
        selected_date,
        data.get("massage_duration", 30)
    )

    if not times:
        await cb.message.answer("❌ Нет свободного времени")
        return

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
