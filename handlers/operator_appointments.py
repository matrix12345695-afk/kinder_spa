from aiogram import Router, F
from aiogram.types import CallbackQuery

from sheets import (
    get_admin_role,
    update_appointment_status,
    get_spreadsheet,
    notify_error
)

router = Router()


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


@router.callback_query(F.data.startswith(("approve_", "reject_")))
async def process_appointment(cb: CallbackQuery):
    try:
        # ⚡ сразу убираем "часики"
        await cb.answer()

        user_id = cb.from_user.id

        # 🔐 проверка роли
        try:
            role = get_admin_role(user_id)
        except Exception as e:
            notify_error(e)
            role = None

        if role != "operator":
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except:
                pass

            await cb.message.answer("❌ У вас нет доступа")
            return

        # 🔥 разбор callback
        try:
            action, row_str = cb.data.split("_")
            row = safe_int(row_str)
        except:
            await cb.message.answer("⚠️ Ошибка данных")
            return

        # 📊 получаем таблицу
        ss = get_spreadsheet()
        if not ss:
            await cb.message.answer("⚠️ Ошибка базы данных")
            return

        try:
            ws = ss.worksheet("appointments")
        except Exception as e:
            notify_error(e)
            await cb.message.answer("⚠️ Ошибка таблицы")
            return

        # ⛔ проверка статуса (анти-дабл клик)
        try:
            current_status = ws.cell(row, 9).value
        except Exception as e:
            notify_error(e)
            await cb.message.answer("⚠️ Ошибка чтения записи")
            return

        if current_status != "pending":
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except:
                pass
            return

        # ✅ обновляем статус
        try:
            if action == "approve":
                update_appointment_status(row, "approved")
                mark = "✅ ПРИНЯТО"
                client_text = "✅ <b>Ваша запись подтверждена!</b>\nМы ждём вас 💚"
            else:
                update_appointment_status(row, "rejected")
                mark = "❌ ОТКЛОНЕНО"
                client_text = "❌ <b>Ваша запись отклонена.</b>\nСвяжитесь с нами для подбора другого времени."
        except Exception as e:
            notify_error(e)
            await cb.message.answer("⚠️ Ошибка обновления статуса")
            return

        # 📩 получаем клиента
        try:
            client_id = safe_int(ws.cell(row, 1).value)
        except Exception as e:
            notify_error(e)
            client_id = None

        # 📩 отправка клиенту
        if client_id:
            try:
                await cb.bot.send_message(
                    client_id,
                    client_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                notify_error(e)

        # ✏️ обновляем сообщение оператору
        try:
            await cb.message.edit_text(
                cb.message.text + f"\n\n<b>{mark}</b>",
                parse_mode="HTML"
            )
        except:
            pass

    except Exception as e:
        notify_error(e)
        await cb.message.answer("⚠️ Ошибка обработки заявки")
