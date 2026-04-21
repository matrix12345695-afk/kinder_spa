
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.sheets import get_services, get_dates, get_times, save_to_sheets
import os

router = Router()
user_data = {}

def make_kb(items, prefix):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i, callback_data=f"{prefix}:{i}")]
            for i in items
        ]
    )

@router.message(lambda m: m.text == "📅 Записаться")
async def start_booking(msg: types.Message):
    user_data[msg.from_user.id] = {}
    services = get_services()
    await msg.answer("💆 Выберите услугу:", reply_markup=make_kb(services, "service"))

@router.callback_query(lambda c: c.data.startswith("service:"))
async def choose_service(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data[uid]["service"] = call.data.split(":")[1]

    dates = get_dates()
    await call.message.edit_text("📅 Выберите дату:", reply_markup=make_kb(dates, "date"))

@router.callback_query(lambda c: c.data.startswith("date:"))
async def choose_date(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data[uid]["date"] = call.data.split(":")[1]

    times = get_times()
    await call.message.edit_text("⏰ Выберите время:", reply_markup=make_kb(times, "time"))

@router.callback_query(lambda c: c.data.startswith("time:"))
async def choose_time(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data[uid]["time"] = call.data.split(":")[1]

    data = user_data[uid]

    text = f"""✨ Проверьте запись:

💆 {data['service']}
📅 {data['date']}
⏰ {data['time']}

Введите имя:"""

    await call.message.edit_text(text)

@router.message()
async def finish(msg: types.Message):
    uid = msg.from_user.id
    if uid not in user_data:
        return

    data = user_data[uid]

    if "name" not in data:
        data["name"] = msg.text
        await msg.answer("📞 Введите телефон:")
        return

    if "phone" not in data:
        data["phone"] = msg.text

        save_to_sheets(data)

        text = f"""📥 Новая запись

👶 {data['name']}
📞 {data['phone']}
💆 {data['service']}
📅 {data['date']}
⏰ {data['time']}"""

        from aiogram import Bot
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        await bot.send_message(os.getenv("OPERATOR_ID"), text)

        await msg.answer("✅ Записали! Мы свяжемся с вами 💖")

        del user_data[uid]
