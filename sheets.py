import json
import gspread
import traceback
import asyncio
import time
import uuid

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME, BOT_TOKEN

OPERATOR_ID = 8752273443

_spreadsheet = None

CACHE = {}
CACHE_TIME = {}
CACHE_TTL = 20


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
        await bot.session.close()
    except:
        pass


def notify_error(e: Exception):
    text = (
        "🚨 <b>SHEETS ERROR</b>\n\n"
        f"{type(e).__name__}\n{str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )
    print(text)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(notify_error_async(text))
    except:
        pass


# =====================================================
# AUTH
# =====================================================

def get_client():
    creds_dict = json.loads(GOOGLE_CREDENTIALS)

    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

    return gspread.authorize(creds)


def get_spreadsheet():
    global _spreadsheet

    if _spreadsheet:
        return _spreadsheet

    client = get_client()
    _spreadsheet = client.open_by_key(SPREADSHEET_NAME)
    return _spreadsheet


def get_ws(name):
    return get_spreadsheet().worksheet(name)


def get_records(name):
    now = time.time()

    if name in CACHE and now - CACHE_TIME[name] < CACHE_TTL:
        return CACHE[name]

    ws = get_ws(name)
    data = ws.get_all_records()

    CACHE[name] = data
    CACHE_TIME[name] = now

    return data


def clear_cache(name=None):
    if name:
        CACHE.pop(name, None)
        CACHE_TIME.pop(name, None)
    else:
        CACHE.clear()
        CACHE_TIME.clear()


# =====================================================
# USERS
# =====================================================

def get_user_lang(user_id: int):
    for r in get_records("users"):
        if str(r.get("user_id")) == str(user_id):
            return r.get("lang") or "ru"
    return "ru"


def set_user_lang(user_id: int, lang: str):
    try:
        ws = get_ws("users")
        records = get_records("users")

        for i, r in enumerate(records, start=2):
            if str(r.get("user_id")) == str(user_id):
                ws.update_cell(i, 2, lang)
                return

        ws.append_row([user_id, lang])
        clear_cache("users")

    except Exception as e:
        notify_error(e)


# =====================================================
# ADMINS (🔥 ДОБАВЛЕНО)
# =====================================================

def get_admin_role(user_id: int):
    try:
        for r in get_records("admins"):
            if str(r.get("user_id")) == str(user_id):
                return r.get("role")
        return None
    except Exception as e:
        notify_error(e)
        return None


# =====================================================
# MASSES
# =====================================================

def get_active_masses(lang=None):
    try:
        result = []

        for r in get_records("masses"):
            if str(r.get("active")).lower() != "true":
                continue

            result.append({
                "id": int(r.get("id", 0)),
                "name": r.get("name_ru") if lang != "uz" else r.get("name_uz"),
                "price": int(r.get("price", 0)),
                "duration": int(r.get("duration_min", 30)),
                "age_from": r.get("age_from"),
                "age_to": r.get("age_to"),
            })

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_massage_name(massage_id: int):
    for r in get_records("masses"):
        if int(r.get("id", 0)) == massage_id:
            return r.get("name_ru")
    return "Неизвестно"


# =====================================================
# THERAPISTS
# =====================================================

def get_therapists_for_massage(massage_id: int):
    try:
        ss = get_spreadsheet()

        therapists = ss.worksheet("therapists").get_all_records()
        links = ss.worksheet("therapist_masses").get_all_records()

        result = []

        for link in links:
            if int(link.get("massage_id", 0)) == massage_id:
                for t in therapists:
                    if int(t.get("id", 0)) == int(link.get("therapist_id", 0)):
                        result.append(t)

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# APPOINTMENTS
# =====================================================

def create_appointment(
    user_id,
    parent_name,
    child_name,
    child_age,
    phone,
    massage_id,
    therapist_id,
    dt
):
    ws = get_ws("appointments")

    appointment_id = str(uuid.uuid4())[:8]

    row = [
        appointment_id,
        user_id,
        massage_id,
        therapist_id,
        dt,
        parent_name,
        child_name,
        child_age,
        phone,
        "NEW",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ]

    ws.append_row(row)
    clear_cache("appointments")

    return True


def get_all_appointments_full():
    return get_records("appointments")


def get_user_appointments(user_id: int):
    return [
        r for r in get_records("appointments")
        if str(r.get("user_id")) == str(user_id)
    ]


def update_appointment_status(row: int, status: str):
    ws = get_ws("appointments")
    ws.update_cell(row, 10, status)
    clear_cache("appointments")


# =====================================================
# FREE TIMES
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration=30):
    records = get_records("appointments")

    start = datetime.strptime(date_str + " 09:00", "%Y-%m-%d %H:%M")
    end = datetime.strptime(date_str + " 18:00", "%Y-%m-%d %H:%M")

    slots = []
    current = start

    while current < end:
        slots.append(current)
        current += timedelta(minutes=30)

    busy = []

    for r in records:
        if int(r.get("therapist_id", 0)) != therapist_id:
            continue

        if r.get("status") not in ["NEW", "CONFIRMED"]:
            continue

        try:
            dt = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")
            busy.append(dt)
        except:
            continue

    free = []

    for slot in slots:
        if all(abs((slot - b).total_seconds()) >= duration * 60 for b in busy):
            free.append(slot.strftime("%H:%M"))

    return free
