import os
from datetime import datetime
from zoneinfo import ZoneInfo
from config import AUDIT_LOG_FILE

TZ = ZoneInfo("Asia/Jakarta")

os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)


def audit_log(
    action: str,
    user_id: int,
    username: str | None,
    result: str,
    detail: str = ""
):
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"[{ts}] "
        f"user_id={user_id} "
        f"user={username or '-'} "
        f"action={action} "
        f"result={result} "
        f"{detail}\n"
    )

    with open(AUDIT_LOG_FILE, "a") as f:
        f.write(line)

