from aiogram import Router, F
from aiogram.types import Message

from sheets import get_spreadsheet

router = Router()


@router.message(
    (F.text.contains("Контакты")) |
    (F.text.contains("Kontaktlar"))
)
async def contacts(message: Message):
    ws = get_spreadsheet().worksheet("contacts")
    rows = ws.get_all_records()

    text_lines = []
    latitude = None
    longitude = None

    for r in rows:
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
        # КЛИКАБЕЛЬНЫЙ ТЕЛЕФОН
        # -------------------------------
        if "телефон" in title.lower():
            clean_phone = value.replace(" ", "").replace("-", "")
            text_lines.append(
                f"{title} <a href=\"tel:{clean_phone}\">{value}</a>"
            )
            continue

        # -------------------------------
        # ОБЫЧНЫЕ СТРОКИ
        # -------------------------------
        text_lines.append(f"{title} {value}")

    # -------------------------------
    # 1️⃣ ОТПРАВЛЯЕМ ТЕКСТ
    # -------------------------------
    if text_lines:
        await message.answer(
            "📞 <b>Контакты</b>\n\n" + "\n".join(text_lines),
            parse_mode="HTML"
        )

    # -------------------------------
    # 2️⃣ ОТПРАВЛЯЕМ ЛОКАЦИЮ
    # -------------------------------
    if latitude is not None and longitude is not None:
        await message.answer_location(
            latitude=latitude,
            longitude=longitude
        )
