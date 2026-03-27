import json
import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_client():
    if not GOOGLE_CREDENTIALS:
        raise ValueError("❌ GOOGLE_CREDENTIALS не задан")

    creds_dict = json.loads(GOOGLE_CREDENTIALS)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()
    return client.open(SPREADSHEET_NAME)


# =========================
# 👇 ДОБАВЛЕНО
# =========================

def get_users_sheet():
    sheet = get_spreadsheet()
    return sheet.worksheet("users")


def get_user_lang(user_id: int) -> str:
    sheet = get_users_sheet()
    rows = sheet.get_all_records()

    for row in rows:
        if str(row.get("user_id")) == str(user_id):
            return row.get("lang", "ru")

    return "ru"


def set_user_lang(user_id: int, lang: str):
    sheet = get_users_sheet()
    rows = sheet.get_all_records()

    for i, row in enumerate(rows, start=2):
        if str(row.get("user_id")) == str(user_id):
            sheet.update_cell(i, 2, lang)
            return

    # если пользователя нет — добавляем
    sheet.append_row([user_id, lang])
