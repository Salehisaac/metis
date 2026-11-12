---
{
  "id": "WEB.M06.L02",
  "title": "JWT access tokens: sign, verify, expire",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["WEB.M06.L01"],
  "objectives": [
    "Explain what the three parts of a JWT are, and why the payload is readable and writable by anyone",
    "Create a signed HS256 token with PyJWT containing sub, iss, aud, iat and exp",
    "Decode a token safely: a key and algorithm list chosen by the server, audience and issuer checks, required claims, and the matching exception for each failure",
    "Keep the signing secret out of the code: load it from the environment at runtime and fail closed when it's missing"
  ],
  "why": "You've met both halves of this lesson in production Go code. Once, a secret was hardcoded and shipped, then fixed. Once, JWT parsing trusted the payload until it was replaced with signature verification. Both bugs pass every functional test: a token decodes, users log in, everything works. Then someone edits a token and becomes admin. This lesson is about the checks that make a token mean something.",
  "applications": [
    "Access tokens for a mobile or web client of the chat API",
    "Signed, expiring links: chat invites, password resets, email verification",
    "Verifying tokens issued by an identity provider (same checks, usually with RS256 and a public key)"
  ],
  "exercises": ["WEB.M06.L02.E1"],
  "sources": [
    {
      "title": "PyJWT: Usage Examples",
      "url": "https://pyjwt.readthedocs.io/en/stable/usage.html",
      "version": "PyJWT docs (stable); installed pyjwt 2.15.1",
      "verified": "2026-11-12",
      "claims": [
        "jwt.encode(payload, key, algorithm=...) and jwt.decode(token, key, algorithms=[...])",
        "decode raises ExpiredSignatureError if exp is in the past; leeway allows a margin",
        "A wrong aud raises InvalidAudienceError; a wrong iss raises InvalidIssuerError",
        "options={\"require\": [...]} raises MissingRequiredClaimError for a missing claim",
        "options={\"verify_signature\": False} skips verification and is ill-advised unless you understand what you're doing"
      ]
    },
    {
      "title": "RFC 7519: JSON Web Token (JWT)",
      "url": "https://www.rfc-editor.org/rfc/rfc7519",
      "version": "RFC 7519 (May 2015)",
      "verified": "2026-11-12",
      "claims": [
        "Each part of a JWT contains a base64url-encoded value",
        "iss identifies the issuer, sub the subject, iat the time of issue; exp is the time on or after which the JWT must not be accepted",
        "If the processor doesn't identify itself with a value in aud, the JWT must be rejected",
        "NumericDate is seconds since 1970-01-01T00:00:00Z UTC"
      ]
    },
    {
      "title": "OWASP REST Security Cheat Sheet (JWT section)",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "Ensure JWTs are integrity protected by a signature or MAC; don't allow unsecured JWTs with alg none",
        "The relying party must verify integrity based on its own configuration, not on the algorithm in the JWT header",
        "Require and validate iss, aud and exp by default"
      ]
    },
    {
      "title": "FastAPI Tutorial: OAuth2 with Password (and hashing), Bearer with JWT tokens",
      "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
      "version": "FastAPI docs (current); installed fastapi 0.162.0",
      "verified": "2026-11-12",
      "claims": [
        "The tutorial uses PyJWT, HS256 and an exp claim",
        "Generate the secret with openssl rand -hex 32 and don't use the example value",
        "sub should be a unique identifier across the application and a string"
      ]
    },
    {
      "title": "OWASP Secrets Management Cheat Sheet",
      "url": "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
      "version": "OWASP Cheat Sheet Series (current)",
      "verified": "2026-11-12",
      "claims": [
        "Secrets hardcoded in source code are a core problem; use secrets detection, for example a pre-commit hook",
        "Exposed keys should be revoked immediately and rotated",
        "Environment variables are accessible to all processes and may end up in logs or dumps; they are not recommended unless other methods (such as orchestrator injection) aren't possible"
      ]
    },
    {
      "title": "secrets: Generate secure random numbers for managing secrets",
      "url": "https://docs.python.org/3.12/library/secrets.html",
      "version": "Python 3.12 docs; installed Python 3.12.3",
      "verified": "2026-11-12",
      "claims": ["token_hex(nbytes) returns nbytes of randomness as hex; 32 bytes (256 bits) is believed sufficient for typical use"]
    }
  ]
}
---
## 1. A JWT is a signed note, not a sealed one

A JWT is three base64url-encoded parts joined by dots: `header.payload.signature`.

```quiz
{ "id": "q1", "type": "output",
  "prompt": "What does this print?",
  "code": "import base64, json\nimport jwt\n\ntoken = jwt.encode({\"sub\": \"42\", \"role\": \"user\"}, \"k\" * 32, algorithm=\"HS256\")\nheader, payload, signature = token.split(\".\")\nprint(json.loads(base64.urlsafe_b64decode(header + \"==\")))\nprint(json.loads(base64.urlsafe_b64decode(payload + \"==\")))",
  "answer": "{'alg': 'HS256', 'typ': 'JWT'}\n{'sub': '42', 'role': 'user'}",
  "explanation": "No key was needed to read the header or the payload. Base64url is an encoding, not encryption. The == padding is added because JWTs strip it." }
```

So:

- **Anyone holding a token can read it.** Never put secrets in it (no password hash, no internal notes).
- **Anyone can write a new payload.** The **signature** is the only part that proves the server issued it. With HS256 it's an HMAC of `header.payload` with the server's secret key. Change one character of the payload, and the signature no longer matches.
- **So the payload means nothing until the signature is verified**, with a key and an algorithm the *server* chose.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "A user can't see the role claim inside their own HS256 access token without the server's secret.", "answer": false,
  "explanation": "The payload is only base64url-encoded, so anyone can read it. The secret protects integrity (nobody can change it unnoticed), not confidentiality." }
```

## 2. Trusting the payload: the bug you fixed in Go

Here's the Python version of payload-trusting parsing: decode without verification, then believe the role:

```quiz
{ "id": "q3", "type": "output", "label": "Debugging",
  "prompt": "The attacker swaps the payload and keeps the old signature. What does this print?",
  "code": "import base64, json\nimport jwt\n\nkey = \"k\" * 32\ntoken = jwt.encode({\"sub\": \"42\", \"role\": \"user\"}, key, algorithm=\"HS256\")\nheader, payload, signature = token.split(\".\")\nevil = base64.urlsafe_b64encode(json.dumps({\"sub\": \"42\", \"role\": \"admin\"}).encode()).rstrip(b\"=\").decode()\nforged = f\"{header}.{evil}.{signature}\"\n\nprint(jwt.decode(forged, options={\"verify_signature\": False})[\"role\"])\ntry:\n    jwt.decode(forged, key, algorithms=[\"HS256\"])\nexcept jwt.InvalidTokenError as exc:\n    print(type(exc).__name__)",
  "answer": "admin\nInvalidSignatureError",
  "explanation": "Without verification, the forged payload is accepted and the user is admin. With the key and a fixed algorithm list, the signature check fails. PyJWT's docs call verify_signature=False ill-advised unless you understand what you're doing." }
```

`options={"verify_signature": False}` has legitimate uses (debugging, reading the header to pick a key), but **never** before an authorization decision.

**The algorithm comes from the server, not the token.** The header says which algorithm was used, and the attacker writes the header. A classic attack sets `"alg": "none"` with an empty signature. The OWASP REST Security Cheat Sheet says the server must verify according to its own configuration. In PyJWT, that's the `algorithms=[...]` list, and PyJWT refuses to decode without one:

```quiz
{ "id": "q4", "type": "output",
  "prompt": "What does this print?",
  "code": "import jwt\n\nnone_token = jwt.encode({\"sub\": \"1\", \"role\": \"admin\"}, None, algorithm=\"none\")\nprint(none_token.endswith(\".\"))\nfor algorithms in ([\"HS256\"], None):\n    try:\n        jwt.decode(none_token, \"k\" * 32, algorithms=algorithms)\n    except jwt.InvalidTokenError as exc:\n        print(type(exc).__name__)",
  "answer": "True\nInvalidAlgorithmError\nDecodeError",
  "explanation": "An alg-none token has an empty signature, so it ends with a dot. With algorithms=[\"HS256\"], PyJWT rejects the alg it wasn't told to allow. With no algorithms list, PyJWT refuses to decode at all (DecodeError: it is required that you pass in a value for algorithms)." }
```

## 3. Claims: who, for whom, until when

The registered claims from RFC 7519 that an access token should carry:

| Claim | Meaning | Checked how |
|---|---|---|
| `sub` | the subject: who the token is about | a **string**, unique in your app, e.g. `"42"` (PyJWT rejects a non-string sub) |
| `iss` | who issued it | `issuer="chat-auth"` |
| `aud` | who it's for | `audience="chat-api"`: a token for your admin API must not work on the chat API |
| `exp` | expiry time | checked automatically when present; `require` makes it mandatory |
| `iat` | issued at | lets you reject tokens issued before, say, a password change |

OWASP's REST cheat sheet: require and validate `iss`, `aud` and `exp` by default. Each failure has its own exception, all subclasses of `jwt.InvalidTokenError`. These were run on this machine with PyJWT 2.15.1:

| Token problem | Exception |
|---|---|
| signed with another key, or payload changed | `InvalidSignatureError` |
| `exp` in the past | `ExpiredSignatureError` |
| `aud` doesn't match, or `audience=` not passed for a token that has `aud` | `InvalidAudienceError` |
| `iss` doesn't match | `InvalidIssuerError` |
| a required claim missing | `MissingRequiredClaimError` |
| `sub` not a string | `InvalidSubjectError` |
| not a JWT at all | `DecodeError` |

```quiz
{ "id": "q5", "type": "output",
  "prompt": "What does this print?",
  "code": "from datetime import datetime, timedelta, timezone\nimport jwt\n\nkey = \"k\" * 32\nnow = datetime.now(timezone.utc)\ntoken = jwt.encode({\"sub\": \"42\", \"aud\": \"chat-api\", \"exp\": now + timedelta(minutes=5)}, key, algorithm=\"HS256\")\nfor kwargs in ({}, {\"audience\": \"admin-api\"}, {\"audience\": \"chat-api\"}):\n    try:\n        print(jwt.decode(token, key, algorithms=[\"HS256\"], **kwargs)[\"sub\"])\n    except jwt.InvalidTokenError as exc:\n        print(type(exc).__name__)",
  "answer": "InvalidAudienceError\nInvalidAudienceError\n42",
  "explanation": "A token with an aud claim is rejected unless the decoder says who it is (audience=) and matches. Only audience=\"chat-api\" succeeds." }
```

**Expiry and leeway:** keep access tokens short-lived (the FastAPI tutorial uses 15 to 30 minutes). PyJWT's `leeway=` (seconds or a timedelta) tolerates small clock differences between servers. Keep it to seconds, not minutes.

Here's the whole pattern on a different kind of token, a signed chat-invite link:

```python
KEY_ENV = "INVITE_LINK_KEY"


def invite_key() -> str:
    key = os.environ.get(KEY_ENV)
    if not key or len(key.encode()) < 32:
        raise RuntimeError(f"set {KEY_ENV} (32+ bytes)")
    return key


def make_invite(chat_id: int, hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": f"chat:{chat_id}", "aud": "chat-invites", "iat": now, "exp": now + timedelta(hours=hours)}
    return jwt.encode(claims, invite_key(), algorithm="HS256")


def read_invite(link_token: str) -> int:
    claims = jwt.decode(link_token, invite_key(), algorithms=["HS256"], audience="chat-invites",
                        options={"require": ["exp", "sub", "aud"]})
    return int(claims["sub"].removeprefix("chat:"))
```

```console
$ python3 invite_links.py      # sets the key, makes a link, reads it; then an expired one; then no key
2 7
ExpiredSignatureError
RuntimeError: set INVITE_LINK_KEY (32+ bytes)
```

`sub` is prefixed (`chat:7`) because the FastAPI tutorial recommends that `sub` be unique across the whole application: user 7 and chat 7 must not be confused. The `aud` is different from your access tokens', so an invite link can never be used as a login token.

## 4. The secret: out of the code, fail closed

The secret is the whole security of HS256: whoever has it can mint a token for any user. So:

- **Never in the code or in Git.** Once committed, it's in every clone, fork and backup. If that happens, rotating it (a new secret) is the fix; deleting the line isn't. OWASP's secrets cheat sheet recommends revoking exposed keys immediately and scanning for secrets before commit, for example with a pre-commit hook.
- **Load it at runtime.** The simplest way is an environment variable, set by the deployment and never committed. OWASP points out its weakness: environment variables are visible to the whole process and can leak into logs or crash dumps. Larger setups therefore inject secrets from a secrets manager or the orchestrator. Either way, the code just reads a value it was given.
- **Fail closed.** If the variable is missing or too short, raise and refuse to start or serve. A fallback like `os.environ.get("SECRET", "dev-secret")` is the hardcoded secret again, waiting for the day production forgets to set it.
- **Make it long and random.** The FastAPI tutorial uses `openssl rand -hex 32`. The Python equivalent is `secrets.token_hex(32)`: 32 random bytes, the size the `secrets` docs call sufficient. PyJWT warns when an HS256 key is shorter than 32 bytes.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "Which is the safest way for the chat API to get its JWT secret?",
  "options": ["Read it at runtime from configuration the deployment injects (an env var or a secrets manager), and refuse to start if it's missing", "`SECRET = os.environ.get(\"JWT_SECRET\", \"change-me\")`", "A constant in settings.py that is excluded from code review", "Generate a new random secret every time the process starts"], "answer": 0,
  "explanation": "The default value is a hardcoded secret in disguise. A constant is in Git. A per-start random secret logs everyone out on every restart and breaks with more than one server. Injected configuration that fails closed is the safe pattern." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "You once replaced payload-trusting JWT parsing in a Go service with signature verification. Explain to a junior developer, in three or four sentences, what an attacker could do before the fix, and which checks the fixed decoder must perform.",
  "model": "Before the fix, the server read the claims without checking the signature, so anyone could base64-encode their own payload (another user id, role: admin) and be treated as that user. The fixed decoder must verify the signature with the server's key and a fixed list of algorithms (never the header's alg, and never none), then check exp, and check that aud and iss are the expected values, requiring those claims to be present. Only after all of that may the code read sub and role.",
  "explanation": "Verify first, with server-chosen key and algorithm; then validate the claims; only then trust them." }
```

## 5. Your turn

The exercise's `tokens.py` has both review findings from your Go history: a hardcoded secret and a decoder that verifies nothing. Fix it.

```exercise
WEB.M06.L02.E1
```
