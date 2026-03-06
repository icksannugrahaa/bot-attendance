import subprocess
import time
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_CHAT_IDS, SERVICE_NAME, LOG_PATH
from bot.security import verify_password
from audit_logger import audit_log

# ======================
# SECURITY GUARDS
# ======================

FAILED_AUTH = {}          # chat_id -> [count, last_ts]
MAX_FAIL = 5
BLOCK_SECONDS = 300       # 5 menit

from bot.users import get_user

def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    chat_id = str(update.effective_chat.id)
    # 1. Global Admin Check
    if chat_id in ADMIN_CHAT_IDS:
        return True
        
    # 2. Personal Bot Check
    if context:
        bot_alias = context.bot_data.get("alias")
        if bot_alias and bot_alias != "GLOBAL":
            user_data = get_user(bot_alias)
            if user_data and user_data.get("chat_id") == chat_id:
                return True
                
    return False


def is_blocked(chat_id: int) -> bool:
    data = FAILED_AUTH.get(chat_id)
    if not data:
        return False
    count, last_ts = data
    return count >= MAX_FAIL and time.time() - last_ts < BLOCK_SECONDS


def register_fail(chat_id: int):
    count, _ = FAILED_AUTH.get(chat_id, (0, 0))
    FAILED_AUTH[chat_id] = (count + 1, time.time())


def reset_fail(chat_id: int):
    FAILED_AUTH.pop(chat_id, None)


async def deny(update: Update):
    if update.message:
        await update.message.reply_text("❌ Akses ditolak")

# ======================
# SYSTEMD SERVICE
# ======================

async def service_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    username = user.username or user.first_name

    if is_blocked(chat_id):
        return await update.message.reply_text("⏳ Terlalu banyak percobaan, coba lagi nanti")

    parts = update.message.text.split()
    if len(parts) != 3:
        return await update.message.reply_text(
            "Format:\n"
            "/service <password> start|stop|restart|status"
        )

    password, action = parts[1], parts[2]

    if not verify_password(password):
        register_fail(chat_id)
        audit_log("service_auth", user.id, username, "FAILED", "wrong_password")
        return await update.message.reply_text("❌ Password salah")

    reset_fail(chat_id)

    if action not in ("start", "stop", "restart", "status"):
        return await update.message.reply_text("❌ Action tidak valid")

    try:
        output = subprocess.check_output(
            ["/bin/systemctl", action, SERVICE_NAME],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15
        )

        audit_log(f"service_{action}", user.id, username, "SUCCESS")

        msg = output.strip() or f"Service `{SERVICE_NAME}` → `{action.upper()}` OK"
        await update.message.reply_text(f"🛠 {msg}")

    except Exception as e:
        audit_log(f"service_{action}", user.id, username, "FAILED", str(e))
        await update.message.reply_text(f"❌ Gagal: {e}")

# ======================
# LOG VIEWER
# ======================

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    if not update.message or not update.message.text:
        return

    user = update.effective_user
    username = user.username or user.first_name

    parts = update.message.text.split()
    if len(parts) != 3:
        return await update.message.reply_text(
            "Format:\n"
            "/logs <password> bot|error|cron|attendance|audit"
        )

    password, key = parts[1], parts[2]

    if not verify_password(password):
        audit_log("logs_auth", user.id, username, "FAILED", "wrong_password")
        return await update.message.reply_text("❌ Password salah")

    log_map = {
        "bot": "bot.log",
        "error": "bot.error.log",
        "cron": "cron.log",
        "attendance": "attendance.log",
        "audit": "audit.log",
    }

    if key not in log_map:
        return await update.message.reply_text("❌ Log tidak dikenal")

    file_path = f"{LOG_PATH}/{log_map[key]}"

    try:
        output = subprocess.check_output(
            ["/usr/bin/tail", "-n", "50", file_path],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )

        audit_log("logs_view", user.id, username, "SUCCESS", key)

        # Telegram safety limit
        output = output[-3500:]

        await update.message.reply_text(
            f"📄 *{log_map[key]}*\n```\n{output or '(kosong)'}\n```",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        audit_log("logs_view", user.id, username, "FAILED", str(e))
        await update.message.reply_text(f"❌ Gagal membaca log")
