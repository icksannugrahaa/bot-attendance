from telegram import Update
from telegram.ext import ContextTypes

from bot.users import (
    list_users,
    add_user,
    get_user,
    set_automation,
    set_notes,
    load_users
)
from auth import AuthClient
from attendance import (
    check_in,
    check_out,
    get_history_for_user,
    generate_timesheet_excel
)
from config import ADMIN_CHAT_IDS


# ======================
# GUARD
# ======================

def is_admin(update: Update) -> bool:
    return str(update.effective_chat.id) in ADMIN_CHAT_IDS


def deny(update: Update):
    return update.effective_message.reply_text("❌ Akses ditolak")


# ======================
# USERS
# ======================

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    users = list_users()
    if not users:
        return await update.effective_message.reply_text("Belum ada user.")

    msg = "👥 *User Terdaftar:*\n"
    for alias, u in users.items():
        auto = "ON" if u.get("automation") else "OFF"
        notes = u.get("notes") or "-"
        msg += (
            f"\n• `{alias}`\n"
            f"  username: `{u['username']}`\n"
            f"  auto: `{auto}`\n"
            f"  notes: {notes}\n"
        )

    await update.effective_message.reply_text(msg, parse_mode="Markdown")


async def adduser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        _, alias, username, password, imei = update.message.text.split()
        add_user(alias, username, password, imei)
        await update.effective_message.reply_text(f"✅ User `{alias}` ditambahkan", parse_mode="Markdown")
    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/adduser <alias> <username> <password> <imei>"
        )


# ======================
# LOGIN
# ======================

async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        _, alias = update.message.text.split()
        user = get_user(alias)
        if not user:
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        AuthClient(
            alias=alias,
            username=user["username"],
            password=user["password"],
            imei=user["imei"]
        ).login_and_get_token()

        await update.effective_message.reply_text(f"✅ Login berhasil `{alias}`", parse_mode="Markdown")

    except ValueError:
        await update.effective_message.reply_text("Format:\n/login <alias>")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Login gagal: {e}")


# ======================
# ATTENDANCE
# ======================

async def masuk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        parts = update.message.text.split()
        alias = parts[1] if len(parts) > 1 else None
        msg = check_in(alias)
        await update.effective_message.reply_text(msg)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")


async def pulang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        parts = update.message.text.split()
        alias = parts[1] if len(parts) > 1 else None
        msg = check_out(alias)
        await update.effective_message.reply_text(msg)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")


# ======================
# HISTORY
# ======================

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    parts = update.message.text.split()
    mode = None
    alias = None

    if len(parts) == 2:
        if parts[1] in ("week", "month", "timesheet"):
            mode = parts[1]
        else:
            alias = parts[1]

    elif len(parts) >= 3:
        mode = parts[1]
        alias = parts[2]

    users = load_users()
    
    if mode == "timesheet":
        if not alias:
            return await update.effective_message.reply_text("Format:\n/history timesheet <alias>")
        if alias not in users:
            return await update.effective_message.reply_text("❌ User tidak ditemukan")
        
        try:
            file_path = generate_timesheet_excel(alias)
            await update.effective_message.reply_document(
                document=open(file_path, "rb"),
                filename=f"Timesheet_{alias}.xlsx",
                caption=f"📊 Timesheet for {alias}"
            )
        except Exception as e:
            await update.effective_message.reply_text(f"❌ Gagal generate timesheet: {e}")
            
        return

    msg = ""
    if alias:
        msg = get_history_for_user(alias, mode)
    else:
        for a in users:
            msg += get_history_for_user(a, mode) + "\n"


    await update.effective_message.reply_text(
        msg or "Tidak ada data",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


# ======================
# NOTES
# ======================

async def setnotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        _, alias, notes = update.message.text.split(maxsplit=2)
        if not set_notes(alias, notes):
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        await update.effective_message.reply_text(
            f"📝 Notes `{alias}` diperbarui:\n{notes}",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/setnotes <alias> <pesan>"
        )


async def clearnotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)

    try:
        _, alias = update.message.text.split()
        if not set_notes(alias, None):
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        await update.effective_message.reply_text(
            f"🧹 Notes `{alias}` dihapus (pakai sprint default)",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/clearnotes <alias>"
        )


# ======================
# AUTOMATION FLAG
# ======================

async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.effective_message.reply_text("❌ Akses ditolak")
        return

    if not update.message or not update.message.text:
        return  # 🔥 PENTING: cegah NoneType error

    parts = update.message.text.split()

    if len(parts) != 3:
        await update.effective_message.reply_text(
            "Format:\n"
            "/auto on <alias>\n"
            "/auto off <alias>"
        )
        return

    _, mode, alias = parts
    enabled = mode.lower() == "on"

    if not set_automation(alias, enabled):
        await update.effective_message.reply_text("❌ User tidak ditemukan")
        return

    status = "AKTIF" if enabled else "NONAKTIF"
    await update.effective_message.reply_text(
        f"⚙️ Automation `{alias}`: {status}",
        parse_mode="Markdown"
    )

