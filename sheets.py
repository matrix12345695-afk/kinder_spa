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

                if lang == "uz":
                    name = r.get("name_uz") or r.get("name_ru")
                else:
                    name = r.get("name_ru") or r.get("name_uz")

                result.append({
                    "id": int(r.get("id", 0)),
                    "name": name,
                    "price": r.get("price") or r.get("cost") or r.get("цена") or 0,
                    "duration": int(r.get("duration_min", 0)),
                    "age_from": r.get("age_from", ""),
                    "age_to": r.get("age_to", ""),
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
            try:
                if int(r.get("id", 0)) == massage_id:
                    if lang == "uz":
                        return r.get("name_uz") or r.get("name_ru")
                    return r.get("name_ru") or r.get("name_uz")
            except:
                continue

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


def get_therapist_name(therapist_id: int) -> str:
    try:
        ss = get_spreadsheet()
        if not ss:
            return "—"

        ws = ss.worksheet("therapists")

        for r in ws.get_all_records():
            try:
                if int(r.get("id", 0)) == therapist_id:
                    return r.get("name", "—")
            except:
                continue

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


def update_appointment_status(row: int, new_status: str):
    try:
        ss = get_spreadsheet()
        if not ss:
            return

        ws = ss.worksheet("appointments")
        ws.update_cell(row, 9, new_status)

    except Exception as e:
        notify_error(e)


def get_all_appointments_full(user_id: int, lang: str = "ru"):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        ws = ss.worksheet("appointments")

        result = []
        for idx, r in enumerate(ws.get_all_records(), start=2):
            try:
                if str(r.get("user_id")) == str(user_id):
                    result.append({
                        "row": idx,
                        "datetime": r.get("datetime"),
                        "massage": get_massage_name(int(r.get("massage_id", 0)), lang),
                        "therapist": get_therapist_name(int(r.get("therapist_id", 0))),
                        "child": r.get("child_name", ""),
                        "status": r.get("status", ""),
                    })
            except:
                continue

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# FREE TIMES
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        ws = ss.worksheet("appointments")
        records = ws.get_all_records()

        start_hour = 9
        end_hour = 18

        slots = []
        current = datetime.strptime(f"{date_str} {start_hour}:00", "%Y-%m-%d %H:%M")

        while current < datetime.strptime(f"{date_str} {end_hour}:00", "%Y-%m-%d %H:%M"):
            slots.append(current)
            current += timedelta(minutes=30)

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

                busy_time = datetime.strptime(dt, "%Y-%m-%d %H:%M")
                busy.append(busy_time)

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
