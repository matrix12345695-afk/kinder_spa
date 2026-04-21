from aiogram import Router, F
from aiogram.types import CallbackQuery
import asyncio

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


async def run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


@router.callback_query(F.data.startswith(("approve_", "reject_")))
async def process_appointment(cb: CallbackQuery):
    await cb.answer()

    print("🔥 CALLBACK RECEIVED:", cb.data)

    try:
        user_id = cb.from_user.id

        # 🔐 ПРОВЕРКА РОЛИ
        try:
            role = await run_blocking(get_admin_role, user_id)
            print("👤 ROLE:", role)
        except Exception as e:
            await notify_error(e)
            role = None

        if role != "operator":
            await cb.message.answer("❌ У вас нет доступа")
            return

        # 🔍 РАЗБОР CALLBACK
        try:
            action, row_str = cb.data.split("_")
            row = safe_int(row_str)

            print("📌 ACTION:", action, "ROW:", row)

            if row <= 1:
                await cb.message.answer("⚠️ Некорректный ID")
                return

        except Exception as e:
            await notify_error(e)
            await cb.message.answer("⚠️ Ошибка данных")
            return

        # 📊 ТАБЛИЦА
        try:
            ss = await run_blocking(get_spreadsheet)
            ws = await asyncio.to_thread(ss.worksheet, "appointments")
        except Exception as e:
            await notify_error(e)
            await cb.message.answer("⚠️ Ошибка базы")
            return

        # ⛔ СТАТУС
        try:
            current_status = await asyncio.to_thread(lambda: ws.cell(row, 9).value)
            print("📊 STATUS:", current_status)
        except Exception as e:
            await notify_error(e)
            await cb.message.answer("⚠️ Ошибка чтения")
            return

        if current_status != "NEW":
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.answer("⚠️ Уже обработано")
            return

        # 📥 ДАННЫЕ
        try:
            record = await asyncio.to_thread(ws.row_values, row)

            print("📦 RECORD:", record)

            client_id = safe_int(record[0]) if len(record) > 0 else None
            dt = record[3] if len(record) > 3 else "—"
            parent_name = record[4] if len(record) > 4 else "—"
            child_name = record[5] if len(record) > 5 else "—"
            phone = record[7] if len(record) > 7 else "—"

        except Exception as e:
            await notify_error(e)
            await cb.message.answer("⚠️ Ошибка данных")
            return

        # 🔄 СТАТУС
        try:
            if action == "approve":
                await run_blocking(update_appointment_status, row, "CONFIRMED")
                mark = "✅ ПРИНЯТО"

                client_text = (
                    "✅ <b>Запись подтверждена!</b>\n\n"
                    f"📅 {dt}\n"
                    "Ждём вас 💚"
                )

            else:
                await run_blocking(update_appointment_status, row, "CANCELLED")
                mark = "❌ ОТКЛОНЕНО"

                client_text = (
                    "❌ <b>Запись отклонена</b>\n\n"
                    f"📅 {dt}\n"
                    "Напишите нам для нового времени"
                )

        except Exception as e:
            await notify_error(e)
            await cb.message.answer("⚠️ Ошибка обновления")
            return

        # 📩 КЛИЕНТУ
        if client_id and client_id > 0:
            try:
                await cb.bot.send_message(client_id, client_text, parse_mode="HTML")
                print("📩 CLIENT NOTIFIED:", client_id)
            except Exception as e:
                await notify_error(e)

        # 🧹 КНОПКИ
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except:
            pass

        # ✏️ ОБНОВЛЕНИЕ ТЕКСТА
        try:
            new_text = (
                (cb.message.text or "") +
                f"\n\n<b>{mark}</b>\n"
                f"👤 {parent_name} / {child_name}\n"
                f"📞 {phone}\n"
                f"🆔 {row}"
            )

            await cb.message.edit_text(new_text, parse_mode="HTML")

        except Exception as e:
            await notify_error(e)

    except Exception as e:
        await notify_error(e)
        await cb.message.answer("⚠️ Ошибка обработки")
