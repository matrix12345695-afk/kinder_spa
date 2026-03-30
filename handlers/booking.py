from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import date, timedelta
import asyncio

from sheets import (
    get_user_lang,
    get_active_masses,
    get_therapists_for_massage,
    get_free_times,
    create_appointment,
    get_spreadsheet,
    get_massage_name,
    get_therapist_name,
    notify_error,
    safe_call
)

from handlers.start import main_menu

router = Router()


# =========================================
# 🔥 АНТИЛАГ (ГЛАВНОЕ)
# =========================================
async def run_blocking(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


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
# UI
# =========================================
def operator_keyboard(row: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{row}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{row}")
        ]]
    )


def parse_age(text: str) -> int:
    text = text.lower().replace(" ", "").replace(",", ".")

    if "г" in text:
        return int(float(text.replace("г", "")) * 12)

    if "м" in text:
        return int(text.replace("м", ""))

    return int(float(text))


# =========================================
# START BOOKING
# =========================================
@router.message(
    (F.text.lower().contains("запис")) |
    (F.text.lower().contains("yozil"))
)
async def start_booking(message: Message, state: FSMContext):
    await state.clear()

    lang = await run_blocking(get_user_lang, message.from_user.id) or "ru"
    massages = await run_blocking(get_active_masses, lang)

    if not massages:
        await message.answer("❌ Нет доступных услуг")
        return

    for m in massages:
        text = (
            f"💆‍♂️ {m.get('name')}\n"
            f"👶 {m.get('age_from')} - {m.get('age_to')}\n"
            f"⏱ {m.get('duration')} мин\n"
            f"💰 {m.get('price')} сум"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"massage_{m.get('id')}"
            )
        ]])

        await message.answer(text, reply_markup=kb)


# =========================================
# MASSAGE
# =========================================
@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    try:
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

    except Exception as e:
        notify_error(e)


# =========================================
# THERAPIST
# =========================================
@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    therapist_id = int(cb.data.split("_")[1])

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


# =========================================
# DATE
# =========================================
@router.callback_query(BookingState.date)
async def choose_date(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    data = await state.get_data()

    times = await run_blocking(
        get_free_times,
        data["therapist_id"],
        cb.data,
        data.get("massage_duration", 30)
    )

    if not times:
        await cb.message.answer("❌ Нет свободного времени")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=f"time_{t}")]
                         for t in times]
    )

    await state.update_data(date=cb.data)
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

        await state.clear()

        lang = await run_blocking(get_user_lang, message.from_user.id) or "ru"

        await message.answer("✅ Заявка отправлена", reply_markup=main_menu(lang))

    except Exception as e:
        notify_error(e)
        await message.answer("❌ Ошибка")


# =========================================
# FALLBACK
# =========================================
@router.message(BookingState.phone)
async def fallback(message: Message):
    await message.answer("Нажмите кнопку отправки номера")
