from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

from sheets import get_appointments_for_reminder


scheduler = AsyncIOScheduler()


async def send_reminders(bot):
    # ⏰ за 24 часа
    for r in get_appointments_for_reminder(24 * 60):
        await bot.send_message(
            r["user_id"],
            f"⏰ Напоминание!\n\n"
            f"У вас запись на массаж завтра:\n"
            f"📅 {r['datetime']}"
        )

    # ⏰ за 2 часа
    for r in get_appointments_for_reminder(2 * 60):
        await bot.send_message(
            r["user_id"],
            f"⏰ Напоминание!\n\n"
            f"У вас запись на массаж через 2 часа:\n"
            f"📅 {r['datetime']}"
        )


def start_scheduler(bot):
    # каждые 5 минут проверяем
    scheduler.add_job(
        send_reminders,
        trigger="interval",
        minutes=5,
        args=[bot],
        id="send_reminders",
        replace_existing=True,
    )

    scheduler.start()
