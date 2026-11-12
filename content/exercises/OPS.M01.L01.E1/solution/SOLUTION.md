```dockerfile
FROM python:3.12.16-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why it works**

- **`python:3.12.16-slim`**: `latest` moves whenever the publisher pushes a new image, so two builds of the same commit can get different Pythons. A version tag says which Python you tested on; `slim` keeps only the minimal Debian packages needed to run Python.
- **The secret is gone.** `ENV` values persist in the image and anyone who can pull it can read them with `docker inspect`. The OAuth secret comes from the environment at run time (`docker run -e`, compose `environment:` from an uncommitted `.env`, or a secret file); OPS.M02 builds the Python side of that.
- **`USER appuser` after creating it.** Everything after `USER` (and the running container) uses that account, so a bug in the app can't write to root-owned files. The user is created in a `RUN` before the switch, the way Docker's best-practices page shows. `pip install` stays above `USER` because it writes into the system site-packages.
- **Exec-form `CMD`**: the JSON array runs uvicorn directly as PID 1, so `docker stop`'s SIGTERM reaches it and FastAPI shuts down cleanly. The shell form would run `/bin/sh -c "..."`, and uvicorn wouldn't receive the signal. `--host 0.0.0.0` is needed because uvicorn's default, 127.0.0.1, is unreachable from outside the container.

**Alternatives**

- A numeric user (`USER 10001`) avoids needing a name in `/etc/passwd`. The test accepts it.
- `CMD ["fastapi", "run", "app/main.py", "--port", "8000"]` is what FastAPI's Docker guide uses; `fastapi run` runs uvicorn underneath, but it needs the `fastapi[standard]` extra, which this academy's venv doesn't have.
- Copying `requirements.txt` first so dependency installs are cached is the next lesson's job; here the order didn't matter for correctness.
