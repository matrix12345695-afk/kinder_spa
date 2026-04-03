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


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


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

    try:
        result = await run_blocking(
            get_free_times,
            therapist_id,
            date_str,
            duration
        )
    except Exception as e:
        notify_error(e)
        result = []

    set_cache(key, result)
    return result


async def build_calendar(year, month, therapist_id, duration, selected_day=None):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    today = date.today()

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}",
            callback_data="ignore"
        )
    ])

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
        try:
            results[day] = await task
        except:
            results[day] = []

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

            row.append(
                InlineKeyboardButton(
                    text=str(day),
                    callback_data=f"date_{d.isoformat()}"
                )
            )

        kb.inline_keyboard.append(row)

    return kb


class BookingState(StatesGroup):
    massage = State()
    therapist = State()
    date = State()
    time = State()
    parent = State()
    child = State()
    child_age = State()
    phone = State()


@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    massage_id = safe_int(cb.data.split("_")[1])
    masses = await run_blocking(get_active_masses, "ru")

    for m in masses:
        if safe_int(m.get("id")) == massage_id:
            await state.update_data(
                massage_id=massage_id,
                massage_duration=m.get("duration", 30)
            )

    therapists = await run_blocking(get_therapists_for_massage, massage_id)

    await state.set_state(BookingState.therapist)

    for t in therapists:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Выбрать", callback_data=f"therapist_{t.get('id')}")
        ]])

        await cb.message.answer(f"{t.get('name')}", reply_markup=kb)


@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    therapist_id = safe_int(cb.data.split("_")[1])

    await state.update_data(therapist_id=therapist_id)
    await state.set_state(BookingState.date)

    now = datetime.now()

    kb = await build_calendar(
        now.year,
        now.month,
        therapist_id,
        30
    )

    await cb.message.answer("📅 Выберите дату:", reply_markup=kb)


@router.callback_query(BookingState.date, F.data.startswith("date_"))
async def choose_date(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    selected_date = cb.data.replace("date_", "")
    data = await state.get_data()

    times = await cached_free_times(
        data.get("therapist_id"),
        selected_date,
        data.get("massage_duration", 30)
    )

    buttons = []
    for t in times:
        buttons.append([InlineKeyboardButton(text=t, callback_data=f"time_{t}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.update_data(date=selected_date)
    await state.set_state(BookingState.time)

    await cb.message.answer("⏰ Выберите время:", reply_markup=kb)


@router.callback_query(BookingState.time, F.data.startswith("time_"))
async def choose_time(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.update_data(time=cb.data.replace("time_", ""))
    await state.set_state(BookingState.parent)
    await cb.message.answer("👩 Имя родителя:")


@router.message(BookingState.parent)
async def parent(message: Message, state: FSMContext):
    await state.update_data(parent_name=message.text)
    await state.set_state(BookingState.child)
    await message.answer("👶 Имя ребёнка:")


@router.message(BookingState.child)
async def child(message: Message, state: FSMContext):
    await state.update_data(child_name=message.text)
    await state.set_state(BookingState.child_age)
    await message.answer("Возраст:")


@router.message(BookingState.child_age)
async def age(message: Message, state: FSMContext):
    await state.update_data(child_age=message.text)
    await state.set_state(BookingState.phone)
    await message.answer("📞 Телефон:")


@router.message(BookingState.phone)
async def phone(message: Message, state: FSMContext):
    data = await state.get_data()

    dt = f"{data.get('date')} {data.get('time')}"

    row = create_appointment(
        message.from_user.id,
        data.get("parent_name"),
        data.get("child_name"),
        data.get("child_age"),
        message.text,
        data.get("massage_id"),
        data.get("therapist_id"),
        dt
    )

    if not row:
        await message.answer("❌ Ошибка сохранения")
        return

    # 🔥 ОТПРАВКА ОПЕРАТОРУ С ROW
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{row}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{row}")
    ]])

    await message.bot.send_message(
        OPERATOR_ID,
        f"🆕 Новая запись\n📅 {dt}",
        reply_markup=kb
    )

    await message.answer("✅ Запись создана!")
    await state.clear()
