import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
)
from telegram.request import HTTPXRequest

from bot.handlers import (
    setnotes_cmd,
    users_cmd,
    adduser_cmd,
    login_cmd,
    masuk_cmd,
    pulang_cmd,
    auto_cmd,
    history_cmd,
    clearnotes_cmd,
    setlocation_cmd
)
from config import TELEGRAM_CONFIG
from logger import log
from bot.handlers_admin import service_cmd, logs_cmd


# ======================
# GLOBAL ERROR HANDLER
# ======================
async def error_handler(update, context):
    err = context.error
    log(f"[BOT ERROR] {repr(err)}")

    # Jangan balas jika update kosong (mis. polling error)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ Terjadi error:\n`{str(err)}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass


# ======================
# MAIN
# ======================
def main():
    # 🔐 HTTPX config untuk mencegah RemoteProtocolError
    request = HTTPXRequest(
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=10,
    )

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_CONFIG["bot_token"])
        .request(request)
        .build()
    )

    # ===== COMMANDS =====
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("adduser", adduser_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("masuk", masuk_cmd))
    app.add_handler(CommandHandler("pulang", pulang_cmd))
    app.add_handler(CommandHandler("auto", auto_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("setnotes", setnotes_cmd))
    app.add_handler(CommandHandler("clearnotes", clearnotes_cmd))
    app.add_handler(CommandHandler("setlocation", setlocation_cmd))

    # ===== ADMIN COMMANDS =====
    app.add_handler(CommandHandler("service", service_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))

    # ===== ERROR HANDLER =====
    app.add_error_handler(error_handler)

    print("Telegram Attendance Bot berjalan...")

    # allowed_updates dibatasi agar polling ringan & stabil
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True  # ⬅️ penting saat restart
    )


if __name__ == "__main__":
    main()
