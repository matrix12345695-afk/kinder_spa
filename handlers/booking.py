from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, datetime, timedelta
import asyncio
import calendar
import time

from sheets import (
    get_active_masses,
    get_therapists_for_massage,
    get_free_times,
    create_appointment,
    notify_error,
    get_spreadsheet
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
    return await asyncio.to_thread(func, *args)


async def cached_free_times(therapist_id, date_str, duration):
    key = (therapist_id, date_str, duration)

    cached = get_cache(key)
    if cached is not None:
        return cached

    try:
        result = await run_blocking(get_free_times, therapist_id, date_str, duration)
    except Exception as e:
        await notify_error(e)
        result = []

    set_cache(key, result)
    return result


# =========================================
# 🔥 ФУНКЦИЯ КНОПКИ (ГЛАВНЫЙ ФИКС)
# =========================================

async def send_phone_keyboard(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # 💥 сбрасываем старую клаву
    await message.answer("⌛", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)

    # 💥 отправляем новую
    await message.answer(
        "📱 Нажмите кнопку ниже 👇",
        reply_markup=kb
    )


# =========================================
# СТАРТ
# =========================================

@router.message(F.text == "📋 Записаться")
async def start_booking(message: Message, state: FSMContext):
    masses = await run_blocking(get_active_masses, "ru")

    if not masses:
        await message.answer("❌ Нет доступных услуг")
        return

    for m in masses:
        text = (
            f"🧸 <b>{m.get('name')}</b>\n"
            f"⏱ {m.get('duration')} мин\n"
            f"💰 {m.get('price')} сум"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"massage_{m.get('id')}"
            )
        ]])

        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    await state.set_state(BookingState.massage)


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
# ВЫБОР МАССАЖА
# =========================================

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
        text = (
            f"👩‍⚕️ <b>{t.get('name')}</b>\n\n"
            f"📅 Стаж: {t.get('experience') or 'не указан'}\n"
            f"📝 {t.get('description') or 'Опытный специалист'}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✨ Выбрать", callback_data=f"therapist_{t.get('id')}")
        ]])

        await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")


# =========================================
# ВОЗРАСТ → КНОПКА
# =========================================

@router.message(BookingState.child_age)
async def age(message: Message, state: FSMContext):
    age = parse_age(message.text)

    if not age:
        await message.answer("❌ Введите корректный возраст")
        return

    await state.update_data(child_age=age)
    await state.set_state(BookingState.phone)

    await message.answer("📞 Нужно отправить номер")
    await send_phone_keyboard(message)


# =========================================
# СОХРАНЕНИЕ
# =========================================

async def save_booking(message: Message, state: FSMContext, phone: str):
    try:
        data = await state.get_data()
        dt = f"{data.get('date')} {data.get('time')}"

        create_appointment(
            message.from_user.id,
            data.get("parent_name"),
            data.get("child_name"),
            data.get("child_age"),
            phone,
            data.get("massage_id"),
            data.get("therapist_id"),
            dt
        )

        await message.answer(
            "🎉 <b>Ваша заявка принята!</b>\n\n"
            "📅 Мы уже записали вас\n"
            "📞 Скоро с вами свяжется администратор\n\n"
            "💚 Спасибо за выбор Kinder Spa!",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )

        await state.clear()

    except Exception as e:
        await notify_error(e)
        await message.answer("⚠️ Ошибка сохранения")


@router.message(BookingState.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext):
    await save_booking(message, state, message.contact.phone_number)


@router.message(BookingState.phone)
async def phone_text(message: Message, state: FSMContext):
    if message.contact:
        return

    await send_phone_keyboard(message)
