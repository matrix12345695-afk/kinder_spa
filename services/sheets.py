import datetime
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except:
    gspread = None

from config import GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS

def _client():
    if not gspread:
        return None
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS, scope)
    return gspread.authorize(creds)

def get_ws(name="appointments"):
    gc = _client()
    if not gc:
        return None
    sh = gc.open(GOOGLE_SHEET_NAME)
    try:
        return sh.worksheet(name)
    except:
        return sh.add_worksheet(title=name, rows=1000, cols=20)

def add_appointment(rec: dict):
    ws = get_ws()
    if not ws:
        return False
    row = [
        rec.get("user_id"), rec.get("service"), rec.get("master"),
        rec.get("date"), rec.get("time"), rec.get("name"), rec.get("phone"),
        "NEW", datetime.datetime.utcnow().isoformat()
    ]
    ws.append_row(row)
    return True

def get_busy_slots(date: str, master: str):
    ws = get_ws()
    if not ws:
        return set()
    vals = ws.get_all_values()
    busy = set()
    for r in vals[1:]:
        if len(r) >= 5 and r[3]==date and r[2]==master and r[7] in ("NEW","CONFIRMED"):
            busy.add(r[4])
    return busy

def stats():
    ws = get_ws()
    if not ws:
        return {"total":0}
    vals = ws.get_all_values()
    return {"total": max(0, len(vals)-1)}
