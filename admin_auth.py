from __future__ import annotations
import hmac

ADMIN_PASSWORD = "admin"

def verify_password(password: str) -> bool:
    return hmac.compare_digest(password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8"))
