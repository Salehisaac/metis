---
{
  "id": "OPS.M01.L03",
  "title": "Compose: app, Postgres and Redis with healthchecks",
  "difficulty": "intermediate",
  "minutes": 75,
  "prerequisites": ["OPS.M01.L02"],
  "objectives": [
    "Write a compose file with an app built from a Dockerfile plus pinned PostgreSQL and Redis services",
    "Explain how services find each other by name on the default network, and HOST:CONTAINER port mapping",
    "Make the app wait for real readiness with healthchecks and depends_on condition: service_healthy",
    "Keep secrets out of the compose file with ${VAR:?message} from an uncommitted .env, or Compose secrets",
    "Keep database data in a named volume and know what docker compose down does and doesn't remove"
  ],
  "why": "Compose files are where 'works on my machine' gets written down for the whole team. The two classic bugs are the app crashing on boot because the database isn't ready yet, and a password committed in the YAML. Both have a precise fix.",
  "applications": [
    "A one-command local stack for a FastAPI service with PostgreSQL and Redis",
    "Integration tests in CI against real services started by Compose",
    "Reviewing compose files for start-up races and committed secrets"
  ],
  "exercises": ["OPS.M01.L03.E1"],
  "sources": [
    {
      "title": "Compose file reference: services",
      "url": "https://docs.docker.com/reference/compose-file/services/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": [
        "healthcheck test: list starting with NONE, CMD or CMD-SHELL; a string equals CMD-SHELL; disable: true",
        "Short depends_on syntax doesn't wait for dependencies to be healthy",
        "Long syntax conditions: service_started (same as short), service_healthy, service_completed_successfully; restart: true",
        "environment takes precedence over env_file",
        "ports short syntax [HOST:]CONTAINER; HOST:CONTAINER should always be a quoted string; binds to 0.0.0.0 if no host IP"
      ]
    },
    {
      "title": "Control startup and shutdown order in Compose",
      "url": "https://docs.docker.com/compose/how-tos/startup-order/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Compose starts containers in dependency order but waits only until they are running, not ready", "Example: postgres:18 with pg_isready healthcheck and depends_on condition: service_healthy, restart: true"]
    },
    {
      "title": "Networking in Compose",
      "url": "https://docs.docker.com/compose/how-tos/networking/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Compose sets up a single default network; each service registers its name with an internal DNS server", "Service-to-service traffic uses the CONTAINER_PORT"]
    },
    {
      "title": "Set, use, and manage variables in a Compose file with interpolation",
      "url": "https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The .env file in the project directory is the default source for interpolation; shell environment variables take precedence", "${VAR:?error} stops with an error if VAR is unset or empty"]
    },
    {
      "title": "Compose file reference: Interpolation",
      "url": "https://docs.docker.com/reference/compose-file/interpolation/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["${VAR:-default} uses the default when VAR is unset or empty", "$$ produces a literal dollar sign (no interpolation)", "An unresolved variable without a default becomes an empty string, with a warning"]
    },
    {
      "title": "Secrets in Compose",
      "url": "https://docs.docker.com/compose/how-tos/use-secrets/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["Passwords in environment variables risk exposure, including in logs", "Top-level secrets with file:, per-service secrets:, mounted at /run/secrets/<name>", "_FILE variables are a convention of some images, e.g. postgres"]
    },
    {
      "title": "postgres - Official Image (Docker Hub)",
      "url": "https://hub.docker.com/_/postgres",
      "version": "Docker Hub page as of 2026-11-12 (tags include 18.6 and 18)",
      "verified": "2026-11-12",
      "claims": ["POSTGRES_PASSWORD is required and must not be empty; POSTGRES_USER and POSTGRES_DB optional", "PostgreSQL 18+ data lives under /var/lib/postgresql (volume there); 17 and earlier: /var/lib/postgresql/data", "POSTGRES_PASSWORD_FILE reads the value from a file"]
    },
    {
      "title": "redis - Official Image (Docker Hub)",
      "url": "https://hub.docker.com/_/redis",
      "version": "Docker Hub page as of 2026-11-12 (tags include 8.10.3, 8.10 and 8)",
      "verified": "2026-11-12",
      "claims": ["redis tags include 8.10 and 8", "The page runs redis-cli from the redis image (Connecting via redis-cli)"]
    },
    {
      "title": "PING (Redis command)",
      "url": "https://redis.io/docs/latest/commands/ping/",
      "version": "Redis docs (current)",
      "verified": "2026-11-12",
      "claims": ["PING returns PONG with no argument; used to test that a connection is alive"]
    },
    {
      "title": "docker compose down",
      "url": "https://docs.docker.com/reference/cli/docker/compose/down/",
      "version": "Docker CLI docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["down removes the services' containers and networks", "-v/--volumes also removes named volumes declared in the file"]
    },
    {
      "title": "Version and name top-level elements",
      "url": "https://docs.docker.com/reference/compose-file/version-and-name/",
      "version": "Docker docs (current, fetched 2026-11-12)",
      "verified": "2026-11-12",
      "claims": ["The top-level version element is obsolete and only produces a warning"]
    }
  ]
}
---
*Every `docker compose` command here is **not run on this machine (Docker unavailable)**; behaviour per the cited docs. YAML parsing snippets are real PyYAML 6.0.3 runs.*

## 1. One file, one network

A compose file describes several containers that run together. For a FastAPI service that's typically three **services**: your app (built from your Dockerfile), PostgreSQL and Redis. Here is the notes service's stack, a different app from the exercise's:

```yaml
services:
  web:
    build: .
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgresql://notes:${NOTES_DB_PASSWORD:?missing}@postgres:5432/notes
      REDIS_URL: redis://redis:6379/0
  postgres:
    image: postgres:18
    environment:
      POSTGRES_USER: notes
      POSTGRES_DB: notes
      POSTGRES_PASSWORD: ${NOTES_DB_PASSWORD:?missing}
  redis:
    image: redis:8
```

- **Names are hostnames.** Compose creates one network for the project, and each service registers its name in an internal DNS. That's why the URL says `@postgres:5432` and `redis://redis:6379`, not `localhost`. Inside the `web` container, `localhost` is `web` itself.
- **Ports are only for you.** `"8080:8080"` is HOST:CONTAINER, so your browser can reach the app. Services talk to each other on the *container* port and need no `ports:` entry; Postgres and Redis have none here, so they aren't exposed on your machine at all.
- **Images are pinned** for the same reason as `FROM` in lesson 1. For a database it matters even more: a new major version may not start on the old version's data.
- No `version:` line at the top. It's obsolete; Compose only warns about it.

```console
$ docker compose up --build
```
*Not run on this machine (Docker unavailable).*

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "In this stack, which DATABASE_URL lets the web container reach PostgreSQL?",
  "options": ["postgresql://notes:...@postgres:5432/notes", "postgresql://notes:...@localhost:5432/notes", "postgresql://notes:...@127.0.0.1:5432/notes", "postgresql://notes:...@web:5432/notes"], "answer": 0,
  "explanation": "Services find each other by service name on the Compose network. localhost inside the web container is the web container itself, where nothing listens on 5432." }
```

**A YAML trap with ports.** The Compose reference says to always quote HOST:CONTAINER. PyYAML (like other YAML 1.1 parsers) reads some unquoted `a:b` values as base-60 numbers:

```quiz
{ "id": "q2", "type": "output",
  "prompt": "What does this print?",
  "code": "import yaml\nprint(yaml.safe_load('ports:\\n  - 22:22\\n  - \"22:22\"'))",
  "answer": "{'ports': [1342, '22:22']}",
  "explanation": "Unquoted 22:22 matches YAML 1.1's sexagesimal (base-60) integer form: 22*60 + 22 = 1342. Quoted, it stays the string '22:22'. Ports above 59 after the colon happen to survive, which is why the bug hides." }
```

## 2. Started is not ready

Add `depends_on: [postgres, redis]` to `web` and Compose starts Postgres and Redis **before** the app. But the docs are explicit: on startup, Compose waits only until a container is **running, not ready**. Postgres needs a few seconds to initialise, so your app's first connection gets "connection refused" and, if it connects at startup, crashes.

The fix has two halves:

1. Give the dependency a **healthcheck**, so Compose can know when it's ready.
2. Ask for **`condition: service_healthy`** with the long `depends_on` syntax.

```yaml
services:
  web:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
        restart: true
      redis:
        condition: service_started
  postgres:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s
```

This is Docker's own example:

- `pg_isready` ships with the postgres image and exits 0 once the server accepts connections. The same exit-code rule as `HEALTHCHECK` in lesson 2.
- `test:` is a list whose first item is `CMD` (run the program directly) or `CMD-SHELL` (run a string through the container's shell). A plain string means `CMD-SHELL`.
- `$${POSTGRES_USER}`: `$$` is a literal `$`, so Compose leaves `${POSTGRES_USER}` alone and the *container's* shell expands it.
- `restart: true` restarts `web` when Compose restarts `postgres`.
- The three conditions are `service_started` (same as the short form), `service_healthy`, and `service_completed_successfully` (for one-shot jobs like migrations).

For Redis, the health probe is `redis-cli ping`: the `redis` image includes `redis-cli`, and `PING` answers `PONG` when the server is alive. Writing that healthcheck is part of the exercise.

You can see the difference between the two syntaxes in what the parser returns:

```python
import yaml

short = yaml.safe_load("depends_on: [postgres, redis]")
long = yaml.safe_load("""
depends_on:
  postgres:
    condition: service_healthy
""")
print(short["depends_on"])
print(long["depends_on"])
```

```console
['postgres', 'redis']
{'postgres': {'condition': 'service_healthy'}}
```

A list has nowhere to put a condition. That's why readiness needs the mapping form.

```quiz
{ "id": "q3", "type": "truefalse",
  "prompt": "`condition: service_healthy` works even if the dependency has no healthcheck, because Compose then checks the port.", "answer": false,
  "explanation": "Healthy means the service's healthcheck passed. Without a healthcheck (in the compose file or the image's HEALTHCHECK), there's no health status to wait for." }
```

```quiz
{ "id": "q4", "type": "choice", "label": "Debugging",
  "prompt": "The app crashes on about one `docker compose up` in three with `connection refused` to postgres:5432, then works after `docker compose restart web`. The file has `depends_on: [postgres]`. Best fix?",
  "options": ["Add a pg_isready healthcheck to postgres and use depends_on with condition: service_healthy", "Add sleep 10 before uvicorn in CMD", "Publish port 5432 with ports:", "Change the URL host to localhost"], "answer": 0,
  "explanation": "A race between 'started' and 'ready'. A fixed sleep is a guess that fails on slow machines and wastes time on fast ones. A healthcheck waits exactly as long as needed." }
```

Even with this in place, your app should still retry or fail clearly when the database disappears later: Compose only orders startup.

## 3. Secrets: interpolate, don't commit

The OAuth secret that once shipped in source code has a Compose equivalent: `POSTGRES_PASSWORD: hunter2` committed in compose.yaml. The fix is **interpolation**:

```yaml
POSTGRES_PASSWORD: ${NOTES_DB_PASSWORD:?missing}
```

- Compose fills `${...}` from your shell environment, or by default from a **`.env` file in the project directory**. Shell variables win when both are set.
- `${VAR:?message}` stops Compose with `message` if VAR is unset or empty. Without the `?`, a missing variable becomes an empty string with a warning, and the official postgres image requires a non-empty `POSTGRES_PASSWORD`.
- `${VAR:-default}` is for harmless defaults (a port, a log level), never for secrets.
- `.env` goes in `.gitignore` *and* `.dockerignore`. Commit a `.env.example` with the variable names and fake values instead.

**Stronger: Compose secrets.** Docker's docs warn that environment variables can leak, for example in logs while debugging. A secret is mounted as a file instead:

```yaml
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/notes_db_password
    secrets:
      - notes_db_password
secrets:
  notes_db_password:
    file: ./notes_db_password.txt
```

The postgres image reads `*_FILE` variables. That's a convention of some images, not a Compose feature, so your own app has to read the file itself.

```quiz
{ "id": "q5", "type": "truefalse",
  "prompt": "With `POSTGRES_PASSWORD: ${DB_PASSWORD}` and no DB_PASSWORD set anywhere, Compose refuses to start.", "answer": false,
  "explanation": "Plain ${DB_PASSWORD} becomes an empty string (with a warning). Only ${DB_PASSWORD:?message} makes Compose stop with an error." }
```

## 4. Data that survives

A container's filesystem disappears with the container. Database files belong in a **named volume**:

```yaml
services:
  postgres:
    image: postgres:18
    volumes:
      - notes-db:/var/lib/postgresql
volumes:
  notes-db:
```

- From PostgreSQL 18, the official image keeps its data under `/var/lib/postgresql` (in a versioned subfolder), and that's where the volume goes. For 17 and earlier, the documented mount point was `/var/lib/postgresql/data`. Mount the wrong path and your data lives in the container after all.
- `docker compose down` removes containers and networks, **not** named volumes. `docker compose down -v` removes the named volumes too: that's your "reset the database" command, and the one to never run by accident.

```quiz
{ "id": "q6", "type": "choice",
  "prompt": "After `docker compose down` and `docker compose up`, is the data in the `notes-db` named volume still there?",
  "options": ["Yes: down removes containers and networks, not named volumes", "No: down removes everything the file created", "Only if restart: always is set", "Only for Redis"], "answer": 0,
  "explanation": "Named volumes are removed only with down -v (--volumes)." }
```

```quiz
{ "id": "q7", "type": "explain", "label": "Application",
  "prompt": "Suppose a team's docker-compose.yml has `MYSQL_ROOT_PASSWORD: root` in it, and it's 'only for local dev'. What's the risk, and what minimal change would you propose?",
  "model": "Local-dev files get copied into CI, staging scripts and other projects, and weak committed defaults end up on reachable machines; Git history keeps the value forever. Minimal change: ${MYSQL_ROOT_PASSWORD:?set it in .env} plus a committed .env.example and .env in .gitignore/.dockerignore. For anything beyond local, use secrets files.",
  "explanation": "Interpolation with :? costs one line and makes the secret an explicit, per-machine input." }
```

## 5. Your turn

The exercise gives you a compose file for the FastAPI app (`api`), Postgres (`db`) and Redis (`cache`) with four problems: start-up race, floating images, a plaintext password (twice) and no volume. The tests parse it with PyYAML.

```exercise
OPS.M01.L03.E1
```
