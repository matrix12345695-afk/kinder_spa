from datetime import datetime, timedelta

WEEKDAY_MAP = {
    "Пн": 0,
    "Вт": 1,
    "Ср": 2,
    "Чт": 3,
    "Пт": 4,
    "Сб": 5,
    "Вс": 6,
}


def get_next_days(days=7):
    today = datetime.now().date()
    return [today + timedelta(days=i) for i in range(days)]
from datetime import datetime


def parse_time(value: str):
    """
    Парсит время из Google Sheets:
    10:00 или 10:00:00
    """
    value = str(value).strip()

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Неверный формат времени: {value}")

