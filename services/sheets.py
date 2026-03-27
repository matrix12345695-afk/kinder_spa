import json
import os
import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS, SPREADSHEET_NAME

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_client():
    creds_dict = json.loads(GOOGLE_CREDENTIALS)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()
    return client.open(SPREADSHEET_NAME)