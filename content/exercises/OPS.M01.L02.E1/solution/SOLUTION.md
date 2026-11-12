```dockerfile
FROM python:3.12.16-slim
WORKDIR /app
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app/ /app/app/
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```text
# .dockerignore
.git
.venv
__pycache__
*.pyc
.pytest_cache
.env
.env.*
```

**Why it works**

- **Cache order.** Docker rebuilds a changed layer and every layer after it. `requirements.txt` changes rarely, so `COPY requirements.txt` and `pip install` stay cached across code edits; only `COPY app/` and the lines below it rerun. With `COPY . .` first, any edit (even a README) invalidated the install.
- **`--no-cache-dir`**: pip's download cache only helps if pip runs again on the same machine, which never happens inside an image layer, so it's dead weight.
- **HEALTHCHECK**: Docker runs the command inside the container. `urlopen` raises on a refused connection, a timeout or a 4xx/5xx response, so Python exits with 1 (unhealthy); a 200 lets it exit 0 (healthy). `--start-period` gives uvicorn time to boot before failures count. `timeout=3` inside the script is shorter than `--timeout=5s`, so Python reports the failure itself instead of being killed.
- **`.dockerignore`** keeps the build context small (no `.git`, no `.venv` that belongs to your machine anyway) and, most importantly, keeps `.env` from being sent to the builder and copied into the image by a future `COPY . .`.

**Alternatives**

- `RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt` keeps pip's cache *outside* the image, between builds, which helps when dependencies change often. This exercise's tests require `--no-cache-dir` on every pip install, so they don't accept that variant; it's a valid choice in a real project.
- A multi-stage build (install into a venv in a builder stage, `COPY --from=` it into the final stage) matters once you need compilers for dependencies; the tests accept it as long as the order holds.
- `curl -f` works too if you `apt-get install` it, at the cost of a bigger image.
