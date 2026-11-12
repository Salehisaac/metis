"""Password hashing for the chat API, with hashlib.scrypt.

Stored format (one string per user, in the users table):

    scrypt$<n>$<r>$<p>$<salt as hex>$<derived key as hex>

The cost parameters are stored with each hash, so old hashes still verify after
the constants below are raised, and needs_rehash() can tell which ones to upgrade.
"""

import hashlib  # noqa: F401  (hashlib, hmac and os are for your code)
import hmac  # noqa: F401
import os  # noqa: F401

N = 2**17           # CPU/memory cost (OWASP baseline for scrypt: 2**17, r=8, p=1)
R = 8
P = 1
SALT_BYTES = 16
KEY_BYTES = 32
MAX_PASSWORD_CHARS = 1024
MAXMEM = 256 * 1024 * 1024  # scrypt with n=2**17, r=8 needs about 128 MiB; OpenSSL's default limit is 32 MiB


def hash_password(password: str) -> str:
    """Hash with a new random salt and the current N, R, P. Return the stored-format string.

    Raise ValueError if the password is longer than MAX_PASSWORD_CHARS.
    """
    raise NotImplementedError


def verify_password(password: str, stored: str) -> bool:
    """True if password matches the stored hash, using the parameters and salt stored in it.

    Return False (never raise) for a wrong password, a too-long password or a malformed stored string.
    Compare the keys in constant time.
    """
    raise NotImplementedError


def needs_rehash(stored: str) -> bool:
    """True if stored was made with parameters different from the current N, R, P (or is malformed)."""
    raise NotImplementedError
