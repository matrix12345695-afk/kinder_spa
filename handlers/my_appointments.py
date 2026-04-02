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

        # 🔥 фильтрация по пользователю (ВАЖНО)
        user_appointments = []

        for a in appointments:
            try:
                if str(a.get("user_id")) == str(user_id):
                    user_appointments.append(a)
            except:
                continue

        # -------------------------------------------------
        # ЕСЛИ ЗАПИСЕЙ НЕТ
        # -------------------------------------------------
        if not user_appointments:
            if lang == "uz":
                await message.answer("📭 Sizda hozircha yozuvlar yo‘q.")
            else:
                await message.answer("📭 У вас пока нет записей.")
            return

        # -------------------------------------------------
        # ВЫВОД
        # -------------------------------------------------
        for a in user_appointments:
            try:
                massage = a.get("massage", "—")
                therapist = a.get("therapist", "—")
                dt = a.get("datetime", "—")
                child = a.get("child_name", "—")
                status = a.get("status", "—")

                if lang == "uz":
                    text = (
                        "📅 <b>Yozuv</b>\n\n"
                        f"💆 <b>Massaj:</b> {massage}\n"
                        f"🧑‍⚕️ <b>Mutaxassis:</b> {therapist}\n"
                        f"⏰ <b>Vaqt:</b> {dt}\n"
                        f"👶 <b>Bola:</b> {child}\n"
                        f"📌 <b>Holat:</b> {status}"
                    )
                else:
                    text = (
                        "📅 <b>Запись</b>\n\n"
                        f"💆 <b>Массаж:</b> {massage}\n"
                        f"🧑‍⚕️ <b>Массажист:</b> {therapist}\n"
                        f"⏰ <b>Время:</b> {dt}\n"
                        f"👶 <b>Ребёнок:</b> {child}\n"
                        f"📌 <b>Статус:</b> {status}"
                    )

                await message.answer(text, parse_mode="HTML")

            except:
                continue

    except Exception as e:
        notify_error(e)
        await message.answer("⚠️ Ошибка при получении записей")
