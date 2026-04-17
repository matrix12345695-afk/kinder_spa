from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime

from sheets import create_appointment, get_therapists_for_massage

router = Router()


# =========================================
# FSM
# =========================================
class Form(StatesGroup):
    parent = State()
    child = State()
    phone = State()


# =========================================
# 📱 КНОПКА ТЕЛЕФОНА
# =========================================
async def send_contact_keyboard(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📱 Нажмите кнопку ниже чтобы отправить номер 👇",
        reply_markup=kb
    )


# =========================================
# ВЫБОР МАССАЖА → МАССАЖИСТЫ (🔥 FIX)
# =========================================
@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    massage_id = int(cb.data.split("_")[1])
    await state.update_data(massage_id=massage_id)

    therapists = get_therapists_for_massage(massage_id)

    if not therapists:
        await cb.message.answer("⚠️ Нет доступных специалистов")
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    for t in therapists:
        text = (
            f"👩‍⚕️ {t.get('name')}\n\n"
            f"📅 Стаж: {t.get('experience') or 'не указан'}\n"
            f"📝 {t.get('description') or 'Опытный специалист'}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Выбрать",
                callback_data=f"therapist_{t['id']}"
            )
        ]])

        # ✅ ТОЛЬКО ОДНО сообщение
        await cb.message.answer(text, reply_markup=kb)


# =========================================
# ВЫБОР МАССАЖИСТА
# =========================================
@router.callback_query(F.data.startswith("therapist_"))
async def therapist(cb: CallbackQuery, state: FSMContext):
    await state.update_data(therapist_id=int(cb.data.split("_")[1]))

    await cb.message.answer("👤 Имя родителя:")
    await state.set_state(Form.parent)


# =========================================
# ИМЯ РОДИТЕЛЯ
# =========================================
@router.message(Form.parent)
async def parent(message: Message, state: FSMContext):
    await state.update_data(parent=message.text)

    await message.answer("👶 Имя ребенка:")
    await state.set_state(Form.child)


# =========================================
# ИМЯ РЕБЕНКА
# =========================================
@router.message(Form.child)
async def child(message: Message, state: FSMContext):
    await state.update_data(child=message.text)

    # 💥 ВЫЗОВ КНОПКИ
    await send_contact_keyboard(message)

    await state.set_state(Form.phone)


# =========================================
# ТЕЛЕФОН (КНОПКА)
# =========================================
@router.message(Form.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    data = await state.get_data()

    create_appointment(
        message.from_user.id,
        data.get("parent"),
        data.get("child"),
        "",
        phone,
        data.get("massage_id", 1),
        data.get("therapist_id"),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    await message.answer(
        "✅ <b>Ваша заявка принята!</b>\n\n📞 Мы скоро свяжемся с вами",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()


# =========================================
# ТЕЛЕФОН (ВРУЧНУЮ)
# =========================================
@router.message(Form.phone)
async def phone_manual(message: Message, state: FSMContext):
    data = await state.get_data()

    create_appointment(
        message.from_user.id,
        data.get("parent"),
        data.get("child"),
        "",
        message.text,
        data.get("massage_id", 1),
        data.get("therapist_id"),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    await message.answer(
        "✅ <b>Ваша заявка принята!</b>\n\n📞 Мы скоро свяжемся с вами",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    await state.clear()
