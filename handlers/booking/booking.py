from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
from config import OPERATOR_ID
from services.sheets import add_appointment, get_busy_slots

router = Router()

class Form(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    name = State()
    phone = State()

SERVICES = ["Массаж","SPA","Бассейн"]
MASTERS = ["Анна","Мария","Ольга"]
TIMES = ["10:00","12:00","14:00","16:00","18:00"]

def dates_kb():
    today = datetime.now()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=(today+timedelta(days=i)).strftime("%d.%m"), callback_data=f"date_{(today+timedelta(days=i)).strftime('%d.%m')}")]
        for i in range(5)
    ])

async def start_booking(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=s, callback_data=f"service_{s}")] for s in SERVICES])
    await message.answer("Выберите услугу:", reply_markup=kb)

@router.callback_query(F.data.startswith("service_"))
async def service(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    s = cb.data.split("_",1)[1]
    await state.update_data(service=s)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=m, callback_data=f"master_{m}")] for m in MASTERS])
    await cb.message.answer("Выберите мастера:", reply_markup=kb)

@router.callback_query(F.data.startswith("master_"))
async def master(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    m = cb.data.split("_",1)[1]
    await state.update_data(master=m)
    await cb.message.answer("Выберите дату:", reply_markup=dates_kb())

@router.callback_query(F.data.startswith("date_"))
async def date(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    d = cb.data.split("_",1)[1]
    data = await state.get_data()
    busy = get_busy_slots(d, data.get("master"))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t + (" ❌" if t in busy else ""), callback_data=f"time_{t}")]
        for t in TIMES if t not in busy
    ])
    await state.update_data(date=d)
    await cb.message.answer("Выберите время:", reply_markup=kb)

@router.callback_query(F.data.startswith("time_"))
async def time(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    t = cb.data.split("_",1)[1]
    await state.update_data(time=t)
    await cb.message.answer("Введите имя:")
    await state.set_state(Form.name)

@router.message(Form.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите телефон:")
    await state.set_state(Form.phone)

@router.message(Form.phone)
async def phone(message: Message, state: FSMContext):
    data = await state.get_data()
    rec = {
        "user_id": message.from_user.id,
        "service": data.get("service"),
        "master": data.get("master"),
        "date": data.get("date"),
        "time": data.get("time"),
        "name": data.get("name"),
        "phone": message.text
    }
    add_appointment(rec)
    text = f"Новая запись\n{rec}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅", callback_data="approve"),
        InlineKeyboardButton(text="❌", callback_data="reject"),
        InlineKeyboardButton(text="🔁 Перенести", callback_data="reschedule")
    ]])
    await message.bot.send_message(OPERATOR_ID, text, reply_markup=kb)
    await message.answer("Запись отправлена ✅")
    await state.clear()
