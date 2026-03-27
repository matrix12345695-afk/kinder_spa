import json
import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_client():
    if not GOOGLE_CREDENTIALS:
        raise ValueError("❌ GOOGLE_CREDENTIALS не задан")

    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
    except Exception as e:
        raise ValueError(f"❌ Ошибка JSON credentials: {e}")

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()

    if not SPREADSHEET_NAME:
        raise ValueError("❌ SPREADSHEET_NAME не задан")

    try:
        return client.open(SPREADSHEET_NAME)
    except Exception as e:
        raise ValueError(f"❌ Не удалось открыть таблицу: {e}")
