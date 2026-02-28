import json
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(os.path.dirname(_BASE_DIR), "users.json")


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(data: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_user(alias: str, username: str, password: str, imei: str):
    users = load_users()
    users[alias] = {
        "username": username,
        "password": password,
        "imei": imei,
        "active": True,
        "automation": False,
        "location_pool": "mb"
    }
    save_users(users)


def get_user(alias: str):
    return load_users().get(alias)


def list_users():
    return load_users()


def set_automation(alias: str, enabled: bool):
    users = load_users()
    if alias not in users:
        return False
    users[alias]["automation"] = enabled
    save_users(users)
    return True

def set_notes(alias: str, notes: str | None):
    users = load_users()
    if alias not in users:
        return False

    users[alias]["notes"] = notes
    save_users(users)
    return True


def set_location_pool(alias: str, pool_name: str) -> bool:
    users = load_users()
    if alias not in users:
        return False

    users[alias]["location_pool"] = pool_name.lower()
    save_users(users)
    return True
