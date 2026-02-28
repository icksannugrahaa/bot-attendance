# runner.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime, time
from zoneinfo import ZoneInfo

from bot.users import load_users
from auth import AuthClient
from attendance import check_in, check_out
from storage import (
    load_token,
    is_token_expired,
    is_already_checked_in,
    is_already_checked_out
)
from logger import log
from config import TEST_MODE
import json
import os
from telegram_notifier import send_telegram
import holidays
from datetime import timedelta

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_DIR = os.path.join(os.path.dirname(_BASE_DIR), "status")
os.makedirs(STATUS_DIR, exist_ok=True)
LOCK_FILE = os.path.join(STATUS_DIR, "attendance_runner.lock")

def acquire_lock():
    if os.name == 'nt':
        import msvcrt
        lock_fd = open(LOCK_FILE, "w")
        try:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            return lock_fd
        except OSError:
            print("Runner masih berjalan, skip.")
            notify_error(f"Coba absen lagi nanti\nRunner masih berjalan, skip.")
            sys.exit(0)
    else:
        import fcntl
        lock_fd = open(LOCK_FILE, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except BlockingIOError:
            print("Runner masih berjalan, skip.")
            notify_error(f"Coba absen lagi nanti\nRunner masih berjalan, skip.")
            sys.exit(0)

def notify_error(msg):
    send_telegram(f"🚨 *Automation Error*\n{msg}")


# ======================
# CONFIG
# ======================

TZ = ZoneInfo("Asia/Jakarta")

CHECK_IN_START  = time(7, 15)
CHECK_IN_END    = time(7, 35)

CHECK_OUT_START = time(16, 30)
CHECK_OUT_END   = time(17, 30)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_DIR = os.path.join(os.path.dirname(_BASE_DIR), "status")
os.makedirs(STATUS_DIR, exist_ok=True)


# ======================
# HELPER
# ======================

def now():
    return datetime.now(TZ)


ID_HOLIDAYS = holidays.ID()

def is_weekend_or_holiday(dt: datetime) -> tuple[bool, str]:
    if dt.weekday() >= 5: # 5=Sat, 6=Sun
        return True, "Akhir pekan (Weekend)"
    
    date_obj = dt.date()
    if date_obj in ID_HOLIDAYS:
        return True, f"Libur Nasional: {ID_HOLIDAYS.get(date_obj)}"
        
    return False, ""


def _update_notif_state(filepath: str, key: str, value: str) -> bool:
    """Helper for reading, updating, and writing json notification state. Returns True if updated."""
    data = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except:
            pass

    if data.get(key) != value:
        data[key] = value
        try:
            with open(filepath, "w") as f:
                json.dump(data, f)
        except:
            pass
        return True
    return False


def check_tomorrow_holiday(dt: datetime):
    tomorrow = dt.date() + timedelta(days=1)
    if tomorrow in ID_HOLIDAYS:
        notif_path = os.path.join(STATUS_DIR, "holiday_notif.json")
        today_str = dt.strftime("%Y-%m-%d")
        if _update_notif_state(notif_path, "last_notified", today_str):
            holiday_name = ID_HOLIDAYS.get(tomorrow)
            send_telegram(f"ℹ️ *Info Libur*\nBesok adalah hari libur: *{holiday_name}*.\nBot tidak akan absen otomatis besok.")


def notify_today_holiday(dt: datetime, reason: str, window: str):
    notif_path = os.path.join(STATUS_DIR, "today_holiday_notif.json")
    today_str = dt.strftime("%Y-%m-%d")
    
    if _update_notif_state(notif_path, window, today_str):
        send_telegram(f"ℹ️ *Info Libur / Akhir Pekan*\nHari ini adalah *{reason}*.\nBot tidak melakukan absen *{window}* otomatis hari ini.")


def notify_tomorrow_status(alias: str, dt_now: datetime, context: str):
    """
    Kirim notifikasi ke Telegram mengenai status bot untuk besok.
    context = 'checkout' atau 'nightly'
    """
    tomorrow = dt_now.date() + timedelta(days=1)
    
    is_weekend = tomorrow.weekday() >= 5
    holiday_name = ID_HOLIDAYS.get(tomorrow)
    
    if is_weekend or holiday_name:
        reason = holiday_name if holiday_name else "Akhir Pekan"
        if context == 'checkout':
            msg = f"🎉 *Selamat Beristirahat, {alias}!*\nKamu sudah berhasil check-out.\n\nBesok adalah *{reason}*, jadi bot absen otomatis akan dimatikan besok. Sampai jumpa di hari kerja berikutnya!"
        else: # nightly
            msg = f"🌙 *Nightly Update ({alias})*\nBesok adalah *{reason}*.\nBot absen otomatis *TIDAK* akan berjalan besok."
    else:
        if context == 'nightly':
            msg = f"🌙 *Nightly Update ({alias})*\nBesok adalah hari kerja biasa.\nBot absen otomatis *AKAN* berjalan sesuai jadwal besok pagi."
        else:
            return  # Tidak perlu spam saat checkout jika besok hari biasa
            
    send_telegram(msg)



def in_range(now_t: time, start: time, end: time) -> bool:
    return start <= now_t <= end


def random_time_between(start: time, end: time) -> str:
    start_sec = start.hour * 3600 + start.minute * 60
    end_sec   = end.hour * 3600 + end.minute * 60
    sec = random.randint(start_sec, end_sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"


def status_path(alias: str) -> str:
    return os.path.join(STATUS_DIR, f"{alias}.json")


def _sched_key(date_key: str) -> str:
    """Key terpisah agar tidak konflik dengan 'IN'/'OUT' milik storage.py."""
    return f"schedule:{date_key}"


def load_daily_schedule(alias: str, date_key: str) -> dict:
    path = status_path(alias)
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        data = json.load(f)

    value = data.get(_sched_key(date_key), {})
    # Guard: tolak nilai lama (string) akibat bug sebelumnya
    return value if isinstance(value, dict) else {}


def save_daily_schedule(alias: str, date_key: str, payload: dict):
    path = status_path(alias)
    data = {}

    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)

    data[_sched_key(date_key)] = payload

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def ensure_schedule(alias: str, date_key: str) -> dict:
    sched = load_daily_schedule(alias, date_key)
    if sched:
        return sched

    sched = {
        "in": random_time_between(CHECK_IN_START, CHECK_IN_END),
        "out": random_time_between(CHECK_OUT_START, CHECK_OUT_END)
    }

    save_daily_schedule(alias, date_key, sched)
    log(f"[AUTO] [{alias}] Jadwal hari ini IN={sched['in']} OUT={sched['out']}")
    return sched


def ensure_login(alias: str, user: dict):
    token = load_token(alias)
    if token and not is_token_expired(token):
        return

    log(f"[AUTO] [{alias}] Token expired / tidak ada → login")
    AuthClient(
        alias=alias,
        username=user["username"],
        password=user["password"],
        imei=user["imei"]
    ).login_and_get_token()


# ======================
# MAIN RUNNER
# ======================

def run():
    now_dt = now()
    now_t = now_dt.time()
    date_key = now_dt.strftime("%Y-%m-%d")

    check_tomorrow_holiday(now_dt)

    is_day_off, reason = is_weekend_or_holiday(now_dt)
    if is_day_off:
        log(f"[AUTO] Skip automation hari ini: {reason}")
        if in_range(now_t, CHECK_IN_START, CHECK_IN_END):
            notify_today_holiday(now_dt, reason, "Masuk")
        elif in_range(now_t, CHECK_OUT_START, CHECK_OUT_END):
            notify_today_holiday(now_dt, reason, "Pulang")
        return

    users = load_users()
    if not users:
        return

    for alias, user in users.items():
        if not user.get("automation"):
            continue

        try:
            sched = ensure_schedule(alias, date_key)

            # ===== CHECK IN =====
            if not is_already_checked_in(alias, date_key):
                sched_in = time.fromisoformat(sched["in"])
                if now_t >= sched_in and in_range(now_t, CHECK_IN_START, CHECK_IN_END):
                    ensure_login(alias, user)
                    log(f"[AUTO] [{alias}] Eksekusi absen masuk @ {sched['in']}")
                    msg = check_in(alias)
                    send_telegram(msg)

            # ===== CHECK OUT =====
            elif not is_already_checked_out(alias, date_key):
                sched_out = time.fromisoformat(sched["out"])
                if now_t >= sched_out and in_range(now_t, CHECK_OUT_START, CHECK_OUT_END):
                    ensure_login(alias, user)
                    log(f"[AUTO] [{alias}] Eksekusi absen pulang @ {sched['out']}")
                    msg = check_out(alias)
                    send_telegram(msg)
                    notify_tomorrow_status(alias, now_dt, context='checkout')

        except Exception as e:
            log(f"[AUTO] [{alias}] ERROR: {e}")
            notify_error(f"{alias}\n{e}")

    log("[AUTO] Runner tick selesai")


def run_nightly_check():
    now_dt = now()
    log("[AUTO] Menjalankan pengecekan Nightly Update (22:00)")
    
    users = load_users()
    if not users:
        return
        
    for alias, user in users.items():
        if not user.get("automation"):
            continue
        notify_tomorrow_status(alias, now_dt, context='nightly')


# ======================
# ENTRY
# ======================

if __name__ == "__main__":
    lock = acquire_lock()
    if len(sys.argv) > 1 and sys.argv[1] == "--nightly":
        run_nightly_check()
    else:
        run()


