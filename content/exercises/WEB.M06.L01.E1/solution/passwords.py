"""Password hashing for the chat API, with hashlib.scrypt.

Stored format (one string per user, in the users table):

    scrypt$<n>$<r>$<p>$<salt as hex>$<derived key as hex>

The cost parameters are stored with each hash, so old hashes still verify after
the constants below are raised, and needs_rehash() can tell which ones to upgrade.
"""

import hashlib
import hmac
import os

N = 2**17           # CPU/memory cost (OWASP baseline for scrypt: 2**17, r=8, p=1)
R = 8
P = 1
SALT_BYTES = 16
KEY_BYTES = 32
MAX_PASSWORD_CHARS = 1024
MAXMEM = 256 * 1024 * 1024  # scrypt with n=2**17, r=8 needs about 128 MiB; OpenSSL's default limit is 32 MiB


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
    """Hash with a new random salt and the current N, R, P. Return the stored-format string.

    Raise ValueError if the password is longer than MAX_PASSWORD_CHARS.
    """
    if len(password) > MAX_PASSWORD_CHARS:
        raise ValueError("password too long")
    salt = os.urandom(SALT_BYTES)
    key = _derive(password, salt, N, R, P)
    return f"scrypt${N}${R}${P}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """True if password matches the stored hash, using the parameters and salt stored in it.

    Return False (never raise) for a wrong password, a too-long password or a malformed stored string.
    Compare the keys in constant time.
    """
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
    """True if stored was made with parameters different from the current N, R, P (or is malformed)."""
    parsed = _parse(stored)
    return parsed is None or parsed[:3] != (N, R, P)
