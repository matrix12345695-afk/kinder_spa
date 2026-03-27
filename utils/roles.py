from sheets import get_spreadsheet
from config import SPREADSHEET_NAME


def get_user_role(user_id: int) -> str:
    spreadsheet = get_spreadsheet(SPREADSHEET_NAME)
    sheet = spreadsheet.worksheet("users_roles")
    rows = sheet.get_all_records()

    for row in rows:
        if int(row["user_id"]) == user_id:
            return row["role"]

    return "USER"
