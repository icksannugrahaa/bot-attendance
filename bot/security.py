import bcrypt
from config import ADMIN_SERVICE_PASSWORD_HASH


def verify_password(plain: str) -> bool:
    return bcrypt.checkpw(
        plain.encode(),
        ADMIN_SERVICE_PASSWORD_HASH
    )
