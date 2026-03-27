import os
import json
import gspread
import traceback
import asyncio

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME

# 👇 ВСТАВЬ СВОЙ ID
OPERATOR_ID = 502438855

# =====================================================
# 🔥 ERROR REPORT
# =====================================================

async def notify_error_async(text):
    try:
        from aiogram import Bot
        from config import BOT_TOKEN

        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(OPERATOR_ID, text, parse_mode="HTML")
    except:
        pass


def notify_error(e: Exception):
    error_text = (
        "🚨 <b>SHEETS ERROR</b>\n\n"
        f"<b>Тип:</b> {type(e).__name__}\n"
        f"<b>Ошибка:</b> {str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(notify_error_async(error_text))
    except:
        pass


# =====================================================
# AUTH
# =====================================================

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_client():
    try:
        if not GOOGLE_CREDENTIALS:
            raise ValueError("GOOGLE_CREDENTIALS пуст")

        creds_dict = json.loads(GOOGLE_CREDENTIALS)

        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPE
        )

        return gspread.authorize(creds)

    except Exception as e:
        notify_error(e)
        return None


def get_spreadsheet():
    try:
        client = get_client()
        if not client:
            return None

        return client.open_by_key(SPREADSHEET_NAME)

    except Exception as e:
        notify_error(e)
        return None


# =====================================================
# USERS
# =====================================================

def get_user_lang(user_id: int):
    try:
        ss = get_spreadsheet()
        if not ss:
            return None

        ws = ss.worksheet("users")

        for r in ws.get_all_records():
            if str(r.get("user_id")) == str(user_id):
                return r.get("lang")

    except Exception as e:
        notify_error(e)

    return None


def set_user_lang(user_id: int, lang: str):
    try:
        ss = get_spreadsheet()
        if not ss:
            return

        ws = ss.worksheet("users")
        rows = ws.get_all_records()

        for i, r in enumerate(rows, start=2):
            if str(r.get("user_id")) == str(user_id):
                ws.update_cell(i, 2, lang)
                return

        ws.append_row([user_id, lang])

    except Exception as e:
        notify_error(e)


# =====================================================
# MASSAGES
# =====================================================

def get_active_masses(lang: str = "ru"):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        ws = ss.worksheet("masses")

        result = []
        for r in ws.get_all_records():
            try:
                if str(r.get("active", "")).upper() != "TRUE":
                    continue

                result.append({
                    "id": int(r.get("id", 0)),
                    "name": r.get("name_ru") if lang == "ru" else r.get("name_uz"),
                    "price": r.get("price") or 0,
                    "duration": int(r.get("duration_min", 0)),
                })
            except:
                continue

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# THERAPISTS
# =====================================================

def get_therapists_for_massage(massage_id: int):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        therapists = {}
        for t in ss.worksheet("therapists").get_all_records():
            try:
                therapists[int(t["id"])] = t
            except:
                continue

        result = []

        for l in ss.worksheet("therapist_masses").get_all_records():
            try:
                if int(l.get("massage_id", 0)) == massage_id:
                    t = therapists.get(int(l.get("therapist_id", 0)))
                    if t:
                        result.append(t)
            except:
                continue

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# FREE TIME
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        schedule_ws = ss.worksheet("schedule")
        appointments_ws = ss.worksheet("appointments")

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        busy = []
        for r in appointments_ws.get_all_records():
            try:
                if int(r.get("therapist_id", 0)) == therapist_id:
                    dt = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")
                    if dt.date() == date_obj:
                        busy.append(dt)
            except:
                continue

        return ["10:00", "11:00", "12:00"]  # fallback если всё сломалось

    except Exception as e:
        notify_error(e)
        return ["10:00", "11:00"]
