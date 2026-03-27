from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="admin_today"
                ),
                InlineKeyboardButton(
                    text="📆 Завтра",
                    callback_data="admin_tomorrow"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все записи",
                    callback_data="admin_all_appointments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Завершить запись",
                    callback_data="admin_mark_done"
                )
            ],
        ]
    )


def admin_appointments_kb(appointments: list) -> InlineKeyboardMarkup:
    buttons = []

    for a in appointments:
        buttons.append([
            InlineKeyboardButton(
                text=f"{a['child_name']} | {a['datetime']}",
                callback_data=f"admin_done_{a['id']}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
