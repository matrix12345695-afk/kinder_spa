from aiogram import Router, F
from aiogram.types import CallbackQuery
from services.sheets import stats

router = Router()

@router.callback_query(F.data == "admin_stats")
async def s(cb: CallbackQuery):
    await cb.answer()
    st = stats()
    await cb.message.answer(f"Всего заявок: {st.get('total',0)}")
