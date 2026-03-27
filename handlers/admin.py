from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from sheets import (
    get_admin_role,
    get_all_appointments_full,
    update_appointment_status,
)

router = Router()


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
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    role = get_admin_role(message.from_user.id)

    if role != "admin":
        await message.answer("⛔ У вас нет доступа")
        return

    await message.answer(
        "🛠 Админ-панель\nВыберите действие:",
        reply_markup=admin_menu()
    )


# =========================
# ALL APPOINTMENTS
# =========================
@router.callback_query(F.data == "admin_all")
async def admin_all(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    apps = get_all_appointments_full()

    if not apps:
        await cb.message.answer("Записей нет")
        await cb.answer()
        return

    for a in apps:
        text = (
            f"🆔 {a['id']}\n"
            f"💆 {a['massage']}\n"
            f"🧑‍⚕️ {a['therapist']}\n"
            f"📅 {a['datetime']}\n"
            f"🧸 {a['child_name']}\n"
            f"📞 {a['phone']}\n"
            f"🏷 Статус: {a['status']}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить",
                        callback_data=f"admin_confirm_{a['id']}"
                    ),
                    InlineKeyboardButton(
                        text="🏁 Завершить",
                        callback_data=f"admin_done_{a['id']}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отменить",
                        callback_data=f"admin_cancel_{a['id']}"
                    )
                ]
            ]
        )

        await cb.message.answer(text, reply_markup=kb)

    await cb.answer()


# =========================
# STATUS ACTIONS
# =========================
@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    app_id = int(cb.data.split("_")[-1])
    update_appointment_status(app_id, "confirmed")

    await cb.message.answer("✅ Запись подтверждена")
    await cb.answer()


@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    app_id = int(cb.data.split("_")[-1])
    update_appointment_status(app_id, "done")

    await cb.message.answer("🏁 Запись завершена")
    await cb.answer()


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    app_id = int(cb.data.split("_")[-1])
    update_appointment_status(app_id, "cancelled")

    await cb.message.answer("❌ Запись отменена")
    await cb.answer()
