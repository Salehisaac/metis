```python
import os


def signing_secret() -> str:
    secret = os.environ.get(SECRET_ENV, "")
    if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
        raise RuntimeError(f"{SECRET_ENV} must be set to at least {MIN_SECRET_BYTES} bytes")
    return secret


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        signing_secret(),
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "sub", "iss", "aud"]},
    )
```

The hardcoded `SECRET = ...` line is deleted.

**Why the starter was dangerous**

- `jwt.decode(token, options={"verify_signature": False})` only base64-decodes the payload. Anyone can build a token with `"role": "admin"` and a garbage signature (the tampered-payload test does exactly that), and the server believed it. This is the same bug class you once fixed in Go: parsing the payload without verifying the signature.
- The hardcoded secret was in Git, so everyone with repository access, every CI log that printed the file, and every fork could sign valid tokens for any user.

**Why the fix works**

- **Signature with a server-chosen algorithm.** `algorithms=[ALGORITHM]` is a fixed list. The `alg` in the token header is attacker input, so a token claiming `alg: none` is rejected (`InvalidAlgorithmError`), as is a token signed with another key (`InvalidSignatureError`). PyJWT refuses to decode at all if you pass no `algorithms`.
- **Claims.** `exp` is checked automatically when present; `require` makes it mandatory, so a token that never expires is rejected (`MissingRequiredClaimError`). `audience` and `issuer` stop a correctly signed token for another service (`admin-api`) or from another issuer being accepted here. PyJWT also rejects a non-string `sub`.
- **Secret from the environment, read per call, failing closed.** No secret in the code means no secret in Git. Reading it per call lets tests (and secret rotation) change it. Raising when it's missing or short means a misconfigured deployment stops immediately instead of quietly running with a weak or empty key. 32 bytes matches the 256-bit HMAC-SHA256 key PyJWT recommends; it warns about shorter keys.
- **Exceptions propagate.** All of these errors subclass `jwt.InvalidTokenError`, so the FastAPI dependency in the next lesson catches that one class and answers 401.

**Alternative:** a settings object (pydantic-settings, or a small dataclass built at startup) validated once at boot. Validating at startup fails even earlier; the per-call read used here keeps the exercise simple and testable with `monkeypatch.setenv`.
