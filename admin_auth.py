"""Admin password — stored in data/admin.json (persists across restarts)."""

from __future__ import annotations

import hashlib
import hmac
import json

from paths import data_dir

DEFAULT_PASSWORD = "admin"
_PASSWORD_FILENAME = "admin.json"


def _password_path():
    return data_dir() / _PASSWORD_FILENAME


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _stored_hash() -> str:
    data_dir().mkdir(parents=True, exist_ok=True)
    path = _password_path()
    if not path.exists():
        path.write_text(
            json.dumps({"password_hash": _hash(DEFAULT_PASSWORD)}, indent=2),
            encoding="utf-8",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["password_hash"]


def verify_password(password: str) -> bool:
    return hmac.compare_digest(_hash(password), _stored_hash())


def change_password(current_password: str, new_password: str) -> bool:
    if not verify_password(current_password):
        return False
    data_dir().mkdir(parents=True, exist_ok=True)
    _password_path().write_text(
        json.dumps({"password_hash": _hash(new_password)}, indent=2),
        encoding="utf-8",
    )
    return True
