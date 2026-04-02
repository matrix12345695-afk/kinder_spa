from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from sheets import (
    get_admin_role,
    update_appointment_status,
    get_spreadsheet,
    get_massage_name,
    get_therapist_name,
    notify_error
)

router = Router()


def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


# =========================
# ADMIN MENU
# =========================
def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все записи", callback_data="admin_all")],
        ]
    )


# =========================
# ADMIN PANEL
# =========================
@router.message(Command("admin"))
async def admin_panel(message: Message):
    try:
        role = get_admin_role(message.from_user.id)

        if role != "admin":
            await message.answer("⛔ У вас нет доступа")
            return

        await message.answer(
            "🛠 Админ-панель\nВыберите действие:",
            reply_markup=admin_menu()
        )

    except Exception as e:
        notify_error(e)
        await message.answer("❌ Ошибка")


# =========================
# ALL APPOINTMENTS
# =========================
@router.callback_query(F.data == "admin_all")
async def admin_all(cb: CallbackQuery):
    try:
        await cb.answer()

        role = get_admin_role(cb.from_user.id)
        if role != "admin":
            await cb.answer("Нет доступа", show_alert=True)
            return

        ss = get_spreadsheet()
        if not ss:
            await cb.message.answer("❌ Ошибка подключения к таблице")
            return

        try:
            ws = ss.worksheet("appointments")
            rows = ws.get_all_records()
        except Exception as e:
            notify_error(e)
            await cb.message.answer("❌ Ошибка чтения таблицы")
            return

        if not rows:
            await cb.message.answer("Записей нет")
            return

        limit = 30

        for idx, r in enumerate(rows[:limit], start=2):
            try:
                massage = get_massage_name(safe_int(r.get("massage_id")))
                therapist = get_therapist_name(safe_int(r.get("therapist_id")))

                text = (
                    f"🆔 {idx}\n"
                    f"💆 {massage}\n"
                    f"🧑‍⚕️ {therapist}\n"
                    f"📅 {r.get('datetime', '—')}\n"
                    f"👩 {r.get('parent_name', '—')}\n"
                    f"🧸 {r.get('child_name', '—')}\n"
                    f"📊 {r.get('child_age', '—')} мес\n"
                    f"📞 {r.get('phone', '—')}\n"
                    f"🏷 Статус: {r.get('status', '—')}"
                )

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить",
                                callback_data=f"admin_confirm_{idx}"
                            ),
                            InlineKeyboardButton(
                                text="🏁 Завершить",
                                callback_data=f"admin_done_{idx}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"admin_cancel_{idx}"
                            )
                        ]
                    ]
                )

                await cb.message.answer(text, reply_markup=kb)

            except Exception as e:
                notify_error(e)

    except Exception as e:
        notify_error(e)
        await cb.message.answer("❌ Ошибка")


# =========================
# CONFIRM
# =========================
@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(cb: CallbackQuery):
    try:
        await cb.answer("Подтверждено ✅")

        if get_admin_role(cb.from_user.id) != "admin":
            return

        row = safe_int(cb.data.split("_")[-1])

        ss = get_spreadsheet()
        if not ss:
            return

        ws = ss.worksheet("appointments")

        try:
            record = ws.row_values(row)
            user_id = safe_int(record[0])
        except:
            user_id = None

        update_appointment_status(row, "confirmed")

        if user_id:
            try:
                await cb.bot.send_message(
                    user_id,
                    "✅ Ваша запись подтверждена!\nЖдём вас 💚"
                )
            except Exception as e:
                notify_error(e)

        try:
            await cb.message.edit_text(
                cb.message.text + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
                parse_mode="HTML"
            )
        except:
            pass

    except Exception as e:
        notify_error(e)


# =========================
# DONE
# =========================
@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done(cb: CallbackQuery):
    try:
        await cb.answer("Завершено 🏁")

        if get_admin_role(cb.from_user.id) != "admin":
            return

        row = safe_int(cb.data.split("_")[-1])

        ss = get_spreadsheet()
        if not ss:
            return

        ws = ss.worksheet("appointments")

        try:
            record = ws.row_values(row)
            user_id = safe_int(record[0])
        except:
            user_id = None

        update_appointment_status(row, "done")

        if user_id:
            try:
                await cb.bot.send_message(
                    user_id,
                    "🏁 Процедура завершена.\nСпасибо за визит 💚"
                )
            except Exception as e:
                notify_error(e)

        try:
            await cb.message.edit_text(
                cb.message.text + "\n\n🏁 <b>ЗАВЕРШЕНО</b>",
                parse_mode="HTML"
            )
        except:
            pass

    except Exception as e:
        notify_error(e)


# =========================
# CANCEL
# =========================
@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(cb: CallbackQuery):
    try:
        await cb.answer("Отменено ❌")

        if get_admin_role(cb.from_user.id) != "admin":
            return

        row = safe_int(cb.data.split("_")[-1])

        ss = get_spreadsheet()
        if not ss:
            return

        ws = ss.worksheet("appointments")

        try:
            record = ws.row_values(row)
            user_id = safe_int(record[0])
        except:
            user_id = None

        update_appointment_status(row, "cancelled")

        if user_id:
            try:
                await cb.bot.send_message(
                    user_id,
                    "❌ Ваша запись отменена.\nСвяжитесь с нами для уточнения."
                )
            except Exception as e:
                notify_error(e)

        try:
            await cb.message.edit_text(
                cb.message.text + "\n\n❌ <b>ОТМЕНЕНО</b>",
                parse_mode="HTML"
            )
        except:
            pass

    except Exception as e:
        notify_error(e)
