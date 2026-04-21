from aiogram import Router, F
from aiogram.types import *
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
import asyncio
import re

from sheets import (
    get_active_masses,
    get_therapists_for_massage,
    create_appointment,
    notify_error,
    OPERATOR_ID
)

from handlers.contact_button import send_contact_keyboard

router = Router()


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


def normalize_phone(text: str):
    digits = re.sub(r"\D", "", text)

    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits

    if len(digits) == 9:
        return "+998" + digits

    return None


async def run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


# =========================================
# STATES
# =========================================

class BookingState(StatesGroup):
    massage = State()
    therapist = State()
    parent = State()
    child = State()
    child_age = State()
    phone = State()


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
# ВЫБОР МАССАЖА
# =========================================

@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    massage_id = safe_int(cb.data.split("_")[1])
    await state.update_data(massage_id=massage_id)

    therapists = await run_blocking(get_therapists_for_massage, massage_id)
    await state.set_state(BookingState.therapist)

    for t in therapists:
        text = (
            f"👩‍⚕️ <b>{t.get('name')}</b>\n\n"
            f"📅 Стаж: {t.get('experience') or 'не указан'}\n"
            f"📝 {t.get('description') or 'Опытный специалист'}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✨ Выбрать",
                callback_data=f"therapist_{t.get('id')}"
            )
        ]])

        await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")


# =========================================
# ВЫБОР МАССАЖИСТА
# =========================================

@router.callback_query(F.data.startswith("therapist_"))
async def choose_therapist(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    therapist_id = safe_int(cb.data.split("_")[1])
    await state.update_data(therapist_id=therapist_id)

    await state.set_state(BookingState.parent)
    await cb.message.answer("👤 Введите имя родителя")


# =========================================
# ДАННЫЕ
# =========================================

@router.message(BookingState.parent)
async def parent(message: Message, state: FSMContext):
    await state.update_data(parent_name=message.text)
    await state.set_state(BookingState.child)
    await message.answer("👶 Имя ребенка")


@router.message(BookingState.child)
async def child(message: Message, state: FSMContext):
    await state.update_data(child_name=message.text)
    await state.set_state(BookingState.child_age)
    await message.answer("🎂 Возраст ребенка")


@router.message(BookingState.child_age)
async def age(message: Message, state: FSMContext):
    age = parse_age(message.text)

    if not age:
        await message.answer("❌ Введите корректный возраст")
        return

    await state.update_data(child_age=age)
    await state.set_state(BookingState.phone)

    await send_contact_keyboard(message)


# =========================================
# 💥 СОХРАНЕНИЕ → ОТПРАВКА В ЛИЧКУ
# =========================================

async def save_booking(message: Message, state: FSMContext, phone: str):
    try:
        data = await state.get_data()
        dt = datetime.now().strftime("%Y-%m-%d %H:%M")

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

        text = (
            "🆕 <b>НОВАЯ ЗАЯВКА!</b>\n\n"
            f"👤 Родитель: {data.get('parent_name')}\n"
            f"👶 Ребенок: {data.get('child_name')}\n"
            f"📞 Телефон: {phone}\n\n"
            f"🆔 user_id: {message.from_user.id}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data="approve_1"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_1")
            ]
        ])

        print("📤 ОТПРАВКА В ЛИЧКУ:", OPERATOR_ID)

        await message.bot.send_message(
            chat_id=OPERATOR_ID,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

        print("✅ ДОШЛО ОПЕРАТОРУ")

        await message.answer(
            "🎉 <b>Ваша заявка принята!</b>\n\n"
            "📞 Скоро с вами свяжется администратор",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )

        await state.clear()

    except Exception as e:
        print("❌ ОШИБКА:", e)
        await notify_error(e)
        await message.answer("⚠️ Ошибка сохранения")


# =========================================
# ТЕЛЕФОН
# =========================================

@router.message(BookingState.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext):
    await save_booking(message, state, message.contact.phone_number)


@router.message(BookingState.phone)
async def phone_text(message: Message, state: FSMContext):
    if message.contact:
        return

    phone = normalize_phone(message.text)

    if not phone:
        await message.answer("❌ Введите корректный номер\n+998901234567")
        await send_contact_keyboard(message)
        return

    await save_booking(message, state, phone)


# =========================================
# AGE PARSER
# =========================================

def parse_age(text):
    text = text.lower()
    try:
        num = int(''.join(filter(str.isdigit, text)))
        return num * 12 if "лет" in text or "год" in text else num
    except:
        return None
