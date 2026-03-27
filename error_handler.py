from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram import Bot
import traceback
import asyncio

OPERATOR_ID = 502438855  # ← вставь свой ID


class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)

        except Exception as e:
            bot: Bot = data.get("bot")

            error_text = (
                "🚨 <b>Ошибка в боте</b>\n\n"
                f"<b>Тип:</b> {type(e).__name__}\n"
                f"<b>Ошибка:</b> {str(e)}\n\n"
                f"<pre>{traceback.format_exc()}</pre>"
            )

            # отправка оператору
            try:
                await bot.send_message(OPERATOR_ID, error_text, parse_mode="HTML")
            except:
                pass

            # ответ пользователю
            try:
                if isinstance(event, Message):
                    await event.answer("⚠️ Что-то пошло не так, попробуйте ещё раз")

                elif isinstance(event, CallbackQuery):
                    await event.answer("Ошибка, попробуйте позже", show_alert=True)

            except:
                pass

            # НЕ даём боту упасть
            return None
