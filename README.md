# Ops Agent

Support assistant that follows **Workflows**, searches **Articles**, and calls **Tools**.

Demo corpus: **Cobalt Home** (generic connected-access company). Replace Articles/Workflows/Rules with a real customer's content for production.

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

## Backup

```bash
docker compose exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore with `psql` into a fresh volume. Schedule this (cron / host job) for real deployments.

## CI

GitHub Actions runs backend pytest + frontend lint/build on push/PR to `main`.

## Multi-company grounding check

Six demo corpora live under `backend/app/data/companies/`.
With the stack up:

```bash
docker compose cp scripts/multi_company_eval.py backend:/tmp/multi_company_eval.py
docker compose exec -e LIVE=1 -e API_BASE=http://127.0.0.1:8000 -e PYTHONPATH=/app -w /app backend python /tmp/multi_company_eval.py
```

This swaps Articles per brand, asks policy + trap questions, then restores Cobalt Home.
