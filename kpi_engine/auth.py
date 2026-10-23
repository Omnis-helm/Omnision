"""
Authentication & server-side RBAC helpers shared by the Streamlit UI and the FastAPI backend.

* Passwords: salted PBKDF2-HMAC-SHA256 (`pbkdf2_sha256$iterations$salt$hash`). Legacy unsalted
  SHA-256 hashes are still accepted so old users.json files keep working; re-hash them with
  `python -m kpi_engine.auth set-password <user> <role>`.
* API tokens: stateless HMAC-signed tokens (username, role, expiry). Set OMNISION_API_SECRET in .env
  so tokens survive restarts; otherwise a random per-process secret is used.
* Provider policy: public cloud LLMs require EXECUTIVE_VP clearance - enforced in the backend, not
  only in the UI.
"""
import base64
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from kpi_engine.config import PUBLIC_LLM_PROVIDERS
from kpi_engine.data.models import UserClearance
from kpi_engine.scoper.security_matrix import clearance_level

USERS_PATH = Path(__file__).resolve().parent / "users.json"
PBKDF2_ITERATIONS = 200_000
_API_SECRET = (os.getenv("OMNISION_API_SECRET") or secrets.token_hex(32)).encode()
TOKEN_TTL_SECONDS = 8 * 3600


# ----------------------------------------------------------------------------- passwords
def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, it, salt, digest = stored.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(it))
            return hmac.compare_digest(dk.hex(), digest)
        except ValueError:
            return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()  # legacy unsalted format
    return hmac.compare_digest(legacy, stored)


def load_users(path: Path = USERS_PATH) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def authenticate(username: str, password: str, path: Path = USERS_PATH) -> Optional[UserClearance]:
    user = load_users(path).get(username)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None
    try:
        return UserClearance(user["role"])
    except (KeyError, ValueError):
        return None


# ----------------------------------------------------------------------------- policy
def is_public_provider(provider: str) -> bool:
    return (provider or "").lower() in PUBLIC_LLM_PROVIDERS


def provider_allowed(role: UserClearance, provider: str) -> bool:
    return not is_public_provider(provider) or clearance_level(role) >= clearance_level(UserClearance.EXECUTIVE_VP)


def assert_providers_allowed(role: UserClearance, *providers: str):
    blocked = [p for p in providers if not provider_allowed(role, p)]
    if blocked:
        raise PermissionError(
            f"Role {role.value} may not send telemetry to public cloud LLMs {blocked}. "
            "Use a private provider (ollama / mock) or an EXECUTIVE_VP account.")


def require_clearance(role: UserClearance, minimum: UserClearance):
    if clearance_level(role) < clearance_level(minimum):
        raise PermissionError(f"Requires {minimum.value} clearance (current: {role.value}).")


# ----------------------------------------------------------------------------- API tokens
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(username: str, role: UserClearance, ttl: int = TOKEN_TTL_SECONDS) -> str:
    body = _b64(json.dumps({"u": username, "r": role.value, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(_API_SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str) -> Optional[Tuple[str, UserClearance]]:
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(_API_SECRET, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(body))
        if data["exp"] < time.time():
            return None
        return data["u"], UserClearance(data["r"])
    except Exception:
        return None


# ----------------------------------------------------------------------------- CLI
def _cli():  # pragma: no cover
    """python -m kpi_engine.auth set-password <username> <ROLE>"""
    if len(sys.argv) != 4 or sys.argv[1] != "set-password":
        print("usage: python -m kpi_engine.auth set-password <username> <EXECUTIVE_VP|SENIOR_ENGINEER|JUNIOR_ANALYST>")
        sys.exit(1)
    user, role = sys.argv[2], UserClearance(sys.argv[3])
    pw = getpass.getpass(f"New password for {user}: ")
    users = load_users()
    users[user] = {"role": role.value, "password_hash": hash_password(pw)}
    USERS_PATH.write_text(json.dumps(users, indent=4), encoding="utf-8")
    print(f"Updated {user} ({role.value}) in {USERS_PATH}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
