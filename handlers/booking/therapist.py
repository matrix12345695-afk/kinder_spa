
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sheets import get_therapists_for_massage

router = Router()

@router.callback_query(F.data.startswith("massage_"))
async def choose(cb: CallbackQuery):
    massage_id = int(cb.data.split("_")[1])
    therapists = get_therapists_for_massage(massage_id)
    for t in therapists:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Выбрать", callback_data=f"therapist_{t['id']}")
        ]])
        await cb.message.answer(t.get("name"), reply_markup=kb)
