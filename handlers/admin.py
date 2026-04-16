from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from sheets import (
    get_admin_role,
    update_appointment_status,
    get_all_appointments_full,
    get_massage_name,
    notify_error
)

router = Router()


# =========================
# ADMIN MENU
# =========================
def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все записи", callback_data="admin_all")]
        ]
    )


# =========================
# ADMIN PANEL
# =========================
@router.message(Command("admin"))
async def admin_panel(message: Message):
    try:
        if get_admin_role(message.from_user.id) != "admin":
            await message.answer("⛔ У вас нет доступа")
            return

        await message.answer(
            "🛠 <b>Админ-панель</b>\nВыберите действие:",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        notify_error(e)
        await message.answer("❌ Ошибка")


# =========================
# ВСЕ ЗАПИСИ
# =========================
@router.callback_query(F.data == "admin_all")
async def admin_all(cb: CallbackQuery):
    try:
        await cb.answer()

        if get_admin_role(cb.from_user.id) != "admin":
            await cb.answer("Нет доступа", show_alert=True)
            return

        rows = get_all_appointments_full()

        if not rows:
            await cb.message.answer("📭 Записей нет")
            return

        rows = sorted(
            rows,
            key=lambda x: x.get("datetime", ""),
            reverse=True
        )

        for r in rows[:30]:
            try:
                massage = get_massage_name(int(r.get("massage_id", 0)))
                dt = r.get("datetime", "—")
                parent = r.get("parent_name", "—")
                child = r.get("child_name", "—")
                phone = r.get("phone", "—")
                status = r.get("status", "NEW")

                appointment_id = r.get("appointment_id")

                text = (
                    f"🧾 <b>Запись</b>\n\n"
                    f"💆 <b>Услуга:</b> {massage}\n"
                    f"📅 <b>Дата:</b> {dt}\n"
                    f"👩 <b>Родитель:</b> {parent}\n"
                    f"🧸 <b>Ребёнок:</b> {child}\n"
                    f"📞 <b>Телефон:</b> {phone}\n"
                    f"📌 <b>Статус:</b> {status}"
                )

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Подтвердить",
                                callback_data=f"admin_confirm_{appointment_id}"
                            ),
                            InlineKeyboardButton(
                                text="🏁 Завершить",
                                callback_data=f"admin_done_{appointment_id}"
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="❌ Отменить",
                                callback_data=f"admin_cancel_{appointment_id}"
                            )
                        ]
                    ]
                )

                await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")

            except Exception as e:
                notify_error(e)

    except Exception as e:
        notify_error(e)
        await cb.message.answer("❌ Ошибка")


# =========================
# ОБНОВЛЕНИЕ СТАТУСА (УНИВЕРСАЛ)
# =========================
async def change_status(cb: CallbackQuery, new_status: str, success_text: str):
    try:
        await cb.answer(success_text)

        if get_admin_role(cb.from_user.id) != "admin":
            return

        appointment_id = cb.data.split("_")[-1]

        rows = get_all_appointments_full()

        for index, r in enumerate(rows, start=2):
            if str(r.get("appointment_id")) == str(appointment_id):

                update_appointment_status(index, new_status)

                user_id = int(r.get("user_id", 0))

                # уведомление клиенту
                if user_id:
                    try:
                        messages = {
                            "CONFIRMED": "✅ Ваша запись подтверждена!\nЖдём вас 💚",
                            "DONE": "🏁 Процедура завершена.\nСпасибо за визит 💚",
                            "CANCELLED": "❌ Ваша запись отменена.\nСвяжитесь с нами."
                        }

                        await cb.bot.send_message(user_id, messages.get(new_status, "Статус обновлён"))
                    except Exception as e:
                        notify_error(e)

                try:
                    await cb.message.edit_text(
                        cb.message.text + f"\n\n<b>{new_status}</b>",
                        parse_mode="HTML"
                    )
                except:
                    pass

                return

    except Exception as e:
        notify_error(e)


# =========================
# CALLBACKS
# =========================
@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(cb: CallbackQuery):
    await change_status(cb, "CONFIRMED", "Подтверждено ✅")


@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done(cb: CallbackQuery):
    await change_status(cb, "DONE", "Завершено 🏁")


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(cb: CallbackQuery):
    await change_status(cb, "CANCELLED", "Отменено ❌")
