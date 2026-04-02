from aiogram import Router, F
from aiogram.types import Message

from sheets import get_spreadsheet, notify_error

router = Router()


@router.message(
    (F.text.contains("Контакты")) |
    (F.text.contains("Kontaktlar"))
)
async def contacts(message: Message):
    try:
        ss = get_spreadsheet()
        if not ss:
            await message.answer("⚠️ Ошибка загрузки контактов")
            return

        try:
            ws = ss.worksheet("contacts")
        except Exception as e:
            notify_error(e)
            await message.answer("⚠️ Контакты временно недоступны")
            return

        try:
            rows = ws.get_all_records()
        except Exception as e:
            notify_error(e)
            await message.answer("⚠️ Ошибка чтения контактов")
            return

        text_lines = []
        latitude = None
        longitude = None

        for r in rows:
            try:
                title = str(r.get("title", "")).strip()
                value = str(r.get("value", "")).strip()

                if not title or not value:
                    continue

                # -------------------------------
                # ЛОКАЦИЯ
                # -------------------------------
                if title.lower() == "latitude":
                    try:
                        latitude = float(value)
                    except:
                        pass
                    continue

                if title.lower() == "longitude":
                    try:
                        longitude = float(value)
                    except:
                        pass
                    continue

                # -------------------------------
                # ТЕЛЕФОН
                # -------------------------------
                if "телефон" in title.lower() or "phone" in title.lower():
                    clean_phone = value.replace(" ", "").replace("-", "").replace("+", "")
                    text_lines.append(
                        f"{title} <a href=\"tel:+{clean_phone}\">{value}</a>"
                    )
                    continue

                # -------------------------------
                # ОБЫЧНЫЕ СТРОКИ
                # -------------------------------
                text_lines.append(f"{title} {value}")

            except:
                continue

        # -------------------------------
        # 1️⃣ ТЕКСТ
        # -------------------------------
        if text_lines:
            await message.answer(
                "📞 <b>Контакты</b>\n\n" + "\n".join(text_lines),
                parse_mode="HTML"
            )
        else:
            await message.answer("📞 Контакты пока не добавлены")

        # -------------------------------
        # 2️⃣ ЛОКАЦИЯ
        # -------------------------------
        if latitude is not None and longitude is not None:
            try:
                await message.answer_location(
                    latitude=latitude,
                    longitude=longitude
                )
            except:
                pass

    except Exception as e:
        notify_error(e)
        await message.answer("⚠️ Ошибка при загрузке контактов")
