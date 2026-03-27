from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def appointment_actions(app_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔁 Перенести",
                    callback_data=f"admin_move:{app_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin_cancel:{app_id}"
                ),
            ]
        ]
    )
