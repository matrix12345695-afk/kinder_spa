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

# 🔥 ДОБАВЛЕН КЭШ ДАННЫХ (НИЧЕГО НЕ УДАЛЕНО)
DATA_CACHE = {}
DATA_CACHE_TIME = {}
DATA_TTL = 30


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
# HEALTH CHECK
# =====================================================

def health_check():
    try:
        ss = get_spreadsheet()
        if not ss:
            return False

        required = ["users", "masses", "therapists", "appointments"]

        for name in required:
            ss.worksheet(name)

        return True

    except Exception as e:
        notify_error(e)
        return False


# =====================================================
# SAFE WORKSHEET + CACHE 🔥
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
# ADMIN ROLE
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
# MASSAGES (🔥 УСКОРЕНО)
# =====================================================

def get_active_masses(lang="ru"):
    try:
        ws = get_ws("masses")
        if not ws:
            return []

        records = get_cached_data("masses", lambda: safe_get_records(ws))

        result = []

        for r in records:
            if str(r.get("active")).lower() != "true":
                continue

            name = r.get("name_ru") if lang == "ru" else r.get("name_uz") or r.get("name_ru")

            result.append({
                "id": safe_int(r.get("id")),
                "name": name,
                "duration": safe_int(r.get("duration_min"), 30),
                "price": r.get("price"),
                "age_from": r.get("age_from"),
                "age_to": r.get("age_to"),
            })

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_massage_name(massage_id: int):
    try:
        ws = get_ws("masses")
        if not ws:
            return "—"

        records = get_cached_data("masses", lambda: safe_get_records(ws))

        for r in records:
            if safe_int(r.get("id")) == massage_id:
                return r.get("name_ru")

        return "—"

    except Exception as e:
        notify_error(e)
        return "—"


# =====================================================
# THERAPISTS (🔥 УСКОРЕНО)
# =====================================================

def get_therapists_for_massage(massage_id: int):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        therapists_data = get_cached_data(
            "therapists",
            lambda: safe_get_records(ss.worksheet("therapists"))
        )

        links_data = get_cached_data(
            "therapist_links",
            lambda: safe_get_records(ss.worksheet("therapist_masses"))
        )

        therapists = {
            safe_int(t.get("id")): t
            for t in therapists_data
        }

        result = []

        for l in links_data:
            if safe_int(l.get("massage_id")) == massage_id:
                t = therapists.get(safe_int(l.get("therapist_id")))
                if t:
                    result.append(t)

        return result

    except Exception as e:
        notify_error(e)
        return []


def get_therapist_name(therapist_id: int):
    try:
        ws = get_ws("therapists")
        if not ws:
            return "—"

        records = get_cached_data("therapists", lambda: safe_get_records(ws))

        for r in records:
            if safe_int(r.get("id")) == therapist_id:
                return r.get("name")

        return "—"

    except Exception as e:
        notify_error(e)
        return "—"


# =====================================================
# APPOINTMENTS
# =====================================================

def create_appointment(*args):
    try:
        ws = get_ws("appointments")
        if not ws:
            return None

        ws.append_row(list(args) + ["pending"])

        try:
            all_values = ws.get_all_values()
            return len(all_values)
        except Exception as e:
            notify_error(e)
            return None

    except Exception as e:
        notify_error(e)
        return None


def update_appointment_status(row: int, new_status: str):
    try:
        ws = get_ws("appointments")
        if not ws:
            return

        ws.update_cell(row, 9, new_status)

    except Exception as e:
        notify_error(e)


def get_all_appointments_full():
    try:
        ws = get_ws("appointments")
        if not ws:
            return []

        records = get_cached_data("appointments", lambda: safe_get_records(ws))

        result = []

        for idx, r in enumerate(records, start=2):
            result.append({
                "row": idx,
                "datetime": r.get("datetime"),
                "massage": get_massage_name(safe_int(r.get("massage_id"))),
                "therapist": get_therapist_name(safe_int(r.get("therapist_id"))),
                "child_name": r.get("child_name"),
                "phone": r.get("phone"),
                "status": r.get("status"),
            })

        return result

    except Exception as e:
        notify_error(e)
        return []


# =====================================================
# FREE TIMES (🔥 УСКОРЕНО)
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    try:
        ss = get_spreadsheet()
        if not ss:
            return []

        ws = ss.worksheet("appointments")

        records = get_cached_data("appointments", lambda: safe_get_records(ws))

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
