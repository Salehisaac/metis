---
{
  "id": "WEB.M06.L01",
  "title": "Password hashing: salt, slow hashes, constant-time checks",
  "difficulty": "intermediate",
  "minutes": 60,
  "prerequisites": ["WEB.M05"],
  "objectives": [
    "Explain why passwords are hashed, not encrypted, and why a fast hash such as sha256 is unsafe even with a salt",
    "Hash a password with a per-user random salt using hashlib.scrypt or hashlib.pbkdf2_hmac, and store the salt and cost parameters with the hash",
    "Verify a password by recomputing with the stored salt and parameters and comparing with hmac.compare_digest",
    "Choose cost parameters from the OWASP baseline, and explain how stored parameters allow raising the cost later"
  ],
  "why": "Every chat app gets its users table stolen eventually: a SQL injection, a leaked backup, a careless export. What matters then is how many passwords the attacker can recover, because people reuse them for email and banking. Correct hashing turns a stolen table from 'game over' into 'years of computing per password'. It's a few lines of code, and the mistakes are easy to make and invisible in normal use.",
  "applications": [
    "The users table of any API with password login",
    "Reviewing a legacy system that stores md5 or sha1 password hashes",
    "Hashing other secrets that must be checked but never read back, such as API keys or reset codes"
  ],
  "exercises": ["WEB.M06.L01.E1"],
  "sources": [
    {
      "title": "OWASP Password Storage Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "Passwords should be hashed (one-way), not encrypted, and never stored in plain text",
        "A salt is a unique, randomly generated value added to each password before hashing",
        "Algorithm order: Argon2id (minimum 19 MiB memory, 2 iterations, parallelism 1); scrypt if Argon2id is unavailable (N=2^17, r=8, p=1); bcrypt for legacy systems (work factor 10 or more, 72-byte limit); PBKDF2-HMAC-SHA256 with 600,000 iterations when FIPS-140 compliance is required",
        "Fast general-purpose hashes are not suitable for password storage",
        "A pepper is stored separately from the hashes and only adds defense in depth"
      ]
    },
    {
      "title": "hashlib: Key derivation (scrypt, pbkdf2_hmac)",
      "url": "https://docs.python.org/3.12/library/hashlib.html",
      "version": "Python 3.12 docs; installed Python 3.12.3",
      "verified": "2026-11-12",
      "claims": [
        "Signatures: hashlib.scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64) and hashlib.pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None)",
        "The salt should be about 16 or more bytes from a proper source such as os.urandom()",
        "A good password hashing function must be tunable, slow and include a salt; salted SHA-256 is not suitable for passwords",
        "maxmem limits memory (OpenSSL 1.1.0 defaults to 32 MiB)",
        "Applications should limit the password to a sensible length (e.g. 1024)"
      ]
    },
    {
      "title": "hmac.compare_digest",
      "url": "https://docs.python.org/3.12/library/hmac.html",
      "version": "Python 3.12 docs; installed Python 3.12.3",
      "verified": "2026-11-12",
      "claims": [
        "compare_digest returns a == b while avoiding content-based short-circuiting, to prevent timing analysis",
        "Both arguments must be the same type: ASCII str or bytes-like"
      ]
    },
    {
      "title": "secrets: Generate secure random numbers for managing secrets",
      "url": "https://docs.python.org/3.12/library/secrets.html",
      "version": "Python 3.12 docs; installed Python 3.12.3",
      "verified": "2026-11-12",
      "claims": ["Use secrets in preference to the random module, which is designed for modelling and simulation, not security or cryptography"]
    },
    {
      "title": "FastAPI Tutorial: OAuth2 with Password (and hashing), Bearer with JWT tokens",
      "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": ["The tutorial hashes passwords with the pwdlib package and the Argon2 algorithm"]
    }
  ]
}
---
## 1. Hash, don't encrypt, and don't hash fast

Login needs to answer one question: is this the password the user chose? It never needs to *read* the password back. So you store a **one-way hash** and compare hashes at login. Encryption would be the wrong tool: whoever steals the key gets every password.

But a plain hash isn't enough, for two reasons:

- **Identical passwords give identical hashes.** `sha256("hunter2")` is the same for every user and in every leaked database, so attackers precompute tables of common passwords. The fix is a **salt**: a random value per user, mixed into the hash and stored next to it. The salt isn't secret; its job is to make every hash unique.
- **General-purpose hashes are fast, by design.** Even with a salt, an attacker can just try guesses. Run on this machine:

```python
salt = os.urandom(16)

start = time.perf_counter()
for _ in range(100_000):
    hashlib.sha256(salt + b"hunter2").digest()
fast = (time.perf_counter() - start) / 100_000

start = time.perf_counter()
hashlib.pbkdf2_hmac("sha256", b"hunter2", salt, 600_000)
slow = time.perf_counter() - start

print(f"sha256:        {fast * 1e6:.2f} µs per guess")
print(f"pbkdf2 600k:   {slow * 1e3:.0f} ms per guess")
print(f"guesses/s/core: {1 / fast:,.0f} vs {1 / slow:,.0f}")
```

```console
sha256:        0.28 µs per guess
pbkdf2 600k:   72 ms per guess
guesses/s/core: 3,573,508 vs 14
```

About 3.5 million guesses per second per core against 14. A login that takes 72 ms more doesn't bother a user, but it makes a stolen table about 250,000 times more expensive to attack. That's the whole idea of a **password hash** (a key-derivation function): salted, **slow**, and **tunable**, so you can raise the cost as hardware gets faster.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import hashlib, os\n\na = hashlib.sha256(b\"hunter2\").hexdigest()\nb = hashlib.sha256(b\"hunter2\").hexdigest()\ns1, s2 = os.urandom(16), os.urandom(16)\nc = hashlib.pbkdf2_hmac(\"sha256\", b\"hunter2\", s1, 1000)\nd = hashlib.pbkdf2_hmac(\"sha256\", b\"hunter2\", s2, 1000)\nprint(a == b, c == d)",
  "answer": "True False",
  "explanation": "Without a salt, the same password always gives the same hash, so precomputed tables work. With a different random salt per user, the same password gives different hashes." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "The salt must be kept secret, separately from the password hash, or it's useless.", "answer": false,
  "explanation": "The salt is stored in the clear next to the hash; verification needs it. Its job is uniqueness, not secrecy: it defeats precomputed tables and hides which users share a password. A secret value kept outside the database is a different thing, called a pepper." }
```

## 2. Which algorithm, which cost?

The OWASP Password Storage Cheat Sheet gives an order of preference:

| Algorithm | Baseline from OWASP | Notes |
|---|---|---|
| **Argon2id** | 19 MiB memory, 2 iterations, parallelism 1 | first choice; needs a library (`argon2-cffi`, or `pwdlib` as in the FastAPI tutorial) |
| **scrypt** | N=2^17 (128 MiB), r=8, p=1 | if Argon2id isn't available; in the standard library as `hashlib.scrypt` |
| bcrypt | work factor 10 or more | legacy; only the first 72 bytes of the password count |
| **PBKDF2-HMAC-SHA256** | 600,000 iterations | when FIPS-140 compliance is required; `hashlib.pbkdf2_hmac` |

scrypt and Argon2 are **memory-hard**: each guess needs lots of RAM, which makes GPU and custom-hardware attacks expensive. PBKDF2 only costs CPU time.

This academy uses the standard library, so you see every step: scrypt in the exercise, PBKDF2 in the examples here. In a production project you'd normally use a maintained library such as argon2-cffi or pwdlib, which also handles the stored format and upgrades.

scrypt at the OWASP baseline needs more memory than OpenSSL allows by default:

```console
$ python3 -c 'import hashlib; hashlib.scrypt(b"hunter2", salt=b"0"*16, n=2**17, r=8, p=1)'
ValueError: [digital envelope routines] memory limit exceeded
```

The hashlib docs say `maxmem` defaults to OpenSSL's 32 MiB. n=2^17 with r=8 needs about 128 MiB (the figure in the OWASP table), so you pass a larger `maxmem`, for example `maxmem=256 * 1024 * 1024`.

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "Why do password-hashing functions have a tunable cost (iterations, memory)?",
  "options": ["So you can make each guess more expensive as hardware gets faster, while keeping logins acceptable", "So that two users with the same password get different hashes", "So the hash can be decrypted with the right cost value", "So that comparisons run in constant time"], "answer": 0,
  "explanation": "Cost is about the attacker's price per guess. Uniqueness comes from the salt, and constant-time comparison is a separate step (section 3). Hashes are never decrypted." }
```

## 3. Storing and verifying

Verification **repeats the hashing** with the same salt and parameters, then compares the results. So the stored string must contain everything needed to repeat it. The common pattern is one string with fields separated by `$`. Here it is for a 4-digit chat-lock PIN (a different secret, same technique):

```python
ITERATIONS = 600_000


def make_pin_hash(pin: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def check_pin(pin: str, record: str) -> bool:
    _, iterations, salt_hex, digest_hex = record.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest, bytes.fromhex(digest_hex))


record = make_pin_hash("4711")
print(record[:40] + "...")
print(check_pin("4711", record), check_pin("4712", record))
print(make_pin_hash("4711") == record)
```

```console
pbkdf2_sha256$600000$8312730a81d087304f1...
True False
False
```

- **The cost is stored per record.** `check_pin` reads the iteration count from the record, not from the constant. When you raise `ITERATIONS` next year, old records still verify, and you can re-hash a user's password with the new cost the next time they log in successfully (the only moment you have the plain password).
- **`hmac.compare_digest`** instead of `==`. A normal comparison can stop at the first differing byte, so its timing reveals how much of the value matched. `compare_digest` avoids that content-based short-circuiting. Both arguments must be the same type: `bytes` with `bytes`, or ASCII `str` with `str`.
- **`.encode("utf-8")`:** the functions take bytes, and a password like `pässwörd` must always encode the same way.
- **Limit the length.** The hashlib docs suggest a sensible limit such as 1024, so nobody can make your server hash a 10 MB "password" on every request.

**What `check_pin` doesn't handle:** a malformed record. `"oops".split("$")` has one field, so the unpacking raises ValueError, and the login endpoint would answer 500. Verification code must **fail closed**: anything unexpected means "no match", never an exception and never "match". The exercise requires this.

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import hmac\n\nprint(hmac.compare_digest(b\"abc\", b\"abd\"), hmac.compare_digest(b\"abc\", b\"abc\"))\ntry:\n    hmac.compare_digest(\"abc\", b\"abc\")\nexcept TypeError:\n    print(\"TypeError\")",
  "answer": "False True\nTypeError",
  "explanation": "compare_digest returns a == b, without stopping early. A str and a bytes value can't be compared, so it raises TypeError: compare bytes with bytes." }
```

```quiz
{ "id": "q5", "type": "choice", "label": "Debugging",
  "prompt": "A login stores `pbkdf2_sha256$600000$<salt>$<hash>`. Next year the team raises ITERATIONS to 900,000, and from then on every existing user fails to log in. What did the verify function do wrong?",
  "options": ["It used the ITERATIONS constant instead of the iteration count stored in each record", "It used compare_digest instead of ==", "It decoded the salt from hex", "It encoded the password as UTF-8"], "answer": 0,
  "explanation": "A hash can only be reproduced with the parameters it was made with. Read them from the stored record. The constant only applies to new hashes." }
```

## 4. Common mistakes

- **One fixed salt for everyone** (a "salt" constant in the code). Identical passwords get identical hashes again. Generate a new `os.urandom(16)` for every hash.
- **`random` instead of `os.urandom` or `secrets`** for salts and tokens. The `random` module is designed for modelling and simulation, not security.
- **Different error messages** for "unknown user" and "wrong password". Attackers use them to discover which usernames exist. Return one generic message. Lesson 3 also equalises the timing.
- **Logging the password,** for example a request body logged on validation errors. Hashing doesn't help if the plain text is in the logs.

```quiz
{ "id": "q6", "type": "explain", "label": "Application",
  "prompt": "You inherit a users table with unsalted md5 hashes. You can't ask every user to reset their password today. Outline a migration plan using what you learned here.",
  "model": "Add a column (or a format prefix) that says which algorithm each row uses. At the next successful login, verify against md5 (with compare_digest), then immediately store a new scrypt or Argon2id hash with a fresh salt, and mark the row upgraded. Optionally wrap the remaining md5 hashes right away: store scrypt(md5_hash) so the weak values are never at rest, and verify with scrypt(md5(password)). After a deadline, force a reset for users who never logged in. Never keep plain md5 longer than necessary.",
  "explanation": "Verify with the old scheme, re-hash with the new one at login: you only have the plain password at that moment." }
```

## 5. Your turn

Implement `hash_password`, `verify_password` and `needs_rehash` with scrypt. The tests lower N so the suite stays fast, which only works if your code reads the parameters when it's called.

```exercise
WEB.M06.L01.E1
```
