import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not API_ID or not API_HASH:
    print("❌ ERROR: TELEGRAM_API_ID atau TELEGRAM_API_HASH belum di set di .env")
    exit(1)

# Session file will be saved as anon.session in the current directory
client = TelegramClient('anon', API_ID, API_HASH)

def main():
    print("Mencoba login...")
    
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())

    # Memaksa menggunakan instance async default
    client.start()
    
    # Setelah start() berhasil, OTP selesai.
    me = client.get_me()
    print(f"\n✅ Berhasil Login sebagai: {me.first_name} (@{me.username})")
    print("✅ File `anon.session` telah dibuat. Telethon API siap digunakan oleh Automation Bot.")

if __name__ == '__main__':
    main()
