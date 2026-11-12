---
{
  "id": "OPS.M01.L02",
  "title": "Layer caching, .dockerignore, multi-stage builds and HEALTHCHECK",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["OPS.M01.L01"],
  "objectives": [
    "Order Dockerfile instructions so a code change doesn't reinstall dependencies, and explain why with the cache rule",
    "Write a .dockerignore that keeps local junk and secret files out of the build context",
    "Read a multi-stage build and say what ends up in the final image",
    "Add a HEALTHCHECK whose command exits 0 when healthy and 1 when not, without tools the image doesn't have"
  ],
  "why": "A Dockerfile that reinstalls every dependency on each commit turns a 5-second rebuild into minutes, in CI and on your laptop. A missing .dockerignore can copy your .env into the image. And without a health check, Compose and orchestrators only know that the process exists, not that it answers.",
  "applications": [
    "Fast rebuilds during development and in CI",
    "Smaller images that don't ship compilers or local files",
    "Containers whose health status is healthy only when the API actually responds, which Compose can wait for"
  ],
  "exercises": ["OPS.M01.L02.E1"],
  "sources": [
    {
      "title": "Docker build cache",
      "url": "https://docs.docker.com/build/cache/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["When a layer changes it is rebuilt, and all layers after it are rebuilt too, even if they would build the same"]
    },
    {
      "title": "Optimize cache usage in builds",
      "url": "https://docs.docker.com/build/cache/optimize/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Steps that change often go near the end; copy package management files and install dependencies before copying the project files", "A .dockerignore in the root of the build context excludes files from the context", "RUN --mount=type=cache,target=/root/.cache/pip keeps pip's cache between builds"]
    },
    {
      "title": "Build context (.dockerignore files)",
      "url": "https://docs.docker.com/build/concepts/context/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [".dockerignore is looked up in the root of the context", "It is a newline-separated list of patterns similar to shell globs"]
    },
    {
      "title": "Multi-stage builds",
      "url": "https://docs.docker.com/build/building/multi-stage/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Multiple FROM statements; stages can be named with AS", "COPY --from copies artifacts from an earlier stage, leaving behind everything you don't want in the final image"]
    },
    {
      "title": "Dockerfile reference: HEALTHCHECK",
      "url": "https://docs.docker.com/reference/dockerfile/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Options --interval (30s), --timeout (30s), --start-period (0s), --start-interval (5s), --retries (3)", "Exit status 0 healthy, 1 unhealthy, 2 reserved", "Only the last HEALTHCHECK takes effect", "Status starts as starting, becomes healthy, or unhealthy after consecutive failures", "Probe failures during the start period don't count towards retries", "A container with a health check has a health status; docker inspect shows the probe output"]
    },
    {
      "title": "Building best practices",
      "url": "https://docs.docker.com/build/building/best-practices/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Combine apt-get update with apt-get install in the same RUN; removing /var/lib/apt/lists reduces image size", "Multi-stage builds reduce the size of the final image"]
    },
    {
      "title": "FastAPI in Containers - Docker",
      "url": "https://fastapi.tiangolo.com/deployment/docker/",
      "version": "FastAPI docs (current; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": ["Copy only the requirements file first; it rarely changes so the install step stays cached", "--no-cache-dir tells pip not to keep downloaded packages, which only helps if pip runs again"]
    }
  ]
}
---
*Every `docker` command in this lesson is **not run on this machine (Docker unavailable)**; behaviour per the cited docs. The Python snippets are real runs.*

## 1. The cache rule, and why order matters

`docker build` caches each layer. The rule from Docker's cache docs is short: **when a layer changes, it is rebuilt, and so is every layer after it**, even if they would produce the same result.

`COPY` changes whenever any copied file changes. So in this Dockerfile, editing one line of your code reruns `pip install` on every build:

```dockerfile
COPY . .
RUN pip install --no-cache-dir -r requirements.txt     # reruns after every code edit
```

The fix is to copy what changes **rarely** first. Docker's own example copies the package manifest, installs, and only then copies the project; FastAPI's Docker guide does the same with `requirements.txt`.

Here is a toy model of that rule. Each step's cache key depends on the previous key, the instruction and the files it copies. It's a simplification, but it follows the rule above:

```python
import hashlib

# A toy model of Docker's build cache: a step's key depends on the previous key,
# the instruction text and the content of the files it copies.
def build(steps, files, cache):
    key = ""
    for line, copies in steps:
        content = "".join(files[name] for name in copies)
        key = hashlib.sha256((key + line + content).encode()).hexdigest()
        print("CACHED" if key in cache else "RUN   ", line)
        cache.add(key)


files = {"requirements.txt": "fastapi==0.162.0", "notes/api.py": "v1"}
everything = list(files)
slow = [("COPY . .", everything), ("RUN pip install ...", [])]
fast = [("COPY requirements.txt .", ["requirements.txt"]), ("RUN pip install ...", []),
        ("COPY notes/ notes/", ["notes/api.py"])]

for name, steps in [("slow", slow), ("fast", fast)]:
    cache = set()
    build(steps, files, cache)                                   # first build fills the cache
    print(f"--- {name}: rebuild after editing notes/api.py")
    build(steps, {**files, "notes/api.py": "v2"}, cache)
```

```console
RUN    COPY . .
RUN    RUN pip install ...
--- slow: rebuild after editing notes/api.py
RUN    COPY . .
RUN    RUN pip install ...
RUN    COPY requirements.txt .
RUN    RUN pip install ...
RUN    COPY notes/ notes/
--- fast: rebuild after editing notes/api.py
CACHED COPY requirements.txt .
CACHED RUN pip install ...
RUN    COPY notes/ notes/
```

In Go terms: it's like `go mod download` running only when `go.mod`/`go.sum` change, which is exactly why Go Dockerfiles copy those two files first.

Two related habits:

- `pip install --no-cache-dir`: pip's download cache only pays off if pip runs again on the same filesystem, which never happens inside an image layer. FastAPI's guide uses it for that reason.
- Want a cache that survives *between* builds without being stored in the image? `RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt` (from Docker's cache-optimisation page). That's an extra, not a requirement.

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "The Dockerfile is: FROM, WORKDIR, `COPY requirements.txt .`, `RUN pip install ...`, `COPY notes/ notes/`, USER, CMD. You change only `requirements.txt`. Which steps rerun?",
  "options": ["COPY requirements.txt and everything after it", "Only RUN pip install", "Only COPY requirements.txt", "Everything, including FROM"], "answer": 0,
  "explanation": "The COPY layer changed, so it and every later layer rebuild. That's expected: new dependencies need a new install. FROM and WORKDIR above it stay cached." }
```

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "Moving `COPY . .` above `RUN pip install` makes no difference to rebuild time, because pip skips packages that are already installed.", "answer": false,
  "explanation": "With COPY . . first, any code change invalidates the pip install layer, so it reruns from a fresh layer where nothing is installed. Layer caching, not pip, is what saves the time." }
```

## 2. .dockerignore: what the builder gets to see

`docker build .` sends the **build context** (the folder, `.`) to the builder. `COPY . .` can only copy from that context, and it copies *everything* in it. A `.dockerignore` file in the root of the context lists patterns to leave out, in a glob syntax similar to `.gitignore`:

```text
# .dockerignore for the notes service
.git
.venv
__pycache__/
.env
```

- **`.git`, `.venv`, caches**: big, useless in the image, and `.venv` belongs to your machine's Python anyway; the image installs its own dependencies.
- **`.env`**: the file where local secrets live. Without this line, the next `COPY . .` puts your secrets into an image layer, exactly the leak from lesson 1, just less visible.

`.dockerignore` and `.gitignore` are separate files. Git ignoring `.env` doesn't stop Docker from copying it.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "If `.env` is in .gitignore, `COPY . .` won't copy it into the image.", "answer": false,
  "explanation": "Docker doesn't read .gitignore. The build context is whatever is in the folder; only .dockerignore filters it." }
```

## 3. Multi-stage builds

In Go you'd build in a `golang` image and ship only the binary. A **multi-stage build** does the same thing with several `FROM` lines. Each `FROM` starts a fresh stage, and `COPY --from=<stage>` picks artifacts out of an earlier one; Docker's docs put it as *leaving behind everything you don't want in the final image*.

For Python, the artifact is usually a virtual environment, built in a stage that has compilers:

```dockerfile
FROM python:3.12.16-slim-trixie AS build
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12.16-slim-trixie
RUN groupadd -r svc && useradd --no-log-init -r -g svc svc
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /srv
COPY notes/ notes/
USER svc
CMD ["uvicorn", "notes.api:api", "--host", "0.0.0.0", "--port", "8080"]
```

- The compilers (`build-essential`) exist only in the `build` stage. The final image has Python, the venv and your code.
- `apt-get update` and `install` share one `RUN`, and the apt lists are deleted in the same layer: Docker's best-practices page recommends both.
- **Why the same base image and the same path?** A venv isn't self-contained. It points at its base interpreter by absolute path, and its scripts hard-code their own location. You can see both on this machine:

```console
$ head -1 .venv/bin/pytest
#!/root/go/metis/.venv/bin/python3
$ python3 -m venv venv && ls -l venv/bin/python3.12
lrwxrwxrwx 1 root root 19 Nov 12 19:15 venv/bin/python3.12 -> /usr/bin/python3.12
```

So copy `/opt/venv` to `/opt/venv`, into an image that has the same Python. Do you need multi-stage? Only when a dependency must compile something, as the python image page warns can happen on slim. Pure-Python requirements like FastAPI install fine in a single stage.

```quiz
{ "id": "q4", "type": "choice",
  "prompt": "In the multi-stage example above, what's in the final image?",
  "options": ["The slim base, /opt/venv with the dependencies, and notes/", "Everything from both stages", "Only notes/ and the compilers", "Only /opt/venv; the base image is discarded"], "answer": 0,
  "explanation": "The final image starts from its own FROM and receives only what COPY --from and the later instructions add. build-essential stays behind in the build stage." }
```

## 4. HEALTHCHECK: does the app answer?

A running process isn't a working API: uvicorn can be up while the app is deadlocked or still starting. `HEALTHCHECK` tells Docker to run a command inside the container periodically:

```dockerfile
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]
```

- **Exit status** decides: `0` healthy, `1` unhealthy. `2` is reserved; don't use it.
- The status starts as `starting`, becomes `healthy` after a pass, and `unhealthy` after `--retries` consecutive failures. Failures during `--start-period` don't count yet.
- Defaults if you omit them: interval 30s, timeout 30s, start-period 0s, retries 3. Only the last `HEALTHCHECK` in the file counts.
- **Why Python instead of curl?** The slim image contains only the minimal packages needed to run Python, so don't assume curl is there. Python and `urllib` definitely are. `urlopen` raises on a refused connection, a timeout or an HTTP error status, and an uncaught exception makes Python exit with 1. Here it is against a local `python3 -m http.server`, where `/missing` returns 404:

```console
$ python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8799/missing', timeout=2)"
Traceback (most recent call last):
  ...
urllib.error.HTTPError: HTTP Error 404: File not found
$ echo $?
1
```

The endpoint itself is one line in FastAPI: a `GET /healthz` that returns `{"status": "ok"}`. Keep it cheap. It runs every few seconds, forever.

```console
$ docker inspect notes-1
```
*Not run on this machine (Docker unavailable). Per the Dockerfile reference, a container with a health check has a health status in addition to its normal status, and `docker inspect` shows the probe's output.*

```quiz
{ "id": "q5", "type": "output",
  "prompt": "A health-check command fails with an uncaught exception. What exit code does Docker see? (This runs the probe as a child process, as Docker would.)",
  "code": "import subprocess, sys\nprobe = \"raise ConnectionRefusedError('nothing on :8080')\"\nr = subprocess.run([sys.executable, \"-c\", probe], capture_output=True)\nprint(r.returncode)",
  "answer": "1",
  "explanation": "An uncaught exception makes Python exit with status 1, which HEALTHCHECK reads as unhealthy. No try/except needed in the probe." }
```

```quiz
{ "id": "q6", "type": "choice", "label": "Debugging",
  "prompt": "A container stays `unhealthy` forever. Its HEALTHCHECK is `CMD [\"curl\", \"-f\", \"http://localhost:8000/health\"]` on a python:3.12.16-slim image, and the app answers on /health. What do you check first?",
  "options": ["Whether curl exists in the image at all; probe with python's urllib instead", "Whether --retries is high enough", "Whether EXPOSE 8000 is set", "Whether the CMD uses exec form"], "answer": 0,
  "explanation": "If the probe command can't even run, it fails every time. slim promises only what's needed to run Python, so either install curl or use Python, which is guaranteed to be there." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Why should a health endpoint be cheap, and what would go wrong if it ran a slow database report?",
  "model": "It runs every interval for the life of every container. A slow check adds constant load and can exceed --timeout, marking a working container unhealthy (and making Compose or an orchestrator wait on or replace it). Check that the process answers, and at most do a trivial dependency ping.",
  "explanation": "Health checks are frequent, so they must be fast and side-effect free." }
```

## 5. Your turn

The exercise gives you a working Dockerfile in lesson 1's style for the FastAPI app (`app.main:app`, port 8000, `GET /health`). Make it cache-friendly, add the health check, and write the `.dockerignore`. The tests parse both files.

```exercise
OPS.M01.L02.E1
```
