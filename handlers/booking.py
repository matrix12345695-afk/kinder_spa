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
# START BOOKING
# =========================================

@router.message(F.text.in_(["😺 Записаться", "😺 Yozilish"]))
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    lang = get_user_lang(message.from_user.id) or "ru"

    for m in get_active_masses(lang):
        text = (
            f"💆‍♂️ {m['name']}\n"
            f"👶 {m['age_from']}-{m['age_to']} лет\n"
            f"⏱ {m['duration_min']} мин\n"
            f"💰 {m['price']} сум"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Выбрать",
                    callback_data=f"massage_{m['id']}"
                )
            ]]
        )

        await message.answer(text, reply_markup=kb)


# =========================================
# MASSAGE
# =========================================

@router.callback_query(F.data.startswith("massage_"))
async def choose_massage(cb: CallbackQuery, state: FSMContext):
    massage_id = int(cb.data.replace("massage_", ""))

    for m in get_active_masses():
        if m["id"] == massage_id:
            await state.update_data(
                massage_id=massage_id,
                massage_duration=m["duration_min"]
            )

    await state.set_state(BookingState.therapist)

    for t in get_therapists_for_massage(massage_id):
        text = f"👩‍⚕️ {t['name']}\n🧠 Опыт: {t.get('experience', 'нет данных')}"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Выбрать",
                    callback_data=f"therapist_{t['id']}"
                )
            ]]
        )

        await cb.message.answer(text, reply_markup=kb)

    await cb.answer()


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
    data = await state.get_data()

    times = get_free_times(
        therapist_id=data["therapist_id"],
        date_str=cb.data,
        duration_min=data["massage_duration"],
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=t, callback_data=f"time_{t}")
        ] for t in times]
    )

    await state.update_data(date=cb.data)
    await state.set_state(BookingState.time)

    await cb.message.answer("⏰ Выберите время:", reply_markup=kb)
    await cb.answer()


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
    await message.answer("📊 Возраст в месяцах")


@router.message(BookingState.child_age)
async def child_age(message: Message, state: FSMContext):
    await state.update_data(child_age=int(message.text))
    await state.set_state(BookingState.phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
        resize_keyboard=True
    )

    await message.answer("📱 Отправьте номер", reply_markup=kb)


# =========================================
# FINAL
# =========================================

@router.message(BookingState.phone, F.contact)
async def phone(message: Message, state: FSMContext):
    try:
        data = await state.get_data()

        create_appointment(
            user_id=message.from_user.id,
            massage_id=data["massage_id"],
            therapist_id=data["therapist_id"],
            datetime_str=f"{data['date']} {data['time']}",
            parent_name=data["parent_name"],
            child_name=data["child_name"],
            child_age=data["child_age"],
            phone=message.contact.phone_number,
        )

        ws = get_spreadsheet().worksheet("appointments")
        row = len(ws.col_values(1))

        admins = get_spreadsheet().worksheet("admins").get_all_records()

        for a in admins:
            if a["role"] == "operator":
                await message.bot.send_message(
                    int(a["user_id"]),
                    "📥 Новая заявка!",
                    reply_markup=operator_keyboard(row)
                )

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
