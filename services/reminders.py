import asyncio, datetime
from services.sheets import get_ws

async def start_reminder_loop(bot):
    while True:
        try:
            ws = get_ws()
            if ws:
                rows = ws.get_all_values()[1:]
                now = datetime.datetime.utcnow()
                for i, r in enumerate(rows, start=2):
                    try:
                        # date DD.MM and time HH:MM
                        dt = datetime.datetime.strptime(r[3]+" "+r[4], "%d.%m %H:%M")
                        # naive: treat as today/year
                        dt = dt.replace(year=now.year)
                        if 0 < (dt - now).total_seconds() < 3600:
                            user_id = int(r[0])
                            await bot.send_message(user_id, f"Напоминание: запись в {r[4]} ({r[3]})")
                    except:
                        pass
        except:
            pass
        await asyncio.sleep(300)
