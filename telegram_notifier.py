import requests
from logger import log
from config import TELEGRAM_CONFIG
from bot.users import get_user

def send_telegram(message: str, alias: str | None = None):
    try:
        token = TELEGRAM_CONFIG.get("bot_token")
        chat_id = TELEGRAM_CONFIG.get("chat_id")

        if alias:
            user_data = get_user(alias)
            if user_data and user_data.get("bot_token") and user_data.get("chat_id"):
                token = user_data["bot_token"]
                chat_id = user_data["chat_id"]

        if not token or not chat_id:
            log(f"TELEGRAM ERROR: Tidak ada token/chat_id untuk mengirim pesan.")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }

        r = requests.post(url, json=payload, timeout=10)

        if r.status_code == 200:
            log(f"TELEGRAM [{alias or 'GLOBAL'}]: pesan terkirim")
        else:
            log(f"TELEGRAM ERROR [{alias or 'GLOBAL'}]: {r.status_code} {r.text}")

    except Exception as e:
        log(f"TELEGRAM ERROR [{alias or 'GLOBAL'}]: {e}")

def notify_error(msg: str, alias: str | None = None):
    send_telegram(f"🚨 *Automation Error*\n{msg}", alias)
