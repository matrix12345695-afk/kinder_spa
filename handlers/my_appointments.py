from aiogram import Router, F
from aiogram.types import Message

from sheets import (
    get_user_lang,
    get_user_appointments,
    get_massage_name,
    notify_error
)

router = Router()


# =====================================================
# МОИ ЗАПИСИ (ПОЛНЫЙ UX)
# =====================================================

@router.message(
    (F.text.contains("Мои записи")) |
    (F.text.contains("Mening yozuvlarim"))
)
async def my_appointments(message: Message):
    try:
        user_id = message.from_user.id
        lang = get_user_lang(user_id) or "ru"

        appointments = get_user_appointments(user_id)

        # =========================================
        # НЕТ ЗАПИСЕЙ
        # =========================================
        if not appointments:
            if lang == "uz":
                await message.answer(
                    "📭 <b>Sizda hali yozuvlar yo‘q</b>\n\n"
                    "✨ \"Yozilish\" tugmasi orqali birinchi yozuvingizni yarating",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "📭 <b>У вас пока нет записей</b>\n\n"
                    "✨ Нажмите «Записаться», чтобы создать первую запись",
                    parse_mode="HTML"
                )
            return

        # =========================================
        # СОРТИРОВКА (свежие сверху)
        # =========================================
        appointments = sorted(
            appointments,
            key=lambda x: x.get("datetime", ""),
            reverse=True
        )

        # =========================================
        # ВЫВОД
        # =========================================
        for a in appointments:
            try:
                massage_name = get_massage_name(int(a.get("massage_id", 0)))
                dt = a.get("datetime", "—")
                child = a.get("child_name", "—")
                status = a.get("status", "NEW")

                # 🎯 красивый статус
                status_map = {
                    "NEW": "⏳ В ожидании",
                    "CONFIRMED": "✅ Подтверждено",
                    "DONE": "🎉 Завершено",
                    "CANCELLED": "❌ Отменено"
                }

                status_text = status_map.get(status, status)

                if lang == "uz":
                    text = (
                        "🧾 <b>Yozuv</b>\n\n"
                        f"💆 <b>Xizmat:</b> {massage_name}\n"
                        f"⏰ <b>Vaqt:</b> {dt}\n"
                        f"👶 <b>Bola:</b> {child}\n\n"
                        f"📌 <b>Holat:</b> {status_text}"
                    )
                else:
                    text = (
                        "🧾 <b>Ваша запись</b>\n\n"
                        f"💆 <b>Услуга:</b> {massage_name}\n"
                        f"⏰ <b>Дата и время:</b> {dt}\n"
                        f"👶 <b>Ребёнок:</b> {child}\n\n"
                        f"📌 <b>Статус:</b> {status_text}"
                    )

                await message.answer(text, parse_mode="HTML")

            except Exception as e:
                notify_error(e)
                continue

    except Exception as e:
        notify_error(e)
        await message.answer("⚠️ Ошибка при получении записей")
