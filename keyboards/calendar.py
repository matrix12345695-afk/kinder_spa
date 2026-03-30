import calendar
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_calendar(year: int, month: int):
    kb = InlineKeyboardMarkup(row_width=7)

    # Заголовок
    kb.row(
        InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}",
            callback_data="ignore"
        )
    )

    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    kb.row(*[InlineKeyboardButton(text=d, callback_data="ignore") for d in days])

    cal = calendar.monthcalendar(year, month)

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month}-{day}"

                # 🔒 пример блокировки (воскресенье)
                weekday = datetime(year, month, day).weekday()
                if weekday == 6:
                    row.append(
                        InlineKeyboardButton(
                            text=f"{day} 🔒",
                            callback_data="ignore"
                        )
                    )
                else:
                    row.append(
                        InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"date_{date_str}"
                        )
                    )
        kb.row(*row)

    # Кнопки перелистывания
    kb.row(
        InlineKeyboardButton(text="<", callback_data=f"prev_{year}_{month}"),
        InlineKeyboardButton(text=">", callback_data=f"next_{year}_{month}")
    )

    return kb
