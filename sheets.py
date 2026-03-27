import os
import json
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME

# =====================================================
# AUTH (через ENV, а не файл)
# =====================================================

SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]

def get_client():
    if not GOOGLE_CREDENTIALS:
        raise ValueError("❌ GOOGLE_CREDENTIALS не задан")

    creds_dict = json.loads(GOOGLE_CREDENTIALS)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPE
    )

    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()

    if not SPREADSHEET_NAME:
        raise ValueError("❌ SPREADSHEET_NAME не задан")

    return client.open(SPREADSHEET_NAME)


# =====================================================
# USERS
# =====================================================

def get_user_lang(user_id: int):
    try:
        ws = get_spreadsheet().worksheet("users")
        for r in ws.get_all_records():
            if str(r.get("user_id")) == str(user_id):
                return r.get("lang")
    except:
        pass
    return None


def set_user_lang(user_id: int, lang: str):
    ws = get_spreadsheet().worksheet("users")
    rows = ws.get_all_records()

    for i, r in enumerate(rows, start=2):
        if str(r.get("user_id")) == str(user_id):
            ws.update_cell(i, 2, lang)
            return

    ws.append_row([user_id, lang])


# =====================================================
# ADMINS
# =====================================================

def get_admin_role(user_id: int):
    try:
        ws = get_spreadsheet().worksheet("admins")
        for r in ws.get_all_records():
            if str(r.get("user_id")) == str(user_id):
                return r.get("role")
    except:
        pass
    return None


# =====================================================
# CONTACTS
# =====================================================

def get_contacts():
    try:
        ws = get_spreadsheet().worksheet("contacts")
        result = []

        for r in ws.get_all_records():
            line = " ".join(str(v) for v in r.values() if v)
            if line.strip():
                result.append(line)

        return result
    except:
        return []


# =====================================================
# MASSAGES
# =====================================================

def get_active_masses(lang: str = "ru"):
    ws = get_spreadsheet().worksheet("masses")
    rows = ws.get_all_records()

    result = []
    for r in rows:
        if str(r.get("active", "")).upper() != "TRUE":
            continue

        result.append({
            "id": int(r.get("id", 0)),
            "name": r.get("name_ru") if lang == "ru" else r.get("name_uz"),
            "price": r.get("price") or r.get("cost") or r.get("цена") or 0,
            "duration": int(r.get("duration_min", 0)),
            "age_from": int(r.get("age_from", 0)),
            "age_to": int(r.get("age_to", 0)),
        })

    return result


def get_massage_name(massage_id: int, lang: str = "ru") -> str:
    ws = get_spreadsheet().worksheet("masses")
    for r in ws.get_all_records():
        if int(r.get("id", 0)) == massage_id:
            return r.get("name_ru") if lang == "ru" else r.get("name_uz")
    return "—"


# =====================================================
# THERAPISTS
# =====================================================

def get_therapists_for_massage(massage_id: int):
    ss = get_spreadsheet()

    therapists = {
        int(t["id"]): t
        for t in ss.worksheet("therapists").get_all_records()
    }

    links = ss.worksheet("therapist_masses").get_all_records()

    result = []
    for l in links:
        if int(l.get("massage_id", 0)) == massage_id:
            t = therapists.get(int(l.get("therapist_id", 0)))
            if t:
                result.append(t)

    return result


def get_therapist_name(therapist_id: int) -> str:
    ws = get_spreadsheet().worksheet("therapists")
    for r in ws.get_all_records():
        if int(r.get("id", 0)) == therapist_id:
            return r.get("name", "—")
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


def update_appointment_status(row: int, new_status: str):
    ws = get_spreadsheet().worksheet("appointments")
    ws.update_cell(row, 9, new_status)


def get_all_appointments_full(user_id: int, lang: str = "ru"):
    ss = get_spreadsheet()
    ws = ss.worksheet("appointments")

    result = []
    for idx, r in enumerate(ws.get_all_records(), start=2):
        if str(r.get("user_id")) == str(user_id):
            result.append({
                "row": idx,
                "datetime": r.get("datetime"),
                "massage": get_massage_name(int(r.get("massage_id", 0)), lang),
                "therapist": get_therapist_name(int(r.get("therapist_id", 0))),
                "child": r.get("child_name", ""),
                "status": r.get("status", ""),
            })

    return result


def get_appointments_for_reminder(hours_before: int = 24):
    ss = get_spreadsheet()
    ws = ss.worksheet("appointments")

    now = datetime.now()
    target_from = now + timedelta(hours=hours_before - 1)
    target_to = now + timedelta(hours=hours_before + 1)

    result = []

    for r in ws.get_all_records():
        if r.get("status") != "approved":
            continue

        try:
            ap_dt = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")
        except:
            continue

        if target_from <= ap_dt <= target_to:
            result.append({
                "user_id": r.get("user_id"),
                "datetime": r.get("datetime"),
                "massage_id": r.get("massage_id"),
                "therapist_id": r.get("therapist_id"),
                "child_name": r.get("child_name", ""),
            })

    return result


# =====================================================
# FREE TIME
# =====================================================

def get_free_times(therapist_id: int, date_str: str, duration_min: int = 30):
    ss = get_spreadsheet()

    schedule_ws = ss.worksheet("schedule")
    appointments_ws = ss.worksheet("appointments")

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    now = datetime.now()

    weekday_map = {
        0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт",
        4: "Пт", 5: "Сб", 6: "Вс",
    }

    weekday = weekday_map[date_obj.weekday()]

    work_from = work_to = None

    for r in schedule_ws.get_all_records():
        if int(r.get("therapist_id", 0)) == therapist_id and r.get("weekday") == weekday:
            work_from = datetime.strptime(r.get("time_from"), "%H:%M").time()
            work_to = datetime.strptime(r.get("time_to"), "%H:%M").time()
            break

    if not work_from or not work_to:
        return []

    step = timedelta(minutes=60 if duration_min > 30 else 30)
    duration = timedelta(minutes=duration_min)

    busy = []
    for r in appointments_ws.get_all_records():
        if int(r.get("therapist_id", 0)) == therapist_id and r.get("status") == "approved":
            try:
                dt = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")
                if dt.date() == date_obj:
                    busy.append(dt)
            except:
                pass

    min_time = datetime.combine(date_obj, work_from)

    if date_obj == now.date():
        min_time = now + timedelta(hours=2)

    slots = []
    current = datetime.combine(date_obj, work_from)
    end_time = datetime.combine(date_obj, work_to)

    while current + duration <= end_time:
        if current >= min_time:
            if all(abs((b - current).total_seconds()) >= duration.total_seconds() for b in busy):
                slots.append(current.strftime("%H:%M"))
        current += step

    return slots