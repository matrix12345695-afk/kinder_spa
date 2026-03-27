import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.sheets import _records
from config import REMINDER_CHECK_INTERVAL_SECONDS, REMINDER_BEFORE_MINUTES, TIMEZONE

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


def start_scheduler(bot):
    """
    Запуск планировщика напоминаний
    """
    scheduler.add_job(
        send_reminders,
        trigger=IntervalTrigger(seconds=REMINDER_CHECK_INTERVAL_SECONDS),
        args=[bot],
        id="send_reminders",
        replace_existing=True,
    )
    scheduler.start()


async def send_reminders(bot):
    """
    Проверяем записи и отправляем напоминания
    """
    now = datetime.now()
    remind_delta = timedelta(minutes=REMINDER_BEFORE_MINUTES)

    appointments = _records("appointments")

    for i, a in enumerate(appointments, start=2):
        try:
            if str(a.get("status")) != "scheduled":
                continue

            dt_str = a.get("datetime")
            if not dt_str:
                continue

            visit_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

            # если время напоминания ещё не наступило
            if not (visit_time - remind_delta <= now < visit_time):
                continue

            # если уже напоминали
            if str(a.get("reminded")).upper() == "TRUE":
                continue

            user_id = int(a.get("user_id"))
            massage_id = int(a.get("massage_id"))
            therapist_id = int(a.get("therapist_id"))

            await bot.send_message(
                user_id,
                (
                    "⏰ <b>Напоминание</b>\n\n"
                    f"Сегодня у вас массаж 🧸\n"
                    f"📅 {dt_str}\n\n"
                    "Ждём вас 💆‍♂️"
                ),
            )

            # помечаем как напомненное
            try:
                ws = bot  # заглушка для совместимости
            except Exception:
                pass

            # обновление флага reminded
            from services.sheets import _ws
            sheet = _ws("appointments")
            if sheet:
                sheet.update_cell(i, 7, "TRUE")

        except Exception as e:
            logger.error(f"Reminder error: {e}")
