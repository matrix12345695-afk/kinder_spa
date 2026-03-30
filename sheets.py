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
    global _spreadsheet

    if _spreadsheet:
        return _spreadsheet

    try:
        client = get_client()
        if not client:
            return None

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
# ADMINS
# =====================================================

def get_admin_role(user_id: int):
    try:
        ss = get_spreadsheet()
        if not ss:
            return None

        ws = ss.worksheet("admins")

        for r in ws.get_all_records():
            if str(r.get("user_id")) == str(user_id):
                return r.get("role")

    except Exception as e:
        notify_error(e)

    return None


# =====================================================
# CONTACTS
# =====================================================

def get_contacts():
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        ws = ss.worksheet("contacts")

        result = []
        for r in ws.get_all_records():
            line = " ".join(str(v) for v in r.values() if v)
            if line.strip():
                result.append(line)

        return result

    except Exception as e:
        notify_error(e)
        return []


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
                if str(r.get("active", "")).lower() != "true":
                    continue

                name = r.get("name_ru") or r.get("name_uz")

                result.append({
                    "id": int(r.get("id", 0)),
                    "name": name,
                    "price": r.get("price", 0),
                    "duration": int(r.get("duration_min", 30)),
                })
            except:
                continue

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_massage_name(massage_id: int, lang: str = "ru") -> str:
    try:
        ss = get_spreadsheet()
        if not ss:
            return "—"

        ws = ss.worksheet("masses")

        for r in ws.get_all_records():
            if int(r.get("id", 0)) == massage_id:
                return r.get("name_ru") or r.get("name_uz")

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
        if not ss:
            return []

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


def get_therapist_name(therapist_id: int) -> str:
    try:
        ss = get_spreadsheet()
        if not ss:
            return "—"

        ws = ss.worksheet("therapists")

        for r in ws.get_all_records():
            if int(r.get("id", 0)) == therapist_id:
                return r.get("name", "—")

        return "—"

    except Exception as e:
        notify_error(e)
        return "—"


# =====================================================
# APPOINTMENTS
# =====================================================

def create_appointment(
    user_id: int,
    massage_id: int,
    therapist_id: int,
    datetime_str: str,
    parent_name: str,
    child_name: str,
    child_age: int,
    phone: str,
):
    try:
        ss = get_spreadsheet()
        if not ss:
            return None

        ws = ss.worksheet("appointments")

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
# 🔥 FIXED FREE TIMES (С УЧЁТОМ SCHEDULE)
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        weekday_map = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
        weekday = weekday_map[target_date.weekday()]

        # 📅 график
        schedule_ws = ss.worksheet("schedule")

        start_time = None
        end_time = None

        for r in schedule_ws.get_all_records():
            if int(r.get("therapist_id", 0)) != therapist_id:
                continue

            if str(r.get("weekday")).strip() != weekday:
                continue

            start_time = r.get("time_from")
            end_time = r.get("time_to")
            break

        if not start_time or not end_time:
            return []

        # ⏰ слоты
        current = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")

        slots = []
        while current < end_dt:
            slots.append(current)
            current += timedelta(minutes=30)

        # 📕 занятые
        ws = ss.worksheet("appointments")
        records = ws.get_all_records()

        busy = []

        for r in records:
            if int(r.get("therapist_id", 0)) != therapist_id:
                continue

            if r.get("status") == "cancelled":
                continue

            dt = r.get("datetime")
            if not dt or date_str not in dt:
                continue

            busy.append(datetime.strptime(dt, "%Y-%m-%d %H:%M"))

        # 🧠 фильтр
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
