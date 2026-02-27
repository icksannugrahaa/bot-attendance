import sys
from bot.users import get_user
from auth import AuthClient
from attendance import check_in, check_out
from logger import log

def help():
    print("""
Usage:
  python main.py login <alias>
  python main.py masuk [alias]
  python main.py pulang [alias]
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
        sys.exit(1)

    try:
        cmd = sys.argv[1]

        if cmd == "login":
            if len(sys.argv) < 3:
                print("Usage: python main.py login <alias>")
                sys.exit(1)
            alias = sys.argv[2]
            user = get_user(alias)
            if not user:
                print(f"ERROR: User '{alias}' tidak ditemukan di users.json")
                sys.exit(1)
            AuthClient(
                alias=alias,
                username=user["username"],
                password=user["password"],
                imei=user["imei"]
            ).login_and_get_token()
            print(log(f"[{alias}] Login & token berhasil"))

        elif cmd == "masuk":
            alias = sys.argv[2] if len(sys.argv) > 2 else None
            print(check_in(alias))

        elif cmd == "pulang":
            alias = sys.argv[2] if len(sys.argv) > 2 else None
            print(check_out(alias))

        else:
            help()

    except Exception as e:
        print("ERROR:", log(str(e)))
