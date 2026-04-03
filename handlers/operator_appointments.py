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

        # =========================================
        # 🔥 РАЗБОР CALLBACK (approve_15)
        # =========================================
        try:
            action, row_str = cb.data.split("_")
            row = safe_int(row_str)

            if row <= 1:
                await cb.message.answer("⚠️ Некорректный ID записи")
                return

        except Exception as e:
            notify_error(e)
            await cb.message.answer("⚠️ Ошибка данных")
            return

        # =========================================
        # 📊 ПОЛУЧАЕМ ТАБЛИЦУ
        # =========================================
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

        # =========================================
        # ⛔ ПРОВЕРКА СТАТУСА
        # =========================================
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

        # =========================================
        # 📥 ЧИТАЕМ ДАННЫЕ ЗАПИСИ
        # =========================================
        try:
            record = ws.row_values(row)

            client_id = safe_int(record[0]) if len(record) > 0 else None
            parent_name = record[1] if len(record) > 1 else "—"
            child_name = record[2] if len(record) > 2 else "—"
            age = record[3] if len(record) > 3 else "—"
            phone = record[4] if len(record) > 4 else "—"
            massage_id = safe_int(record[5]) if len(record) > 5 else 0
            therapist_id = safe_int(record[6]) if len(record) > 6 else 0
            dt = record[7] if len(record) > 7 else "—"

        except Exception as e:
            notify_error(e)
            client_id = None
            parent_name = child_name = phone = dt = "—"
            age = "—"
            massage_id = therapist_id = 0

        # =========================================
        # ✅ ОБНОВЛЕНИЕ СТАТУСА
        # =========================================
        try:
            if action == "approve":
                update_appointment_status(row, "approved")
                mark = "✅ ПРИНЯТО"

                client_text = (
                    "✅ <b>Ваша запись подтверждена!</b>\n\n"
                    f"📅 {dt}\n"
                    "Мы ждём вас 💚"
                )

            else:
                update_appointment_status(row, "rejected")
                mark = "❌ ОТКЛОНЕНО"

                client_text = (
                    "❌ <b>Ваша запись отклонена.</b>\n\n"
                    f"📅 {dt}\n"
                    "Свяжитесь с нами для подбора другого времени."
                )

        except Exception as e:
            notify_error(e)
            await cb.message.answer("⚠️ Ошибка обновления статуса")
            return

        # =========================================
        # 📩 ОТПРАВКА КЛИЕНТУ
        # =========================================
        if client_id:
            try:
                await cb.bot.send_message(
                    client_id,
                    client_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                notify_error(e)

        # =========================================
        # ✏️ ОБНОВЛЕНИЕ СООБЩЕНИЯ ОПЕРАТОРА
        # =========================================
        try:
            new_text = (
                cb.message.text +
                f"\n\n<b>{mark}</b>\n"
                f"🆔 Строка: {row}"
            )

            await cb.message.edit_text(
                new_text,
                parse_mode="HTML"
            )
        except:
            pass

    except Exception as e:
        notify_error(e)
        await cb.message.answer("⚠️ Ошибка обработки заявки")
