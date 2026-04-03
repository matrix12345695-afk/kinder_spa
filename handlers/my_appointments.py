from aiogram import Router, F
from aiogram.types import Message

from sheets import get_user_lang, get_all_appointments_full, notify_error

router = Router()


@router.message(
    (F.text.contains("Мои записи")) |
    (F.text.contains("Mening yozuvlarim"))
)
async def my_appointments(message: Message):
    try:
        user_id = message.from_user.id
        lang = get_user_lang(user_id) or "ru"

        try:
            appointments = get_all_appointments_full()
        except Exception as e:
            notify_error(e)
            await message.answer("⚠️ Ошибка загрузки записей")
            return

        # =========================================
        # ФИЛЬТРАЦИЯ
        # =========================================
        user_appointments = []

        for a in appointments:
            try:
                if str(a.get("user_id")) == str(user_id):
                    user_appointments.append(a)
            except:
                continue

        # =========================================
        # ЕСЛИ НЕТ ЗАПИСЕЙ
        # =========================================
        if not user_appointments:
            if lang == "uz":
                await message.answer(
                    "📭 <b>Sizda hozircha yozuvlar yo‘q</b>\n\n"
                    "✨ Yangi yozuv yaratish uchun \"Yozilish\" tugmasini bosing",
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
        # ВЫВОД (КАРТОЧКИ)
        # =========================================
        for a in user_appointments:
            try:
                massage = a.get("massage", "—")
                therapist = a.get("therapist", "—")
                dt = a.get("datetime", "—")
                child = a.get("child_name", "—")
                status = a.get("status", "—")

                # 🎯 статус красивый
                if status == "approved":
                    status_text = "✅ Подтверждено"
                elif status == "rejected":
                    status_text = "❌ Отклонено"
                elif status == "pending":
                    status_text = "⏳ Ожидает"
                else:
                    status_text = status

                if lang == "uz":
                    text = (
                        "📅 <b>Yozuv tafsilotlari</b>\n\n"
                        f"💆 <b>Massaj:</b> {massage}\n"
                        f"🧑‍⚕️ <b>Mutaxassis:</b> {therapist}\n"
                        f"⏰ <b>Vaqt:</b> {dt}\n"
                        f"👶 <b>Bola:</b> {child}\n\n"
                        f"📌 <b>Holat:</b> {status_text}"
                    )
                else:
                    text = (
                        "📅 <b>Ваша запись</b>\n\n"
                        f"💆 <b>Массаж:</b> {massage}\n"
                        f"🧑‍⚕️ <b>Специалист:</b> {therapist}\n"
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
