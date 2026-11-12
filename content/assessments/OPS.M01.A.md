---
{ "id": "OPS.M01.A", "module": "OPS.M01", "title": "OPS.M01 module assessment: Dockerfiles and Compose", "minutes": 15 }
---
Answer without the lessons open and without AI. Only your **first** answer counts. If you miss more than one, ask the mentor for practice on that topic before OPS.M02.

```quiz
{ "id": "a1", "type": "choice",
  "prompt": "Which Dockerfile line order rebuilds fastest after you edit only `app/main.py`?",
  "options": ["COPY requirements.txt . / RUN pip install -r requirements.txt / COPY app/ app/", "COPY . . / RUN pip install -r requirements.txt", "COPY app/ app/ / COPY requirements.txt . / RUN pip install -r requirements.txt", "RUN pip install -r requirements.txt / COPY . ."], "answer": 0,
  "explanation": "A changed layer rebuilds itself and everything after it. Only the first order keeps the install layer above the code that changed. The last option fails outright: requirements.txt isn't in the image yet when pip runs." }
```

```quiz
{ "id": "a2", "type": "output",
  "prompt": "Docker parses an exec-form CMD as JSON. What does this print?",
  "code": "import json\nfor cmd in ['[\"uvicorn\", \"app.main:app\"]', \"[uvicorn, app.main:app]\"]:\n    try:\n        print(len(json.loads(cmd)))\n    except json.JSONDecodeError:\n        print(\"shell\")",
  "answer": "2\nshell",
  "explanation": "The first is a valid JSON array of two strings: exec form. The second has unquoted words, so it isn't JSON and Docker runs it through /bin/sh -c (shell form), where uvicorn won't receive SIGTERM directly." }
```

```quiz
{ "id": "a3", "type": "truefalse",
  "prompt": "Adding `USER app` as the very first line after FROM is the safest place for it.", "answer": false,
  "explanation": "USER applies to every following instruction. The user has to be created first, and pip install has to run as root, so USER goes after both, near the end." }
```

```quiz
{ "id": "a4", "type": "choice", "label": "Debugging",
  "prompt": "`docker compose up` sometimes fails with the API logging `connection refused` to `db:5432`. The api service has `depends_on: [db]` and db has no healthcheck. What fixes it properly?",
  "options": ["A pg_isready healthcheck on db plus depends_on: db: condition: service_healthy", "Publishing 5432:5432 on db", "Changing the host in DATABASE_URL to localhost", "Adding EXPOSE 5432 to the api Dockerfile"], "answer": 0,
  "explanation": "The short depends_on waits only for the container to start. Readiness needs a healthcheck and the service_healthy condition. The other options don't touch the race, and localhost would point at the api container itself." }
```

```quiz
{ "id": "a5", "type": "choice",
  "prompt": "Which is the right way to give PostgreSQL its password in compose.yaml that's committed to Git?",
  "options": ["POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set it in .env} with .env uncommitted", "POSTGRES_PASSWORD: changeme, since it's only local", "ENV POSTGRES_PASSWORD=... in the app's Dockerfile", "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}"], "answer": 0,
  "explanation": ":? makes a missing value a loud error and keeps the real value out of Git. A :- default silently ships the weak password, and ENV bakes it into an image anyone with pull access can inspect." }
```

```quiz
{ "id": "a6", "type": "explain", "label": "Application",
  "prompt": "Review this Dockerfile for production in three short points: `FROM python:latest`, `COPY . .`, `RUN pip install -r requirements.txt`, `CMD uvicorn app.main:app --port 8000`.",
  "model": "1) Pin the base: python:3.12.x-slim instead of latest. 2) Copy requirements.txt and install before copying the source (cache), add a .dockerignore (keeps .env and .git out), use --no-cache-dir, and run as a non-root USER. 3) Exec-form CMD with --host 0.0.0.0: shell form doesn't get SIGTERM and 127.0.0.1 is unreachable from outside the container. Optionally add a HEALTHCHECK.",
  "explanation": "Floating base, cache order plus context, root, and shell-form CMD on localhost: the four classic Dockerfile review comments." }
```
