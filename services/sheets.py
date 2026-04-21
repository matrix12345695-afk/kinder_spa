
import gspread
import os, json
from oauth2client.service_account import ServiceAccountCredentials

def get_client():
    creds_json = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    return gspread.authorize(creds)

def get_services():
    client = get_client()
    sheet = client.open_by_key(os.getenv("SPREADSHEET_NAME")).worksheet("services")
    return [row[0] for row in sheet.get_all_values() if row]

def get_dates():
    client = get_client()
    sheet = client.open_by_key(os.getenv("SPREADSHEET_NAME")).worksheet("dates")
    return [row[0] for row in sheet.get_all_values() if row]

def get_times():
    client = get_client()
    sheet = client.open_by_key(os.getenv("SPREADSHEET_NAME")).worksheet("times")
    return [row[0] for row in sheet.get_all_values() if row]

def save_to_sheets(data):
    try:
        client = get_client()
        sheet = client.open_by_key(os.getenv("SPREADSHEET_NAME")).sheet1
        sheet.append_row([
            data["name"],
            data["phone"],
            data["service"],
            data["date"],
            data["time"]
        ])
    except Exception as e:
        print("Sheets error:", e)
