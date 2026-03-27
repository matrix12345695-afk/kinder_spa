from aiogram import Router, F
from aiogram.types import CallbackQuery

from sheets import (
    get_admin_role,
    update_appointment_status,
    get_spreadsheet,
)

router = Router()


@router.callback_query(F.data.startswith(("approve_", "reject_")))
async def process_appointment(cb: CallbackQuery):
    # ⚡️ СРАЗУ отвечаем Telegram (убирает "загрузка")
    await cb.answer()

    user_id = cb.from_user.id

    # 🔐 проверка роли (ОДИН вызов)
    if get_admin_role(user_id) != "operator":
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer("❌ У вас нет доступа")
        return

    action, row_str = cb.data.split("_")
    row = int(row_str)

    ws = get_spreadsheet().worksheet("appointments")

    # ⛔ БЛОК ПОВТОРНЫХ НАЖАТИЙ
    current_status = ws.cell(row, 9).value
    if current_status != "pending":
        await cb.message.edit_reply_markup(reply_markup=None)
        return

    # ✅ ОБНОВЛЯЕМ СТАТУС (ОДИН ЗАПРОС)
    if action == "approve":
        update_appointment_status(row, "approved")
        mark = "✅ ПРИНЯТО"
        client_text = "✅ <b>Ваша запись подтверждена!</b>\nМы ждём вас 💚"
    else:
        update_appointment_status(row, "rejected")
        mark = "❌ ОТКЛОНЕНО"
        client_text = "❌ <b>Ваша запись отклонена.</b>\nСвяжитесь с нами для подбора другого времени."

    # 📩 получаем user_id клиента (ОДИН ЧТЕНИЕ)
    client_id = int(ws.cell(row, 1).value)

    # уведомляем клиента
    await cb.bot.send_message(
        client_id,
        client_text,
        parse_mode="HTML"
    )

    # ✏️ обновляем сообщение оператору
    await cb.message.edit_text(
        cb.message.text + f"\n\n<b>{mark}</b>",
        parse_mode="HTML"
    )
