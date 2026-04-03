import time
import asyncio

# =========================================
# ГЛОБАЛЬНЫЙ КЭШ
# =========================================

CACHE = {
    "masses": [],
    "therapists": [],
    "therapist_links": [],
    "appointments": [],
    "schedule": [],
}

CACHE_TIME = {
    "masses": 0,
    "therapists": 0,
    "therapist_links": 0,
    "appointments": 0,
    "schedule": 0,
}

TTL = 30  # секунд


# =========================================
# ПРОВЕРКА КЭША
# =========================================

def is_valid(name):
    return time.time() - CACHE_TIME[name] < TTL


def get(name):
    return CACHE.get(name, [])


def set_cache(name, data):
    CACHE[name] = data
    CACHE_TIME[name] = time.time()


# =========================================
# ЗАГРУЗКА ИЗ SHEETS
# =========================================

def load_all_data(sheets):
    try:
        print("⚡ Loading cache...")

        ss = sheets.get_spreadsheet()
        if not ss:
            return

        set_cache("masses", sheets.safe_get_records(ss.worksheet("masses")))
        set_cache("therapists", sheets.safe_get_records(ss.worksheet("therapists")))
        set_cache("therapist_links", sheets.safe_get_records(ss.worksheet("therapist_masses")))
        set_cache("appointments", sheets.safe_get_records(ss.worksheet("appointments")))

        try:
            set_cache("schedule", sheets.safe_get_records(ss.worksheet("schedule")))
        except:
            set_cache("schedule", [])

        print("✅ Cache loaded")

    except Exception as e:
        sheets.notify_error(e)


# =========================================
# АВТО ОБНОВЛЕНИЕ
# =========================================

async def auto_update(sheets):
    while True:
        try:
            load_all_data(sheets)
        except Exception as e:
            sheets.notify_error(e)

        await asyncio.sleep(TTL)
