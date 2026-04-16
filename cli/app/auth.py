import os
import json
import jwt
import time
from typing import Optional

CONFIG_FILE = os.path.expanduser("~/.cli_config.json")


def save_token(token: str):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)


def load_token() -> Optional[str]:
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            token = data.get("token")
            if token and _is_token_valid(token):
                return token
    except Exception:
        pass
    return None


def delete_token():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


def _is_token_valid(token: str) -> bool:
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("exp", 0) > time.time()
    except Exception:
        return False
