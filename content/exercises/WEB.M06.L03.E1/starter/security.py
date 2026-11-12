"""The team's security helpers (already reviewed). Don't edit this file."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

ITERATIONS = 600_000
SECRET_ENV = "CHAT_JWT_SECRET"
ISSUER, AUDIENCE = "chat-auth", "chat-api"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        name, iterations, salt, key = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
    except ValueError:
        return False
    return name == "pbkdf2_sha256" and hmac.compare_digest(candidate, bytes.fromhex(key))


# Checked when the username doesn't exist, so that case takes as long as a wrong password.
DUMMY_HASH = hash_password("dummy password, never matches")


def _secret() -> str:
    secret = os.environ.get(SECRET_ENV, "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError(f"{SECRET_ENV} must be set to at least 32 bytes")
    return secret


def create_access_token(user_id: int, expires_in: timedelta = timedelta(minutes=15)) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "iss": ISSUER, "aud": AUDIENCE, "iat": now, "exp": now + expires_in}
    return jwt.encode(claims, _secret(), algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Verified claims. Raises a subclass of jwt.InvalidTokenError for any bad token."""
    return jwt.decode(token, _secret(), algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER,
                      options={"require": ["exp", "iat", "sub", "iss", "aud"]})
