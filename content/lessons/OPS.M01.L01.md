---
{
  "id": "OPS.M01.L01",
  "title": "Placement check and a first Dockerfile for FastAPI",
  "difficulty": "intermediate",
  "minutes": 70,
  "prerequisites": ["WEB.M05"],
  "objectives": [
    "Answer a 5-minute placement check on running existing Docker and Compose setups",
    "Explain how Dockerfile instructions become image layers, and how an image differs from a container",
    "Pin a python slim base image by version and say what a tag does and doesn't guarantee",
    "Run the app as a non-root user and start uvicorn with an exec-form CMD on 0.0.0.0",
    "Spot secrets baked into an image through ENV or ARG"
  ],
  "why": "You already run docker compose up on setups someone else wrote. Writing the Dockerfile yourself is where the production decisions live: which Python you ship, who the process runs as, whether it shuts down cleanly and whether a secret ends up inside the image for anyone with pull access to read.",
  "applications": [
    "Packaging a FastAPI service so every environment runs the same Python and dependencies",
    "Reviewing a colleague's Dockerfile for root users, floating tags and leaked secrets",
    "Making containers stop cleanly on deploys instead of being killed after the timeout"
  ],
  "exercises": ["OPS.M01.L01.E1"],
  "sources": [
    {
      "title": "Dockerfile reference",
      "url": "https://docs.docker.com/reference/dockerfile/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [
        "Exec form is parsed as a JSON array and needs double quotes; invalid JSON is treated as shell form",
        "Shell form runs through a command shell; then the executable is not PID 1 and doesn't receive SIGTERM from docker stop",
        "Only the last CMD takes effect; docker run arguments override CMD",
        "ENV values persist in containers run from the image and can be viewed with docker inspect",
        "Build arguments are not recommended for secrets: they are visible in docker history",
        "EXPOSE doesn't publish the port",
        "RUN executes a command and commits the result as a new layer",
        "WORKDIR defaults to / and should be set explicitly",
        "COPY without --chown creates files with UID and GID 0"
      ]
    },
    {
      "title": "Building best practices",
      "url": "https://docs.docker.com/build/building/best-practices/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [
        "Image tags are mutable; pin a digest for full supply-chain integrity",
        "If a service can run without privileges, use USER to change to a non-root user; example groupadd -r / useradd --no-log-init -r -g",
        "CMD should almost always be used in exec form",
        "Each container should have only one concern"
      ]
    },
    {
      "title": "docker container stop",
      "url": "https://docs.docker.com/reference/cli/docker/container/stop/",
      "version": "Docker CLI docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The main process receives SIGTERM, then SIGKILL after a grace period", "The default stop timeout is 10 seconds for Linux containers"]
    },
    {
      "title": "python - Official Image (Docker Hub)",
      "url": "https://hub.docker.com/_/python",
      "version": "Docker Hub tag list as of 2026-11-12",
      "verified": "2026-11-12",
      "claims": [
        "Tags 3.12.16-slim, 3.12-slim, 3.12-slim-trixie and 3.12-slim-bookworm exist",
        "The slim variant contains only the minimal Debian packages needed to run python; packages that compile from source may fail to install"
      ]
    },
    {
      "title": "FastAPI in Containers - Docker",
      "url": "https://fastapi.tiangolo.com/deployment/docker/",
      "version": "FastAPI docs (current; installed fastapi 0.162.0)",
      "verified": "2026-11-12",
      "claims": [
        "Always use the exec form of CMD so FastAPI can shut down gracefully and lifespan events run",
        "Copy only the requirements file first, then the code, to use the build cache"
      ]
    },
    {
      "title": "Uvicorn settings",
      "url": "https://uvicorn.dev/settings/",
      "version": "Uvicorn docs (current); installed uvicorn 0.54.0, default confirmed with uvicorn --help",
      "verified": "2026-11-12",
      "claims": ["--host defaults to 127.0.0.1; use --host 0.0.0.0 to make the app reachable from other machines", "--port defaults to 8000"]
    }
  ]
}
---
Docker is **not installed on this machine**, so every `docker` command below is labelled *Not run on this machine (Docker unavailable)* and shows no output. Behaviour is as described in the cited Docker docs. The exercises check your Dockerfile **statically**: a test parses the file and checks the rules.

## 1. Placement check (5 minutes)

You run existing Docker setups at work. Answer these four without looking anything up, so the mentor can see how much of this module you can skim. Your answers go to the mentor as evidence; a wrong answer here costs nothing.

```quiz
{ "id": "q1", "type": "choice", "label": "Placement",
  "prompt": "What is the relationship between an image and a container?",
  "options": ["An image is a read-only template built from a Dockerfile; a container is a running (or stopped) instance of it", "They are two names for the same thing", "A container is built from a Dockerfile; an image is a container that has stopped", "An image is a compressed container used only for uploads"], "answer": 0,
  "explanation": "docker build produces an image (layers plus metadata). docker run creates a container from it, with its own writable layer and process. One image, many containers, the way one Go binary can run as many processes." }
```

```quiz
{ "id": "q2", "type": "choice", "label": "Placement",
  "prompt": "A compose service has `ports: [\"8080:80\"]`. Which port do you open in your browser on the host?",
  "options": ["8080", "80", "Either one", "Neither: ports only connect containers to each other"], "answer": 0,
  "explanation": "The short syntax is HOST:CONTAINER. The host's 8080 forwards to port 80 inside the container." }
```

```quiz
{ "id": "q3", "type": "truefalse", "label": "Placement",
  "prompt": "`EXPOSE 8000` in a Dockerfile makes the app reachable at localhost:8000 on your machine.", "answer": false,
  "explanation": "EXPOSE is documentation for whoever runs the image; it doesn't publish anything. You publish with docker run -p 8000:8000 or compose ports." }
```

```quiz
{ "id": "q4", "type": "truefalse", "label": "Placement",
  "prompt": "With `depends_on: [db]` (the short list form), Compose waits until PostgreSQL accepts connections before starting the app.", "answer": false,
  "explanation": "The short form only waits for the db container to be started, not ready. Waiting for readiness needs a healthcheck plus condition: service_healthy (lesson 3)." }
```

**If you got all four right**, skim sections 2 and 3 and go straight to section 4. Otherwise read on; nothing here assumes Docker knowledge beyond running it.

## 2. A Dockerfile is a recipe of layers

Go gives you one static binary, so a Go image can be little more than that binary. A Python service needs **an interpreter, your dependencies and your source** at run time. A Dockerfile is the recipe that assembles those:

- `FROM` picks the starting image (here: Debian plus Python).
- Each `RUN` executes a command and **commits the result as a new layer**. `COPY` adds files as a layer too.
- `CMD` doesn't run at build time. It records the default command the container starts with.

`docker build` runs the recipe and produces an image. `docker run` starts a container from it. Here is a complete Dockerfile for a different app than the exercise's: a small notes API whose FastAPI object is `api` in `notes/api.py`, served on port 8080.

```dockerfile
FROM python:3.12.16-slim-trixie
WORKDIR /srv
RUN groupadd -r svc && useradd --no-log-init -r -g svc svc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY notes/ notes/
USER svc
EXPOSE 8080
CMD ["uvicorn", "notes.api:api", "--host", "0.0.0.0", "--port", "8080"]
```

```console
$ docker build -t notes:dev .
$ docker run --rm -p 8080:8080 notes:dev
```
*Not run on this machine (Docker unavailable); behaviour per the cited docs.*

`WORKDIR /srv` sets the directory for every following instruction (and creates it). Without it, you work in `/`, which the Dockerfile reference tells you to avoid. The order of the two `COPY` lines is about build speed. Lesson 2 explains it; for now, notice that requirements come first.

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Which instruction does NOT do any work while `docker build` runs?",
  "options": ["CMD", "RUN", "COPY", "WORKDIR"], "answer": 0,
  "explanation": "CMD only records the default start command in the image's metadata. It runs when a container starts. RUN, COPY and WORKDIR all change the filesystem during the build." }
```

## 3. Pin the base image

A tag is a **movable name**. The Docker docs say it plainly: publishers can update a tag to point to a new image. So `python:latest` is "whatever Python was newest when this machine last pulled". Two builds of the same commit can ship different Python versions, and the next major release can break you on a random Tuesday.

Docker Hub lists, for example, these tags of the official `python` image:

| Tag | What stays fixed |
|---|---|
| `python:latest` | nothing |
| `python:3.12-slim` | Python 3.12; patch releases arrive on rebuild |
| `python:3.12.16-slim` | Python 3.12.16 (the Debian base under it can still be updated) |
| `python:3.12.16-slim-trixie` | Python 3.12.16 on Debian trixie |
| `python@sha256:...` (digest) | the exact bytes; the only truly immutable option |

Pin at least the minor version, and match the Python your tests run on (3.12 here). **slim** contains only the minimal Debian packages needed to run Python, so images are smaller. The trade-off, from the image docs: packages that must compile C code during `pip install` can fail on slim, because the compilers aren't there. Then you either install the build packages or use a multi-stage build (lesson 2).

```quiz
{ "id": "q6", "type": "truefalse",
  "prompt": "`FROM python:3.12-slim` guarantees that every build gets exactly the same Python patch version.", "answer": false,
  "explanation": "3.12-slim moves to each new 3.12.x patch release. Only a full patch tag like 3.12.16-slim pins the Python version, and only a digest pins the exact image." }
```

## 4. Don't run as root

By default the container's process runs as **root**. If an attacker gets code execution through your app, they're root inside the container, which makes every other weakness (a mounted volume, a kernel bug) worse. Docker's guidance: *if a service can run without privileges, use `USER` to change to a non-root user.* A web API never needs root.

Two lines do it. Create a system user and group, then switch:

```dockerfile
RUN groupadd -r svc && useradd --no-log-init -r -g svc svc
USER svc
```

- `-r` creates a system account. `--no-log-init` is the workaround Docker's best-practices page gives for a known problem when `useradd` creates very large UIDs.
- **Order matters.** Everything after `USER` runs as that user: later `RUN` lines and the container itself. Put `pip install` *before* `USER`, because it writes into the system's site-packages.
- Files from `COPY` belong to root (UID 0) unless you pass `--chown`. That's fine and even good: the app can read its code but can't modify it.

A Go comparison: this is the container version of not running your service with `sudo`.

```quiz
{ "id": "q7", "type": "choice", "label": "Debugging",
  "prompt": "A Dockerfile has three lines in some order. A: `RUN pip install --no-cache-dir -r requirements.txt`. B: `USER svc`. C: `RUN groupadd -r svc && useradd --no-log-init -r -g svc svc`. Which order is correct?",
  "options": ["A, C, B", "B, C, A", "C, B, A", "B, A, C"], "answer": 0,
  "explanation": "USER applies to every later instruction. pip install has to run as root (it writes the system site-packages), the user has to exist before USER names it, and USER comes after both. C, A, B would also work." }
```

## 5. Exec-form CMD, and listen on 0.0.0.0

`CMD` has two forms, and only one of them is right for a server:

```dockerfile
CMD uvicorn notes.api:api --host 0.0.0.0 --port 8080             # shell form
CMD ["uvicorn", "notes.api:api", "--host", "0.0.0.0", "--port", "8080"]   # exec form
```

- **Shell form** runs `/bin/sh -c "uvicorn ..."`. The shell is PID 1, uvicorn is its child, and per the Dockerfile reference **the app doesn't receive the SIGTERM from `docker stop`**. `docker stop` then waits out its grace period (10 seconds by default on Linux) and sends SIGKILL, so in-flight requests are cut off and FastAPI's shutdown (lifespan) code never runs. FastAPI's Docker guide says to *always* use exec form for this reason.
- **Exec form** runs uvicorn directly as PID 1, so it gets the signal and shuts down gracefully. Docker's best-practices page: CMD should almost always be in exec form.

The exec form is **parsed as a JSON array**, which means double quotes. Anything that isn't valid JSON silently becomes shell form. You can watch the parser decide:

```python
import json

for cmd in ['["uvicorn", "main:app"]', "['uvicorn', 'main:app']"]:
    try:
        print(json.loads(cmd))
    except json.JSONDecodeError:
        print("not JSON -> shell form")
```

```console
['uvicorn', 'main:app']
not JSON -> shell form
```

The second, **0.0.0.0**: uvicorn's `--host` defaults to `127.0.0.1` (check with `uvicorn --help`). Inside a container, 127.0.0.1 is the *container's own* loopback, so the port you published with `-p` reaches nothing. `--host 0.0.0.0` listens on all interfaces of the container.

```quiz
{ "id": "q8", "type": "output",
  "prompt": "Docker parses exec form as JSON. What does this print?",
  "code": "import json\ncmd = \"['uvicorn', 'app:app']\"\ntry:\n    json.loads(cmd)\n    print(\"exec form\")\nexcept json.JSONDecodeError:\n    print(\"shell form\")",
  "answer": "shell form",
  "explanation": "JSON strings need double quotes, so the single-quoted array isn't valid JSON, and Docker falls back to shell form: /bin/sh -c becomes PID 1." }
```

```quiz
{ "id": "q9", "type": "choice", "label": "Debugging",
  "prompt": "The container runs `CMD [\"uvicorn\", \"main:app\", \"--port\", \"8000\"]` with `-p 8000:8000`. The logs say uvicorn is running, but curl localhost:8000 on the host fails. Most likely cause?",
  "options": ["uvicorn listens on 127.0.0.1 inside the container; add --host 0.0.0.0", "EXPOSE 8000 is missing", "Exec form doesn't support ports", "The host port must differ from the container port"], "answer": 0,
  "explanation": "The default host 127.0.0.1 is the container's own loopback, unreachable through the published port. EXPOSE wouldn't help: it publishes nothing." }
```

## 6. No secrets in the image

Imagine a past bug: an OAuth client secret was hardcoded in the source and shipped. Removing it from the code later doesn't remove it from images already built, pushed and pulled. A Dockerfile can make the same mistake:

```dockerfile
ENV STRIPE_API_KEY=sk_live_...        # wrong: stored in the image
ARG DB_PASSWORD                       # wrong: visible in docker history
```

- `ENV` values **persist in the image**. Anyone who can pull it can read them with `docker inspect`.
- Build arguments (`ARG`) are visible in `docker history`; the Dockerfile reference says not to use them for secrets.
- Config that is safe to publish (`ENV PYTHONUNBUFFERED=1`, a default port) is fine in `ENV`.

**Secrets arrive at run time**: `docker run -e`, compose `environment:` filled from an uncommitted `.env` file, or a secret file mounted into the container (lesson 3). OPS.M02 builds the Python side: reading them from the environment and failing fast when they're missing.

```quiz
{ "id": "q10", "type": "truefalse",
  "prompt": "If you delete an `ENV API_TOKEN=...` line and rebuild, the token is gone from every copy of the old image as well.", "answer": false,
  "explanation": "Old images are immutable and may already sit in registries and on other machines. Rotate (revoke and replace) a leaked secret; deleting the line only fixes future images." }
```

```quiz
{ "id": "q11", "type": "explain", "label": "Application",
  "prompt": "A teammate says: 'Our registry is private, so ENV DATABASE_PASSWORD=... in the Dockerfile is fine.' What do you answer?",
  "model": "Private isn't secret: everyone with pull access (CI, other teams, every server) can read ENV with docker inspect, and the value is also in Git history via the Dockerfile. Rotating it means rebuilding images. Pass it at run time (environment from the deploy system or a mounted secret file) instead.",
  "explanation": "Images and Git history are copied widely; secrets belong to the runtime environment." }
```

## 7. Your turn

The exercise is a **fix**: a colleague's Dockerfile for a FastAPI app (`app.main:app`, port 8000) breaks the four rules from sections 3 to 6. The tests parse it, so you don't need Docker.

```console
$ .venv/bin/python tools/scaffold.py OPS.M01.L01.E1
$ cd workspace/OPS.M01.L01.E1
$ ../../.venv/bin/pytest
```

```exercise
OPS.M01.L01.E1
```
