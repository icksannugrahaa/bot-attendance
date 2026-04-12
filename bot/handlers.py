from telegram import Update
from telegram.ext import ContextTypes

from bot.users import (
    list_users,
    add_user,
    get_user,
    set_automation,
    set_notes,
    set_location_pool,
    set_imei,
    load_users
)
import device_utils
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


def deny(update: Update):
    return update.effective_message.reply_text("❌ Akses ditolak")


# ======================
# COMMAND HANDLERS
# ======================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_alias = context.bot_data.get("alias")
    
    # Jangan proses '/start' di GLOBAL bot untuk auto-link
    if not bot_alias or bot_alias == "GLOBAL":
        await update.effective_message.reply_text("👋 Selamat datang di Indocyber Attendance Bot.")
        return

    users = list_users()
    user_data = users.get(bot_alias)

    if user_data:
        chat_id = str(update.effective_chat.id)
        # Jika chat_id belum ada, otomatis daftarkan.
        if not user_data.get("chat_id"):
            from bot.users import load_users, save_users
            all_users = load_users()
            all_users[bot_alias]["chat_id"] = chat_id
            save_users(all_users)
            await update.effective_message.reply_text(
                f"🎉 Selamat Datang!\n\nBot Personal untuk `{bot_alias}` berhasil dihubungkan dengan perangkat ini. \n\nSilahkan lakukan proses berikut agar bot bisa berjalan dengan normal:\n\n1.Silahkan minta admin untuk mereset IMEI dengan alasan 'ID already regstered with another IMEI' ketike mencoba login.\n\n2.Setelah imei berhasil direset, jalankan perintah /register_imei <alias>.\n\n3.Jika sudah berhasil, silahkan coba login dengan perintah /login <alias>.\n\n4.Jika sudah berhasil login berarti bot sudah bisa digunakan.\n\n5.Anda dapat menambahkan beberapa konfigurasi yang spesifik seperti : 1.Notes spesifik dengan perintah /setnotes <alias> <notes>. \n2.Mengaktifkan/menonaktifkan automation attandance dengan perintah /auto <on/off> <alias>. \n3.Melihat daftar lokasi dengan /location_list dan mengubah location absen dengan /setlocation <alias> <nama_atau_id_lokasi>. (Gunakan /addlocation untuk menambah lokasi baru) \n4.Mengelola waktu absen acak dengan /set_checkin_timerange <alias> <start> <end> dan /set_checkout_timerange <alias> <start> <end>.\n5.Anda bisa mengecek history dengan perintah /history <alias> atau /history week atau /history month atau /history timesheet <alias>.\n6.Anda juga dapat melakukan absen masuk/pulang manual dengan perintah /masuk <alias> atau /pulang <alias>.\n\n DAH SISANYA TANYA ADMINN.", 
                parse_mode="Markdown"
            )
            from logger import log
            log(f"[{bot_alias}] Chat ID ({chat_id}) berhasil di-link via /start")
        else:
             await update.effective_message.reply_text("Bot ini sudah terhubung.")
    else:
        await update.effective_message.reply_text("User tidak ditemukan.")

# ======================
# USERS
# ======================

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    users = list_users()
    if not users:
        return await update.effective_message.reply_text("Belum ada user.")

    msg = "👥 *User Terdaftar:*\n"
    for alias, u in users.items():
        auto = "ON" if u.get("automation") else "OFF"
        notes = u.get("notes") or "-"
        pool = u.get("location_pool", "kanpus").upper()
        msg += (
            f"\n• `{alias}`\n"
            f"  username: `{u['username']}`\n"
            f"  location: `{pool}`\n"
            f"  auto: `{auto}`\n"
            f"  notes: {notes}\n"
        )

    await update.effective_message.reply_text(msg, parse_mode="Markdown")


import os
import sys
from bot.botfather import create_new_bot

async def adduser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split()
        if len(parts) == 5:
            _, alias, username, password, imei = parts
            
            await update.effective_message.reply_text(f"⏳ Membuat bot Telegram personal untuk `{alias}` di @BotFather...", parse_mode="Markdown")
            try:
                bot_info = await create_new_bot(alias)
                bot_token = bot_info["token"]
                bot_username = bot_info["username"]
                
                # Chat ID kosong dulu, akan diisi saat user klik /start di bot barunya
                add_user(alias, username, password, imei, bot_token, "")
                
                msg = (
                    f"✅ User {alias} ditambahkan!\n\n"
                    f"🤖 Bot Personal: @{bot_username}\n"
                    f"Silahkan minta user untuk mencari username bot tersebut di Telegram dan klik tombol START agar otomatis terhubung.\n\n"
                    f"🔄 Bot System is restarting automatically to apply new configuration..."
                )
                await update.effective_message.reply_text(msg)
                
                # Restart bot otomatis melalui graceful shutdown
                import bot.state as tb
                tb.RESTART_FLAG = True
                if tb.STOP_EVENT:
                    tb.STOP_EVENT.set()
                
            except Exception as e:
                add_user(alias, username, password, imei)
                await update.effective_message.reply_text(f"⚠️ User ditambahkan, tapi gagal membuat bot otomatis.\nError Info: {str(e)}\n\nFormat manual: /adduser <alias> <user> <pass> <imei> [token chat_id]")


        elif len(parts) == 7:
            _, alias, username, password, imei, bot_token, chat_id = parts
            add_user(alias, username, password, imei, bot_token, chat_id)
            await update.effective_message.reply_text(f"✅ User `{alias}` ditambahkan beserta bot personal manual\n🔄 *Bot System is restarting otomatis*...", parse_mode="Markdown")
            
            # Restart otomatis
            import bot.state as tb
            tb.RESTART_FLAG = True
            if tb.STOP_EVENT:
                tb.STOP_EVENT.set()
        else:
            raise ValueError()

    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/adduser <alias> <username> <password> <imei>\nAtau:\n/adduser <alias> <username> <password> <imei> <bot_token> <chat_id>"
        )


# ======================
# LOGIN
# ======================

async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
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


async def register_imei_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
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
        ).register_imei()

        await update.effective_message.reply_text(f"✅ IMEI Berhasil Didaftarkan untuk `{alias}`", parse_mode="Markdown")

    except ValueError:
        await update.effective_message.reply_text("Format:\n/register_imei <alias>")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Register IMEI gagal: {e}")


# ======================
# DEVICE ID
# ======================

async def gendeviceid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split()
        new_imei = device_utils.generate_device_id()

        if len(parts) > 1:
            alias = parts[1]
            if set_imei(alias, new_imei):
                await update.effective_message.reply_text(f"✅ Device ID (IMEI) baru untuk `{alias}` berhasil dibuat dan disimpan:\n`{new_imei}`\n\nSilahkan jalankan `/register_imei {alias}` untuk mendaftarkannya ke server.", parse_mode="Markdown")
            else:
                await update.effective_message.reply_text("❌ User tidak ditemukan. Gunakan `/gendeviceid` tanpa alias untuk generate saja.", parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(f"✅ Generated Device ID (Android):\n`{new_imei}`", parse_mode="Markdown")
            
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Gagal generate device id: {e}")


# ======================
# ATTENDANCE
# ======================

async def masuk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split()
        alias = parts[1] if len(parts) > 1 else None
        msg = check_in(alias)
        await update.effective_message.reply_text(msg)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")


async def pulang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
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
    if not is_admin(update, context):
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
    if not is_admin(update, context):
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
    if not is_admin(update, context):
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
# LOCATION SETTINGS
# ======================

async def location_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    from bot.location import load_locations
    locations = load_locations()
    if not locations:
        return await update.effective_message.reply_text("Belum ada lokasi tersimpan.")
        
    sorted_keys = sorted(locations.keys())
    
    # Set default location to "kanpus" for users who might be missing the field
    from bot.users import load_users
    users = load_users()
    pool_counts = {k: 0 for k in sorted_keys}
    for u in users.values():
        pool = u.get("location_pool", "kanpus").lower()
        if pool in pool_counts:
            pool_counts[pool] += 1
    
    msg = "📍 *Daftar Lokasi*\n\n"
    for idx, key in enumerate(sorted_keys):
        lat, lng = locations[key]
        users_count = pool_counts[key]
        gmaps_link = f"https://www.google.com/maps?q={lat},{lng}"
        
        msg += f"*{idx + 1}. {key.upper()}*\n"
        msg += f"   • Lat/Lng: `{lat}, {lng}`\n"
        msg += f"   • Total User: `{users_count}` user\n"
        msg += f"   • [Buka di Google Maps]({gmaps_link})\n\n"
        
    msg += "----- \n📌 _Gunakan_ `/setlocation <alias> <ID>` _atau_ `/setlocation <alias> <nama>`"
    await update.effective_message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)


async def setlocation_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split(maxsplit=2)
        if len(parts) != 3:
            raise ValueError()

        alias = parts[1]
        pool = parts[2].lower()

        from bot.location import load_locations
        available_locations = load_locations()
        sorted_keys = sorted(available_locations.keys())

        # Support selecting by ID
        if pool.isdigit():
            idx = int(pool) - 1
            if 0 <= idx < len(sorted_keys):
                pool = sorted_keys[idx]

        if pool not in available_locations:
            loc_list = ", ".join([f"'{k}'" for k in sorted_keys])
            return await update.effective_message.reply_text(f"❌ Location pool tidak valid.\nTersedia: {loc_list}\nGunakan /location_list atau /addlocation.")

        if not set_location_pool(alias, pool):
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        await update.effective_message.reply_text(
            f"📍 Location pool `{alias}` diubah ke: *{pool.upper()}*",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/setlocation <alias> <name_or_id>\nContoh:\n/setlocation icksan 1\n/setlocation icksan mb"
        )


async def addlocation_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split(maxsplit=2)
        if len(parts) != 3:
            raise ValueError()

        loc_name = parts[1].lower()
        latlng_str = parts[2]
        
        # Parse latlng (e.g. "12.34, 56.78" atau "-6.22,106.83")
        latlng = latlng_str.replace(" ", "").split(",")
        if len(latlng) != 2:
            return await update.effective_message.reply_text("❌ Format latlng salah. Contoh: -6.225336,106.831291")
            
        lat = float(latlng[0])
        lng = float(latlng[1])
        
        from bot.location import save_location
        save_location(loc_name, lat, lng)

        await update.effective_message.reply_text(
            f"✅ Location `{loc_name}` berhasil ditambahkan/diupdate dengan koordinat {lat}, {lng}.",
            parse_mode="Markdown"
        )

    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/addlocation <location_name> <lat,lng>\nContoh:\n/addlocation hotel_manhatan -6.2253,106.8312"
        )



# ======================
# TIME RANGES
# ======================

async def set_checkin_timerange_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split()
        if len(parts) != 4:
            raise ValueError()

        alias = parts[1]
        start_time = parts[2]
        end_time = parts[3]

        from bot.users import set_checkin_timerange
        if not set_checkin_timerange(alias, start_time, end_time):
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        await update.effective_message.reply_text(
            f"✅ Waktu check-in `{alias}` diatur ke: *{start_time} - {end_time}*",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/set_checkin_timerange <alias> <start_time> <end_time>\nContoh:\n/set_checkin_timerange icksan 07:15 07:35"
        )


async def set_checkout_timerange_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
        return await deny(update)

    try:
        parts = update.message.text.split()
        if len(parts) != 4:
            raise ValueError()

        alias = parts[1]
        start_time = parts[2]
        end_time = parts[3]

        from bot.users import set_checkout_timerange
        if not set_checkout_timerange(alias, start_time, end_time):
            return await update.effective_message.reply_text("❌ User tidak ditemukan")

        await update.effective_message.reply_text(
            f"✅ Waktu check-out `{alias}` diatur ke: *{start_time} - {end_time}*",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.effective_message.reply_text(
            "Format:\n/set_checkout_timerange <alias> <start_time> <end_time>\nContoh:\n/set_checkout_timerange icksan 16:30 17:30"
        )


# ======================
# AUTOMATION FLAG
# ======================

async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update, context):
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

