# attendance.py
import requests
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram_notifier import send_telegram
from storage import (
    load_token,
    is_token_expired,
    is_already_checked_in,
    is_already_checked_out,
    save_check_in,
    save_check_out,
    get_or_create_time
)
from sprint import get_current_sprint
from logger import log
from config import BASE_URL, TEST_MODE
from bot.users import load_users

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
except ImportError:
    pass


# ======================
# CONFIG
# ======================

DEFAULT_USERNAME = "icksan.nugraha"

#Location Kantor Pusat
# LOCATION_POOL = [
#     {"lat": -6.2169029, "lng": 106.8145117},
#     {"lat": -6.2170483, "lng": 106.8144632},
#     {"lat": -6.2169641, "lng": 106.8147136},
#     {"lat": -6.2172156, "lng": 106.8144859},
#     {"lat": -6.2168369, "lng": 106.8144021},
# ]

#Location Kantor MB
LOCATION_POOL = [
    {"lat": -6.24087391, "lng": 106.83660382},
    {"lat": -6.24095942, "lng": 106.83650713},
    {"lat": -6.24084277, "lng": 106.83655894},
    {"lat": -6.24093165, "lng": 106.83662044},
    {"lat": -6.24098736, "lng": 106.83657512},
    {"lat": -6.24090124, "lng": 106.83648367},
    {"lat": -6.24086853, "lng": 106.83653629},
    {"lat": -6.24094418, "lng": 106.83659173},
    {"lat": -6.24092384, "lng": 106.83646395},
    {"lat": -6.24087962, "lng": 106.83651548},
]

# ======================
# HELPER
# ======================

def random_time(start_h, start_m, end_h, end_m) -> str:
    base = datetime(2000, 1, 1, start_h, start_m)
    end = datetime(2000, 1, 1, end_h, end_m)
    seconds = int((end - base).total_seconds())
    return datetime.fromtimestamp(
        base.timestamp() + random.randint(0, seconds)
    ).strftime("%H:%M:%S")


def _headers(token: dict) -> dict:
    return {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "okhttp/3.14.9",
    }


def _resolve_alias(alias: str | None) -> str:
    """
    Jika alias None → pakai default user
    """
    if alias:
        return alias

    users = load_users()
    for a, u in users.items():
        if u.get("username") == DEFAULT_USERNAME:
            return a

    raise Exception("Default user tidak ditemukan")


def _get_user(alias: str) -> dict:
    users = load_users()
    if alias not in users:
        raise Exception(f"User '{alias}' tidak ditemukan")
    return users[alias]


def _now_jakarta():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


# ======================
# CHECK IN
# ======================

def check_in(alias: str | None = None) -> str:
    alias = _resolve_alias(alias)
    user = _get_user(alias)

    token = load_token(alias)
    if not token or is_token_expired(token):
        raise Exception(f"[{alias}] Token tidak ada / expired")

    now = _now_jakarta()
    date_key = now.strftime("%Y-%m-%d")

    if is_already_checked_in(alias, date_key):
        return f"[{alias}] Sudah absen masuk hari ini"

    sprint = get_current_sprint(now.date())
    notes = user.get("notes") or f"Working sprint {sprint}"

    location = random.choice(LOCATION_POOL)
    log_time = get_or_create_time(
        alias,
        date_key,
        (7, 15),
        (7, 35)
    )

    payload = {
        "UserName": token["loginName"],
        "LogDate": now.strftime("%m/%d/%Y"),
        "LogTime": log_time,
        "LocationID": token.get("LocationID"),
        "LocationName": token.get("Location"),
        "LocationAddress": "Gedung BRI Tower II, Jakarta",
        "Longitude": location["lng"],
        "Latitude": location["lat"],
        "LogType": "Start Day",
        "Event": "",
        "Notes": notes,
        "GMT": "7",
    }


    # ===== TEST MODE =====
    if TEST_MODE:
        save_check_in(alias, date_key)
        msg = log(f"[TEST] [{alias}] Simulasi absen masuk | {notes}")
        send_telegram(msg)
        return msg

    # ===== REAL MODE =====
    r = requests.post(
        f"{BASE_URL}/ESS/api/Attendance/Absence",
        data=payload,
        headers=_headers(token),
        timeout=15
    )
    r.raise_for_status()

    resp = r.json()
    if resp.get("isSucceed"):
        save_check_in(alias, date_key)
        msg = log(f"[{alias}] Absen masuk berhasil | {notes}")
        send_telegram(msg)
        return msg

    raise Exception(f"[{alias}] Absen masuk gagal: {resp}")


# ======================
# CHECK OUT
# ======================

def check_out(alias: str | None = None) -> str:
    alias = _resolve_alias(alias)

    token = load_token(alias)
    if not token or is_token_expired(token):
        raise Exception(f"[{alias}] Token tidak ada / expired")

    now = _now_jakarta()
    date_key = now.strftime("%Y-%m-%d")

    if is_already_checked_out(alias, date_key):
        return f"[{alias}] Sudah absen pulang hari ini"

    location = random.choice(LOCATION_POOL)
    log_time = get_or_create_time(
        alias,
        date_key,
        (16, 30),
        (17, 30)
    )

    payload = {
        "UserName": token["loginName"],
        "LogDate": now.strftime("%m/%d/%Y"),
        "LogTime": log_time,
        "LocationID": token.get("LocationID"),
        "LocationName": token.get("Location"),
        "LocationAddress": "Gedung BRI Tower II, Jakarta",
        "Longitude": location["lng"],
        "Latitude": location["lat"],
        "LogType": "End Day",
        "GMT": "7",
    }

    # ===== TEST MODE =====
    if TEST_MODE:
        save_check_out(alias, date_key)
        msg = log(f"[TEST] [{alias}] Simulasi absen pulang")
        send_telegram(msg)
        return msg

    # ===== REAL MODE =====
    r = requests.post(
        f"{BASE_URL}/ESS/api/Attendance/Absence",
        data=payload,
        headers=_headers(token),
        timeout=15
    )
    r.raise_for_status()

    resp = r.json()
    if resp.get("isSucceed"):
        save_check_out(alias, date_key)
        msg = log(f"[{alias}] Absen pulang berhasil")
        send_telegram(msg)
        return msg

    raise Exception(f"[{alias}] Absen pulang gagal: {resp}")


# ======================
# HISTORY
# ======================

def get_attendance_history(alias: str, date_from: str, date_to: str) -> list:
    token = load_token(alias)
    if not token or is_token_expired(token):
        raise Exception(f"[{alias}] Token tidak ada / expired")

    payload = {
        "DateFrom": date_from,
        "DateTo": date_to
    }

    r = requests.post(
        f"{BASE_URL}/ESS/api/Attendance/History",
        data=payload,
        headers=_headers(token),
        timeout=15
    )
    r.raise_for_status()

    result = r.json()
    if result.get("isSucceed"):
        return result.get("ReturnValue", [])

    raise Exception(f"[{alias}] Gagal mengambil history: {result}")


def get_history_for_user(alias: str, mode: str | None = None) -> str:
    from datetime import timedelta

    now = _now_jakarta()

    if mode == "week":
        start = (now - timedelta(days=6)).strftime("%m/%d/%Y")
    elif mode == "month":
        start = (now - timedelta(days=30)).strftime("%m/%d/%Y")
    else:
        start = now.strftime("%m/%d/%Y")

    end = now.strftime("%m/%d/%Y")

    records = get_attendance_history(alias, start, end)

    msg = f"\n👤 *{alias}*\n"
    if not records:
        return msg + "Belum ada data\n"

    for r in records:
        raw_date = r.get("LogDate", "")
        # Helper for Indonesian Months
        id_months = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        try:
            if "T" in raw_date:
                dt_obj = datetime.strptime(raw_date.split("T")[0], "%Y-%m-%d")
            else:
                dt_obj = datetime.strptime(raw_date.split(" ")[0], "%m/%d/%Y")
            date_str = f"{dt_obj.day} {id_months[dt_obj.month]} {dt_obj.year}"
        except (ValueError, TypeError):
            date_str = raw_date or "-"

        time = r.get("DisplayTime", "-")
        typ = r.get("LogType", "-")
        note = r.get("Notes", "-")
        lat = r.get("Latitude")
        lng = r.get("Longitude")

        map_url = (
            f"https://maps.google.com/?q={lat},{lng}"
            if lat and lng else ""
        )

        msg += f"• {date_str} - {time} - {typ} - {note} - {lat} - {lng} - {map_url}\n"

    return msg


def generate_timesheet_excel(alias: str) -> str:
    """
    Generate an Excel timesheet for the specified user and return the true file path.
    Requires openpyxl.
    """
    from datetime import timedelta
    import os

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        raise Exception("openpyxl library is required for this feature")

    now = _now_jakarta()
    # default fetch 1 month history
    start = (now - timedelta(days=30)).strftime("%m/%d/%Y")
    end = now.strftime("%m/%d/%Y")

    records = get_attendance_history(alias, start, end)

    # Helper for Indonesian Months
    id_months = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    # Group records by Date
    grouped_data = {}
    
    for r in records:
        raw_date = r.get("LogDate", "")
        # convert dates to DD MMMM YYYY (Indonesian)
        try:
            if "T" in raw_date:
                dt_obj = datetime.strptime(raw_date.split("T")[0], "%Y-%m-%d")
            else:
                dt_obj = datetime.strptime(raw_date.split(" ")[0], "%m/%d/%Y")
            date_str = f"{dt_obj.day} {id_months[dt_obj.month]} {dt_obj.year}"
        except (ValueError, TypeError):
            date_str = raw_date or "-"

        if date_str not in grouped_data:
            grouped_data[date_str] = {
                "check_in": "-",
                "check_out": "-",
                "work_place": "-"
            }

        typ = r.get("LogType", "")
        time = r.get("DisplayTime", "")
        loc_name = r.get("LocationName") or r.get("LocationAddress") or "Gedung BRI Tower II, Jakarta"
        
        if typ == "Start Day":
            if grouped_data[date_str]["check_in"] == "-":
                grouped_data[date_str]["check_in"] = time
                grouped_data[date_str]["work_place"] = loc_name
        elif typ == "End Day":
            grouped_data[date_str]["check_out"] = time
            if grouped_data[date_str]["work_place"] == "-":
                 grouped_data[date_str]["work_place"] = loc_name

    # Create Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = f"Timesheet {alias}"

    # Headers
    headers = ["date", "check in", "check out", "work place"]
    ws.append(headers)
    
    header_font = Font(bold=True)
    alignment = Alignment(horizontal="center")

    for col in range(1, 5):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.alignment = alignment

    # Write Data Rows
    # get_attendance_history often returns descending. To sort it, we could try parsing "date_str" back if needed.
    # But usually it's fine as returned.
    
    for date_str, data in grouped_data.items():
        ws.append([
            date_str, 
            data["check_in"], 
            data["check_out"], 
            data["work_place"]
        ])

    # Adjust Column Widths mildly
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 30

    import tempfile
    file_path = os.path.join(tempfile.gettempdir(), f"{alias}_timesheet.xlsx")
    wb.save(file_path)

    return file_path
