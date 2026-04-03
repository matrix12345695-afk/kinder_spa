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

                title_lower = title.lower()

                # =========================================
                # 📍 ЛОКАЦИЯ
                # =========================================
                if title_lower == "latitude":
                    try:
                        latitude = float(value)
                    except:
                        pass
                    continue

                if title_lower == "longitude":
                    try:
                        longitude = float(value)
                    except:
                        pass
                    continue

                # =========================================
                # 📞 ТЕЛЕФОН (КЛИКАБЕЛЬНЫЙ)
                # =========================================
                if "телефон" in title_lower or "phone" in title_lower:
                    clean_phone = value.replace(" ", "").replace("-", "").replace("+", "")
                    text_lines.append(
                        f"📞 <b>{title}:</b> <a href=\"tel:+{clean_phone}\">{value}</a>"
                    )
                    continue

                # =========================================
                # 📍 АДРЕС
                # =========================================
                if "адрес" in title_lower or "manzil" in title_lower:
                    text_lines.append(f"📍 <b>{title}:</b> {value}")
                    continue

                # =========================================
                # ⏰ РЕЖИМ РАБОТЫ
                # =========================================
                if "время" in title_lower or "hours" in title_lower:
                    text_lines.append(f"⏰ <b>{title}:</b> {value}")
                    continue

                # =========================================
                # 💬 ОСТАЛЬНОЕ
                # =========================================
                text_lines.append(f"ℹ️ <b>{title}:</b> {value}")

            except:
                continue

        # =========================================
        # 📄 ТЕКСТ
        # =========================================
        if text_lines:
            text = (
                "📞 <b>Контакты Kinder Spa</b>\n\n"
                "✨ Мы всегда на связи\n\n"
                + "\n".join(text_lines)
            )

            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("📞 Контакты пока не добавлены")

        # =========================================
        # 📍 КАРТА
        # =========================================
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
