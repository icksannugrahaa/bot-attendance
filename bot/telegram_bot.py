import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.state

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
    setlocation_cmd,
    register_imei_cmd,
    gendeviceid_cmd,
    addlocation_cmd,
    location_list_cmd,
    set_checkin_timerange_cmd,
    set_checkout_timerange_cmd,
    start_cmd,
    menu_cmd
)
from bot.users import load_users
from config import TELEGRAM_CONFIG
from logger import log
from bot.handlers_admin import service_cmd, logs_cmd


# ======================
# GLOBAL ERROR HANDLER
# ======================
async def error_handler(update, context):
    err = context.error
    log(f"[BOT ERROR] {repr(err)}")

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ Terjadi error:\n`{str(err)}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

def build_bot_app(token: str, alias: str = "GLOBAL"):
    request = HTTPXRequest(
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=10,
    )

    app = (
        ApplicationBuilder()
        .token(token)
        .request(request)
        .build()
    )

    # ===== COMMANDS =====
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("list_users", users_cmd))
    app.add_handler(CommandHandler("add_user", adduser_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("checkin", masuk_cmd))
    app.add_handler(CommandHandler("checkout", pulang_cmd))
    app.add_handler(CommandHandler("set_auto", auto_cmd))
    app.add_handler(CommandHandler("list_history", history_cmd))
    app.add_handler(CommandHandler("set_notes", setnotes_cmd))
    app.add_handler(CommandHandler("clear_notes", clearnotes_cmd))
    app.add_handler(CommandHandler("set_location", setlocation_cmd))
    app.add_handler(CommandHandler("add_location", addlocation_cmd))
    app.add_handler(CommandHandler("list_location", location_list_cmd))
    app.add_handler(CommandHandler("set_checkin_timerange", set_checkin_timerange_cmd))
    app.add_handler(CommandHandler("set_checkout_timerange", set_checkout_timerange_cmd))
    app.add_handler(CommandHandler("register_imei", register_imei_cmd))
    app.add_handler(CommandHandler("generate_deviceid", gendeviceid_cmd))

    # ===== ADMIN COMMANDS =====
    app.add_handler(CommandHandler("service", service_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))

    # ===== ERROR HANDLER =====
    app.add_error_handler(error_handler)
    
    # Simpan informasi bot di context aplikasi
    app.bot_data["alias"] = alias

    return app

async def run_bots():
    users = load_users()
    apps = []
    
    # 1. Start Main/Global Bot (from config.py) if token exists
    main_token = TELEGRAM_CONFIG.get("bot_token")
    if main_token:
        log("[MULTIPLEX] Membangun Main Bot")
        apps.append(build_bot_app(main_token, "GLOBAL"))
        
    # 2. Start Personal Bots
    added_tokens = {main_token} if main_token else set()
    for alias, user in users.items():
        user_token = user.get("bot_token")
        if user_token and user_token not in added_tokens:
            log(f"[MULTIPLEX] Membangun Bot Pesonal: {alias}")
            apps.append(build_bot_app(user_token, alias))
            added_tokens.add(user_token)

    if not apps:
        print("Tidak ada bot_token yang terkonfigurasi!")
        return

    print(f"Memulai {len(apps)} bot instance...")
    
    # Initialize and start all applications properly
    for app in apps:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=["message"], drop_pending_updates=True)

    print("Semua bot berjalan. Tekan Ctrl+C untuk berhenti.")

    bot.state.STOP_EVENT = asyncio.Event()

    # Keep running until cancelled by user
    try:
        await bot.state.STOP_EVENT.wait()
    except KeyboardInterrupt:
        pass
        
    print("\nStopping bots...")
    for app in apps:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    import asyncio
    try:
        asyncio.run(run_bots())
    except KeyboardInterrupt:
        pass
        
    if bot.state.RESTART_FLAG:
        print("Restarting script natively...")
        os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    main()
