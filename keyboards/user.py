from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from datetime import datetime, timedelta


# =========================
# MAIN MENU
# =========================
def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="😺 Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
            [KeyboardButton(text="📞 Контакты")]
        ],
        resize_keyboard=True
    )


# =========================
# MASSAGES
# =========================
def massages_kb(masses: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=m["name"],
                callback_data=f"massage_{m['id']}"
            )]
            for m in masses
        ]
    )


# =========================
# THERAPISTS
# =========================
def therapists_kb(therapists: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t["name"],
                callback_data=f"therapist_{t['id']}"
            )]
            for t in therapists
        ]
    )


# =========================
# DATES (14 дней вперёд)
# =========================
def dates_kb(days: int = 14) -> InlineKeyboardMarkup:
    today = datetime.now().date()
    buttons = []

    for i in range(days):
        d = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(
                text=d.strftime("%d.%m.%Y"),
                callback_data=f"date_{d.isoformat()}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# TIMES
# =========================
def times_kb(times: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t,
                callback_data=f"time_{t}"
            )]
            for t in times
        ]
    )


# =========================
# BACK
# =========================
def back_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=action
            )]
        ]
    )
