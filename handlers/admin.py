from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from sheets import (
    get_admin_role,
    update_appointment_status,
    get_spreadsheet,
    get_massage_name,
    get_therapist_name
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
# ADMIN PANEL (ИСПРАВЛЕНО)
# =========================
@router.message(Command("admin"))
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
# ALL APPOINTMENTS (ИСПРАВЛЕНО)
# =========================
@router.callback_query(F.data == "admin_all")
async def admin_all(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    ss = get_spreadsheet()
    if not ss:
        await cb.message.answer("❌ Ошибка подключения к таблице")
        return

    ws = ss.worksheet("appointments")
    rows = ws.get_all_records()

    if not rows:
        await cb.message.answer("Записей нет")
        await cb.answer()
        return

    for idx, r in enumerate(rows, start=2):
        try:
            massage = get_massage_name(int(r.get("massage_id", 0)))
            therapist = get_therapist_name(int(r.get("therapist_id", 0)))

            text = (
                f"🆔 {idx}\n"
                f"💆 {massage}\n"
                f"🧑‍⚕️ {therapist}\n"
                f"📅 {r.get('datetime')}\n"
                f"👩 {r.get('parent_name')}\n"
                f"🧸 {r.get('child_name')}\n"
                f"📊 {r.get('child_age')} мес\n"
                f"📞 {r.get('phone')}\n"
                f"🏷 Статус: {r.get('status')}"
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
            print("ADMIN ERROR:", e)

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

    row = int(cb.data.split("_")[-1])
    update_appointment_status(row, "confirmed")

    await cb.message.answer("✅ Запись подтверждена")
    await cb.answer()


@router.callback_query(F.data.startswith("admin_done_"))
async def admin_done(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    row = int(cb.data.split("_")[-1])
    update_appointment_status(row, "done")

    await cb.message.answer("🏁 Запись завершена")
    await cb.answer()


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(cb: CallbackQuery):
    role = get_admin_role(cb.from_user.id)
    if role != "admin":
        await cb.answer("Нет доступа", show_alert=True)
        return

    row = int(cb.data.split("_")[-1])
    update_appointment_status(row, "cancelled")

    await cb.message.answer("❌ Запись отменена")
    await cb.answer()
