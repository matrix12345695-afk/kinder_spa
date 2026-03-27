from aiogram import Router, F
from aiogram.types import Message

from sheets import get_user_lang, get_all_appointments_full

router = Router()


@router.message(
    (F.text.contains("Мои записи")) |
    (F.text.contains("Mening yozuvlarim"))
)
async def my_appointments(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id) or "ru"

    appointments = get_all_appointments_full(user_id, lang)

    # -------------------------------------------------
    # ЕСЛИ ЗАПИСЕЙ НЕТ
    # -------------------------------------------------
    if not appointments:
        if lang == "uz":
            await message.answer(
                "📭 Sizda hozircha yozuvlar yo‘q."
            )
        else:
            await message.answer(
                "📭 У вас пока нет записей."
            )
        return

    # -------------------------------------------------
    # ВЫВОД ЗАПИСЕЙ
    # -------------------------------------------------
    for a in appointments:
        if lang == "uz":
            text = (
                "📅 <b>Yozuv</b>\n\n"
                f"💆 <b>Massaj:</b> {a['massage']}\n"
                f"🧑‍⚕️ <b>Mutaxassis:</b> {a['therapist']}\n"
                f"⏰ <b>Vaqt:</b> {a['datetime']}\n"
                f"👶 <b>Bola:</b> {a['child']}\n"
                f"📌 <b>Holat:</b> {a['status']}"
            )
        else:
            text = (
                "📅 <b>Запись</b>\n\n"
                f"💆 <b>Массаж:</b> {a['massage']}\n"
                f"🧑‍⚕️ <b>Массажист:</b> {a['therapist']}\n"
                f"⏰ <b>Время:</b> {a['datetime']}\n"
                f"👶 <b>Ребёнок:</b> {a['child']}\n"
                f"📌 <b>Статус:</b> {a['status']}"
            )

        await message.answer(text, parse_mode="HTML")
