```python
def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          maxmem=MAXMEM, dklen=KEY_BYTES)


def _parse(stored: str):
    """-> (n, r, p, salt, key), or None if stored isn't in our format."""
    fields = stored.split("$")
    if len(fields) != 6 or fields[0] != "scrypt":
        return None
    try:
        n, r, p = int(fields[1]), int(fields[2]), int(fields[3])
        salt, key = bytes.fromhex(fields[4]), bytes.fromhex(fields[5])
    except ValueError:
        return None
    return n, r, p, salt, key


def hash_password(password: str) -> str:
    if len(password) > MAX_PASSWORD_CHARS:
        raise ValueError("password too long")
    salt = os.urandom(SALT_BYTES)
    key = _derive(password, salt, N, R, P)
    return f"scrypt${N}${R}${P}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None or len(password) > MAX_PASSWORD_CHARS:
        return False
    n, r, p, salt, key = parsed
    try:
        candidate = _derive(password, salt, n, r, p)
    except ValueError:  # parameters OpenSSL rejects
        return False
    return hmac.compare_digest(candidate, key)


def needs_rehash(stored: str) -> bool:
    parsed = _parse(stored)
    return parsed is None or parsed[:3] != (N, R, P)
```

**Why it works**

- **Salt per password.** Two users with the same password get different stored strings, so a precomputed table is useless and a leaked database doesn't reveal who shares a password. The salt isn't secret; it's stored in the clear next to the key.
- **A deliberately slow, memory-hard function.** scrypt with n=2**17 and r=8 needs about 128 MiB and a noticeable fraction of a second per guess. An attacker with a stolen table pays that cost for every guess, for every user. sha256 takes about a microsecond, which allows billions of guesses.
- **Parameters inside the hash.** `verify_password` uses the n, r, p *stored with the hash*, not the current constants. So you can raise the cost later: old hashes keep working, and `needs_rehash` tells the login code to store a fresh hash once the user has typed the correct password.
- **`hmac.compare_digest`** avoids content-based short-circuiting: `==` can return as soon as the first byte differs, which leaks timing information.
- **Fail closed, never crash.** Any parse or parameter problem returns False. A malformed row can't become a 500, or worse, a successful login.
- **Length limit:** the hashlib docs advise limiting password length (e.g. 1024), so an attacker can't make the server hash megabytes per request.

**Alternatives:** OWASP ranks Argon2id first and scrypt second; PBKDF2 (`hashlib.pbkdf2_hmac`, 600,000 iterations for SHA-256) is the choice when FIPS-140 compliance is required. Production apps usually use a maintained library (argon2-cffi, bcrypt, or pwdlib as in the FastAPI tutorial) that also handles the format and rehashing. This exercise uses the standard library so you see every moving part.
