import os
import json
import gspread
import traceback
import asyncio

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME, BOT_TOKEN

OPERATOR_ID = 8752273443

_spreadsheet = None


# =====================================================
# ERROR REPORT
# =====================================================

async def notify_error_async(text):
    try:
        from aiogram import Bot
        bot = Bot(token=BOT_TOKEN)

        if len(text) > 4000:
            text = text[:4000]

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
        asyncio.create_task(notify_error_async(error_text))
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
    global _spreadsheet

    if _spreadsheet:
        return _spreadsheet

    try:
        client = get_client()
        _spreadsheet = client.open_by_key(SPREADSHEET_NAME)
        return _spreadsheet

    except Exception as e:
        notify_error(e)
        return None


# =====================================================
# USERS
# =====================================================

def get_user_lang(user_id: int):
    try:
        ws = get_spreadsheet().worksheet("users")

        for r in ws.get_all_records():
            if str(r.get("user_id")) == str(user_id):
                return r.get("lang")

    except Exception as e:
        notify_error(e)

    return None


# =====================================================
# MASSAGES
# =====================================================

def get_active_masses(lang="ru"):
    try:
        ws = get_spreadsheet().worksheet("masses")

        result = []
        for r in ws.get_all_records():
            if str(r.get("active")).lower() != "true":
                continue

            result.append({
                "id": int(r["id"]),
                "name": r.get("name_ru"),
                "duration": int(r.get("duration_min", 30))
            })

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_massage_name(massage_id: int):
    try:
        ws = get_spreadsheet().worksheet("masses")

        for r in ws.get_all_records():
            if int(r.get("id", 0)) == massage_id:
                return r.get("name_ru")

        return "—"

    except Exception as e:
        notify_error(e)
        return "—"


# =====================================================
# THERAPISTS
# =====================================================

def get_therapists_for_massage(massage_id: int):
    try:
        ss = get_spreadsheet()

        therapists = {}
        for t in ss.worksheet("therapists").get_all_records():
            therapists[int(t["id"])] = t

        result = []

        for l in ss.worksheet("therapist_masses").get_all_records():
            if int(l.get("massage_id", 0)) == massage_id:
                t = therapists.get(int(l.get("therapist_id", 0)))
                if t:
                    result.append(t)

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_therapist_name(therapist_id: int):
    try:
        ws = get_spreadsheet().worksheet("therapists")

        for r in ws.get_all_records():
            if int(r.get("id", 0)) == therapist_id:
                return r.get("name")

        return "—"

    except Exception as e:
        notify_error(e)
        return "—"


# =====================================================
# APPOINTMENTS
# =====================================================

def create_appointment(
    user_id,
    massage_id,
    therapist_id,
    datetime_str,
    parent_name,
    child_name,
    child_age,
    phone
):
    try:
        ws = get_spreadsheet().worksheet("appointments")

        ws.append_row([
            user_id,
            massage_id,
            therapist_id,
            datetime_str,
            parent_name,
            child_name,
            child_age,
            phone,
            "pending"
        ])

        return True

    except Exception as e:
        notify_error(e)
        return None


# =====================================================
# 🔥 ФИКС: FREE TIMES С УЧЁТОМ SCHEDULE
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ss = get_spreadsheet()

        target_date = datetime.strptime(date_str, "%Y-%m-%d")

        weekday_map = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        weekday = weekday_map[target_date.weekday()].lower()

        schedule_ws = ss.worksheet("schedule")

        start_time = None
        end_time = None

        for r in schedule_ws.get_all_records():
            try:
                if int(r.get("therapist_id", 0)) != therapist_id:
                    continue

                excel_day = str(r.get("weekday")).strip().lower()

                if excel_day != weekday:
                    continue

                start_time = str(r.get("time_from")).strip()
                end_time = str(r.get("time_to")).strip()
                break
            except:
                continue

        if not start_time or not end_time:
            return []

        current = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")

        slots = []
        while current < end_dt:
            slots.append(current)
            current += timedelta(minutes=30)

        ws = ss.worksheet("appointments")
        records = ws.get_all_records()

        busy = []

        for r in records:
            try:
                if int(r.get("therapist_id", 0)) != therapist_id:
                    continue

                if r.get("status") == "cancelled":
                    continue

                dt = r.get("datetime")
                if not dt or date_str not in dt:
                    continue

                busy.append(datetime.strptime(dt, "%Y-%m-%d %H:%M"))
            except:
                continue

        free = []

        for slot in slots:
            is_busy = False

            for b in busy:
                if abs((slot - b).total_seconds()) < duration_min * 60:
                    is_busy = True
                    break

            if not is_busy:
                free.append(slot.strftime("%H:%M"))

        return free

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# 📋 СПИСОК ЗАПИСЕЙ
# =====================================================

def get_all_appointments_full(user_id: int, lang="ru"):
    try:
        ws = get_spreadsheet().worksheet("appointments")

        result = []
        for idx, r in enumerate(ws.get_all_records(), start=2):
            if str(r.get("user_id")) == str(user_id):
                result.append({
                    "row": idx,
                    "datetime": r.get("datetime"),
                    "massage": get_massage_name(int(r.get("massage_id", 0))),
                    "therapist": get_therapist_name(int(r.get("therapist_id", 0))),
                    "child": r.get("child_name", ""),
                    "status": r.get("status", ""),
                })

        return result

    except Exception as e:
        notify_error(e)
        return []
