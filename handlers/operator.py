from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "approve")
async def ok(cb: CallbackQuery):
    await cb.answer("OK")
    await cb.message.edit_text(cb.message.text + "\n✅ ПРИНЯТО")

@router.callback_query(F.data == "reject")
async def no(cb: CallbackQuery):
    await cb.answer("NO")
    await cb.message.edit_text(cb.message.text + "\n❌ ОТКЛОНЕНО")

@router.callback_query(F.data == "reschedule")
async def rs(cb: CallbackQuery):
    await cb.answer("Перенос")
    await cb.message.answer("Свяжитесь с клиентом для переноса времени")
