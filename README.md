# Ops Agent

Support assistant that follows **Workflows**, searches **Articles**, and calls **Tools**.

Stack: FastAPI + Postgres/pgvector + Next.js.

## Quick start (local dev)

```bash
cp .env.example .env
# set OPENAI_API_KEY (and a non-default POSTGRES_PASSWORD)

docker compose up --build
```

- UI: http://localhost:3001  
- API: http://localhost:8001  
- Health: `GET /healthz` · Ready: `GET /readyz`

## Production compose

```bash
# Strong secrets in .env: POSTGRES_PASSWORD, OPENAI_API_KEY, CORS_ORIGINS
# Optional: REQUIRE_AUTH=true and OPS_API_KEYS=...

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Prod overlay:

- No source bind mounts / no `--reload`
- Multi-worker API, standalone Next.js
- `ALLOW_LOCAL_TEST=false`
- Postgres not published to the host
- Readiness via `/readyz`
- Non-root containers

## Auth

When `REQUIRE_AUTH=true`:

1. Set `OPS_API_KEYS` to one or more Bearer tokens.
2. Clients send `Authorization: Bearer <token>` and `X-Ops-User: agent@company.com`.
3. In the browser, set:

```js
localStorage.setItem("ops-agent.api-token", "<token>");
localStorage.setItem("ops-agent.user-email", "agent@company.com");
```

## Naming (UI)

| Area | Label |
|------|--------|
| Procedures | Workflows |
| Help docs | Articles |
| APIs | Tools |
| Standing instructions | Rules |
| Outbound demo mail | Outbox |
| Spend board | Costs |

## Backup

```bash
docker compose exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore with `psql` into a fresh volume. Schedule this (cron / host job) for real deployments.

## CI

GitHub Actions runs backend pytest + frontend lint/build on push/PR to `main`.
