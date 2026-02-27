# test.py
# ============================================================
# FILE INI HANYA UNTUK DEVELOPMENT — JANGAN JALANKAN DI SERVER
# Gunakan TEST_MODE=true di .env untuk simulasi aman
# ============================================================
import os

if os.getenv("ALLOW_TEST") != "1":
    raise SystemExit(
        "❌ test.py tidak boleh dijalankan langsung di production!\n"
        "   Jalankan dengan: ALLOW_TEST=1 python test.py"
    )

from storage import save_token
from attendance import check_in, check_out

# save_token("icksan", {"access_token": "dummy", "expires_at": "2099-01-01T00:00:00+00:00"})

check_in()           # default user
check_in("icksan")   # user spesifik
check_out("icksan")