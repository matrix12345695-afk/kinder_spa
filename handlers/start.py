from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from handlers.booking import start_booking

router = Router()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Записаться", callback_data="booking")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
    ])

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Kinder Spa 💚", reply_markup=menu())

@router.callback_query(F.data == "booking")
async def go(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await start_booking(cb.message, state)
