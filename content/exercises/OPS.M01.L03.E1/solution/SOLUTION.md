```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app:${POSTGRES_PASSWORD:?set it in .env}@db:5432/app
      REDIS_URL: redis://cache:6379/0
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy

  db:
    image: postgres:18.6
    environment:
      POSTGRES_USER: app
      POSTGRES_DB: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set it in .env}
    volumes:
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app", "-d", "app"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 20s

  cache:
    image: redis:8.10
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

**Why it works**

- **Readiness, not just start order.** The short `depends_on` list only makes Compose start db and cache first; Compose doesn't wait until they're ready. With healthchecks on both and `condition: service_healthy`, api is created only after `pg_isready` succeeds (Postgres accepts connections) and `redis-cli ping` gets PONG.
- **Pinned images**: `postgres:18.6` and `redis:8.10` are tags listed on Docker Hub. Pinning matters even more for a database than for your app, because the data directory belongs to one major version of PostgreSQL.
- **No plaintext password.** `${POSTGRES_PASSWORD:?set it in .env}` is filled from the shell or the `.env` file next to compose.yaml; if it's unset or empty, Compose stops with that message instead of starting Postgres with an empty password. The same variable is used inside `DATABASE_URL`, so the secret lives in one uncommitted place.
- **Named volume at `/var/lib/postgresql`**: the data outlives the container. For PostgreSQL 18+ the official image keeps data under `/var/lib/postgresql/18/docker`, so the volume goes on the parent `/var/lib/postgresql` (for 17 and earlier it was `/var/lib/postgresql/data`).

**Alternatives**

- **Compose secrets**: a top-level `secrets: db_password: file: ./db_password.txt`, `secrets: [db_password]` on the service, and `POSTGRES_PASSWORD_FILE: /run/secrets/db_password`. The value is then a file in the container instead of an environment variable, which Docker's docs recommend for sensitive data. Your app has to read the file too.
- `test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]` reads the names from the container's environment; `$$` stops Compose from interpolating them itself.
