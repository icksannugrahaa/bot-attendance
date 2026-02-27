import requests
from logger import log
from config import TELEGRAM_CONFIG

def send_telegram(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_CONFIG['bot_token']}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CONFIG["chat_id"],
            "text": message
        }

        r = requests.post(url, json=payload, timeout=10)

        if r.status_code == 200:
            log("TELEGRAM: pesan terkirim")
        else:
            log(f"TELEGRAM ERROR: {r.status_code} {r.text}")

    except Exception as e:
        log(f"TELEGRAM ERROR: {e}")

def notify_error(msg):
    send_telegram(f"🚨 *Automation Error*\n{msg}")
