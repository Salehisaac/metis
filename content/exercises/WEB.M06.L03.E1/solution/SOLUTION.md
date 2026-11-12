```python
def get_current_user(request: Request, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_error()
    user = find_user_by_id(request.app.state.users, user_id)
    if user is None:
        raise credentials_error()
    return user


    @app.post("/auth/token")
    def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
        user = app.state.users.get(form.username)
        stored = user.password_hash if user is not None else DUMMY_HASH
        if not verify_password(form.password, stored) or user is None:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        return Token(access_token=create_access_token(user.id), token_type="bearer")
```

**Why it works**

- **One answer for every failed login.** Unknown user and wrong password produce the same status and body, so the API doesn't reveal which usernames exist. `verify_password` runs *first* in the condition, with `DUMMY_HASH` standing in for a missing user, so both cases also cost the same hashing time. The FastAPI tutorial does the same thing to prevent timing-based username enumeration.
- **One answer for every bad token.** `decode_access_token` raises a subclass of `jwt.InvalidTokenError` for a bad signature, expiry, wrong audience or issuer, or a missing claim. `int(...)` raises `ValueError` for a non-numeric `sub`. Both become the same 401. A deleted user is also a 401: the token is genuine, but it no longer identifies anyone.
- **401 carries `WWW-Authenticate: Bearer`.** The FastAPI docs: every 401 is supposed to return a `WWW-Authenticate` header, with the value `Bearer` for bearer tokens. `OAuth2PasswordBearer` already does this when the header is missing.
- **Dependencies chain.** `read_me` depends on `get_current_active_user`, which depends on `get_current_user`, which depends on `oauth2_scheme`. Each layer adds one rule, and any endpoint can pick the layer it needs.

**Why form fields?** The OAuth2 password flow requires `username` and `password` as form data, so standard OAuth2 clients and the `/docs` "Authorize" button work with this endpoint. `OAuth2PasswordRequestForm` declares exactly those fields (it needs the `python-multipart` package). A JSON body is answered with 422.

**Alternatives:** an API used only by your own clients could take a JSON body (a Pydantic model with username and password) instead; it just isn't standard OAuth2. And look users up by id in a dict or a database query instead of scanning `users.values()`. With the database from WEB.M05, `get_current_user` would also depend on `get_session` and call `session.get(User, user_id)`.
