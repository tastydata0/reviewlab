import os
import json
import jwt
import time
from typing import Optional

CONFIG_FILE = os.path.expanduser("~/.rlcli_config.json")
DEFAULT_URL = "http://localhost:8080/api"

def _load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def save_token(token: str):
    config = _load_config()
    config["token"] = token
    _save_config(config)

def load_token() -> Optional[str]:
    config = _load_config()
    token = config.get("token")
    if token and _is_token_valid(token):
        return token
    return None

def delete_token():
    config = _load_config()
    if "token" in config:
        del config["token"]
        _save_config(config)

def save_url(url: str):
    config = _load_config()
    config["base_url"] = url.rstrip("/")
    _save_config(config)

def load_url() -> str:
    config = _load_config()
    return config.get("base_url", DEFAULT_URL)

def _is_token_valid(token: str) -> bool:
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("exp", 0) > time.time()
    except Exception:
        return False
