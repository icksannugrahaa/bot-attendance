import os
import asyncio
import re
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

from config import TELEGRAM_CONFIG
from logger import log

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(_BASE_DIR, 'anon.session')

async def create_new_bot(alias: str) -> dict:
    """
    Mengautomasi botfather untuk membuat bot baru.
    Kembalian: {"token": "123:abc", "username": "BotName"} atau melempar Exception.
    """
    api_id = TELEGRAM_CONFIG.get("api_id")
    api_hash = TELEGRAM_CONFIG.get("api_hash")

    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID / TELEGRAM_API_HASH tidak di set")

    if not os.path.exists(SESSION_FILE):
        raise FileNotFoundError("Sesi telethon tidak ditemukan. Jalankan `python telethon_setup.py` terlebih dahulu di terminal.")

    # Inisiasi Client dengan anon session
    client = TelegramClient(SESSION_FILE, int(api_id), api_hash)
    
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise Exception("Sesi kadaluarsa. Jalankan `python telethon_setup.py` lagi.")

    try:
        # Gunakan nomor acak di username agar tidak bentrok
        import random
        rand_num = random.randint(100, 999)
        display_name = f"Absen IndoCyber - {alias}"
        bot_username = f"IndoAtt_{alias}_{rand_num}_bot"

        botfather = '@BotFather'

        log(f"[TELETHON] Memulai percakapan dengan BotFather untuk {alias}")
        
        async with client.conversation(botfather, timeout=10) as conv:
            # 1. Kirim /newbot
            await conv.send_message('/newbot')
            resp1: Message = await conv.get_response()
            if "Alright, a new bot" not in resp1.text:
                raise Exception(f"BotFather response error: {resp1.text}")
            
            # 2. Kirim Display Name
            await conv.send_message(display_name)
            resp2: Message = await conv.get_response()
            if "Good. Now let's choose a username" not in resp2.text:
                raise Exception(f"BotFather response error: {resp2.text}")

            # 3. Kirim Username
            await conv.send_message(bot_username)
            resp3: Message = await conv.get_response()
            
            if "Sorry, this username is already taken" in resp3.text:
                # Coba 1 kali lagi jika kebetulan Username penuh
                bot_username = f"IndoAtt_{alias}_{random.randint(1000, 9999)}_bot"
                await conv.send_message(bot_username)
                resp3 = await conv.get_response()

            if "Done! Congratulations" not in resp3.text:
                raise Exception(f"Gagal membuat bot: {resp3.text}")

            # 4. Extract Token pake Regex
            # Menggunakan \s* untuk handle \r\n atau sekedar \n
            match = re.search(r'HTTP API:\s*([\w:-]+)', resp3.text)
            if not match:
                match = re.search(r'`([\w:-]+)`', resp3.text) # Alternative matching
                
            if not match:
                raise Exception(f"Tidak dapat menemukan token di response: {resp3.text}")

            token = match.group(1).strip("`")
            log(f"[TELETHON] Sukses membuat @{bot_username}")
            
            return {
                "token": token,
                "username": bot_username
            }

    finally:
        await client.disconnect()
