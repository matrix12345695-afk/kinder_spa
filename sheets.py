import json
import gspread
import traceback
import asyncio
import time

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME, BOT_TOKEN

OPERATOR_ID = 8752273443

_spreadsheet = None
_ws_cache = {}
_cache_time = {}
CACHE_TTL = 30

DATA_CACHE = {}
DATA_CACHE_TIME = {}
DATA_TTL = 30


def clear_cache(name=None):
    if name:
        DATA_CACHE.pop(name, None)
        DATA_CACHE_TIME.pop(name, None)
    else:
        DATA_CACHE.clear()
        DATA_CACHE_TIME.clear()


def get_cached_data(name, loader):
    try:
        now = time.time()

        if name in DATA_CACHE:
            if now - DATA_CACHE_TIME[name] < DATA_TTL:
                return DATA_CACHE[name]

        data = loader()

        DATA_CACHE[name] = data
        DATA_CACHE_TIME[name] = now

        return data

    except Exception as e:
        notify_error(e)
        return []


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
    error_text = (
        "🚨 <b>SHEETS ERROR</b>\n\n"
        f"{type(e).__name__}\n"
        f"{str(e)}\n\n"
        f"<pre>{traceback.format_exc()}</pre>"
    )

    print(error_text)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
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
# WORKSHEET CACHE
# =====================================================

def get_ws(name):
    try:
        now = time.time()

        if name in _ws_cache:
            if now - _cache_time[name] < CACHE_TTL:
                return _ws_cache[name]

        ss = get_spreadsheet()
        if not ss:
            return None

        ws = ss.worksheet(name)

        _ws_cache[name] = ws
        _cache_time[name] = now

        return ws

    except Exception as e:
        notify_error(e)
        return None


def safe_get_records(ws):
    for _ in range(3):
        try:
            return ws.get_all_records()
        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
                continue
            notify_error(e)
            return []
    return []


# =====================================================
# HELPERS
# =====================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default


# =====================================================
# USERS
# =====================================================

def get_user_lang(user_id: int):
    try:
        ws = get_ws("users")
        if not ws:
            return "ru"

        for r in safe_get_records(ws):
            if str(r.get("user_id")) == str(user_id):
                return r.get("lang") or "ru"

    except Exception as e:
        notify_error(e)

    return "ru"


def set_user_lang(user_id: int, lang: str):
    try:
        ws = get_ws("users")
        if not ws:
            return

        records = safe_get_records(ws)

        for i, r in enumerate(records, start=2):
            if str(r.get("user_id")) == str(user_id):
                ws.update_cell(i, 2, lang)
                return

        ws.append_row([user_id, lang])

    except Exception as e:
        notify_error(e)


# =====================================================
# ADMIN
# =====================================================

def get_admin_role(user_id: int):
    try:
        ws = get_ws("admins")
        if not ws:
            return None

        for r in safe_get_records(ws):
            if str(r.get("user_id")) == str(user_id):
                return r.get("role")

        return None

    except Exception as e:
        notify_error(e)
        return None


# =====================================================
# MASSAGES
# =====================================================

def get_active_masses(lang="ru"):
    try:
        ws = get_ws("masses")
        if not ws:
            return []

        records = get_cached_data("masses", lambda: safe_get_records(ws))

        return [
            {
                "id": safe_int(r.get("id")),
                "name": r.get("name_ru"),
                "duration": safe_int(r.get("duration_min"), 30),
            }
            for r in records
            if str(r.get("active")).lower() == "true"
        ]

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

        therapists = safe_get_records(ss.worksheet("therapists"))
        links = safe_get_records(ss.worksheet("therapist_masses"))

        result = []

        for l in links:
            if safe_int(l.get("massage_id")) == massage_id:
                for t in therapists:
                    if safe_int(t.get("id")) == safe_int(l.get("therapist_id")):
                        result.append(t)

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# CREATE APPOINTMENT (🔥 ГЛАВНЫЙ ФИКС)
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
    try:
        ws = get_ws("appointments")
        if not ws:
            return None

        row = [
            user_id,
            massage_id,
            therapist_id,
            dt,
            parent_name,
            child_name,
            child_age,
            phone,
            "pending"
        ]

        ws.append_row(row)

        clear_cache("appointments")

        return True

    except Exception as e:
        notify_error(e)
        return None


def update_appointment_status(row: int, new_status: str):
    try:
        ws = get_ws("appointments")
        if not ws:
            return

        ws.update_cell(row, 9, new_status)
        clear_cache("appointments")

    except Exception as e:
        notify_error(e)


# =====================================================
# FREE TIMES (🔥 ИСПРАВЛЕНО)
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ws = get_ws("appointments")
        if not ws:
            return []

        records = safe_get_records(ws)

        start_hour = 9
        end_hour = 18

        slots = []
        current = datetime.strptime(f"{date_str} {start_hour}:00", "%Y-%m-%d %H:%M")

        while current < datetime.strptime(f"{date_str} {end_hour}:00", "%Y-%m-%d %H:%M"):
            slots.append(current)
            current += timedelta(minutes=30)

        busy = []

        for r in records:
            if safe_int(r.get("therapist_id")) != therapist_id:
                continue

            if r.get("status") not in ["pending", "approved"]:
                continue

            dt = r.get("datetime")
            if not dt:
                continue

            try:
                busy_dt = datetime.strptime(dt, "%Y-%m-%d %H:%M")
                if date_str in dt:
                    busy.append(busy_dt)
            except:
                continue

        free = []

        for slot in slots:
            if all(abs((slot - b).total_seconds()) >= duration_min * 60 for b in busy):
                free.append(slot.strftime("%H:%M"))

        return free

    except Exception as e:
        notify_error(e)
        return []
