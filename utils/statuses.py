STATUS_MAP = {
    "scheduled": "🟢 Запланирована",
    "cancelled": "🔴 Отменена",
    "rescheduled": "🟡 Перенесена",
    "completed": "✅ Завершена"
}


def get_status_ru(status: str) -> str:
    return STATUS_MAP.get(status, status)
