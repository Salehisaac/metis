"""Access tokens for the chat API.

Security review findings for this file:
  1. The signing secret is hardcoded and committed to Git.
  2. decode_access_token trusts whatever payload it's given: it never checks the signature,
     the expiry, the audience or the issuer.
Fix both. The rules are in the docstrings below.
"""

from datetime import datetime, timedelta, timezone

import jwt

SECRET = "dev-secret-change-me"
ALGORITHM = "HS256"
ISSUER = "chat-auth"
AUDIENCE = "chat-api"
SECRET_ENV = "CHAT_JWT_SECRET"
MIN_SECRET_BYTES = 32


def signing_secret() -> str:
    """The secret from the environment variable SECRET_ENV, read on every call.

    Raise RuntimeError if it's missing or shorter than MIN_SECRET_BYTES bytes: fail closed,
    never fall back to a default.
    """
    return SECRET


def create_access_token(user_id: int, role: str, expires_in: timedelta = timedelta(minutes=15)) -> str:
    """A signed HS256 token with the claims sub (str(user_id)), role, iss, aud, iat and exp."""
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "role": role, "iss": ISSUER, "aud": AUDIENCE, "iat": now, "exp": now + expires_in}
    return jwt.encode(claims, signing_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """The verified claims of token.

    Verify the signature with signing_secret() and only ALGORITHM, check exp, aud == AUDIENCE and
    iss == ISSUER, and require the claims exp, iat, sub, iss and aud. Let PyJWT's exceptions
    (all subclasses of jwt.InvalidTokenError) propagate.
    """
    return jwt.decode(token, options={"verify_signature": False})
