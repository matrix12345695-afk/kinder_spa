
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
from sheets import create_appointment

router = Router()

class Form(StatesGroup):
    parent = State()
    child = State()
    phone = State()

@router.callback_query(F.data.startswith("therapist_"))
async def therapist(cb: CallbackQuery, state: FSMContext):
    await state.update_data(therapist_id=int(cb.data.split("_")[1]))
    await cb.message.answer("Имя родителя:")
    await state.set_state(Form.parent)

@router.message(Form.parent)
async def parent(message: Message, state: FSMContext):
    await state.update_data(parent=message.text)
    await message.answer("Имя ребенка:")
    await state.set_state(Form.child)

@router.message(Form.child)
async def child(message: Message, state: FSMContext):
    await state.update_data(child=message.text)
    await message.answer("Телефон:")
    await state.set_state(Form.phone)

@router.message(Form.phone)
async def phone(message: Message, state: FSMContext):
    data = await state.get_data()
    create_appointment(
        message.from_user.id,
        data["parent"],
        data["child"],
        "",
        message.text,
        1,
        data["therapist_id"],
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    await message.answer("Готово")
    await state.clear()
