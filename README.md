# BPSR Crowd Data MVP

Minimal FastAPI app that accepts community submissions for Blue Protocol: Star Resonance combat and trade events, stores them in Postgres (SQLite locally), and exposes tiny read APIs plus a status page.

## Why this stack (free & simple)
1. **FastAPI + Uvicorn** run anywhere Python 3.11 works and stay within Fly.io's shared-cpu free VMs (3×256MB) while delivering built-in OpenAPI docs.
2. **Fly.io** still offers an always-free allowance for one 256MB VM with 3GB outbound data/month, enough for a low-traffic MVP without credit card charges.
3. Dockerized deployment keeps parity between local dev and Fly's container runtime so smoke scripts behave identically.
4. **Supabase Postgres** free tier (500MB database, 50MB/month egress) is sufficient for JSONB payload storage and can be provisioned in minutes.
5. Both Fly.io and Supabase support secrets via CLI, so no paid add-ons are needed for configuration management.
6. SQLite + SQLAlchemy locally means contributors need zero external services to run smoke tests.
7. Schema-first SQL migration keeps the database portable while sticking to Postgres features (JSONB, timestamptz) that Supabase supports.
8. Python-only stack avoids Node runtimes; even the HTML status page is a single string template.
9. Docker image uses official python:3.11-slim, meeting Fly.io's free builder constraints.
10. Smoke script relies only on `httpx` and built-in tooling, so CI/CD can reuse it without bespoke infra.
11. Bash smoke script gives a no-Python fallback for remote verification via SSH terminals.
12. CORS + rate limiting implemented in-memory to avoid external dependencies.
13. CLI utilities reuse the same migration SQL so Fly release commands stay trivial.
14. If Fly.io/Supabase free tiers change, swap in Railway + Neon (both have free hobby tiers) without touching application code.
15. Everything remains under the MIT license for easy reuse.

## Quickstart (local)
```bash
cp .env.example .env
poetry install
poetry run make db-local
poetry run python -m app.cli seed-key local-dev-key
poetry run make dev
poetry run make smoke
```

Set `SMOKE_API_KEY=local-dev-key` when hitting write endpoints locally. Open http://127.0.0.1:8000/docs for the interactive API.

## Deploy on Fly.io (free tier)
1. Install the Fly CLI (`curl -L https://fly.io/install.sh | sh`) and log in: `fly auth signup` then `fly auth login`.
2. Create a Supabase project (free tier) and copy the Postgres connection string (replace password placeholders). Set `DATABASE_URL` to that DSN.
3. Provision at least one API key: `fly secrets set DEFAULT_API_KEY=$(openssl rand -hex 16)` to auto-seed on startup.
4. Configure allowed POST origins (optional): `fly secrets set API_ALLOWED_ORIGINS="https://yourdomain"`.
5. Deploy:
   ```bash
   fly launch --no-deploy  # accepts fly.toml app name
   fly deploy
   ```
6. Set the Supabase DSN secret: `fly secrets set DATABASE_URL="<postgres-url>"` if not already done.
7. Verify:
   ```bash
   curl -s https://<your-app>.fly.dev/health
   curl -s -X POST https://<your-app>.fly.dev/v1/ingest \
     -H "X-API-Key: $DEFAULT_API_KEY" -H "Content-Type: application/json" \
     -d '{"source":"manual","category":"boss_event","payload":{}}'
   curl -s "https://<your-app>.fly.dev/v1/submissions/recent?category=boss_event&limit=1"
   ```

## API usage
```bash
# Health
curl -s https://<host>/health

# Recent submissions
curl -s "https://<host>/v1/submissions/recent?category=combat&limit=5"

# Filter by boss and time
curl -s "https://<host>/v1/submissions/search?category=boss_event&boss_name=Frostclaw"

# Write (needs key)
curl -s -X POST https://<host>/v1/ingest \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{
    "source": "bp_timer",
    "category": "boss_event",
    "region": "NA",
    "boss_name": "Frostclaw",
    "payload": {"hp": 123456, "timestamp": "2024-01-01T12:00:00Z"}
  }'
```

## Data format hints
- **BP Timer** payloads often include `boss`, `event`, `timestamp`, `server`; adapter maps those into `boss_name`, `category`, and `metadata.timestamp`.
- **bpsr-logs (WinJ)** payloads may include `type`, `boss.name`, `tick`, `region`; adapter stores them and normalizes combat/heal/trade categories.
- Unknown fields are preserved in `payload` JSON for future enrichment.

## Smoke checks
- Python: `poetry run make smoke` boots a temp API, seeds a key, ingests, and verifies retrieval.
- Bash: `SMOKE_API_KEY=<key> BASE_URL=http://127.0.0.1:8000 scripts/smoke.sh` assumes a running server with that key inserted.

## Limits & next steps
- Free tiers mean limited CPU (256MB VM) and 500MB Postgres storage; prune old data or archive JSONL exports regularly.
- Rate limiting is in-memory per instance—consider Redis if multi-region traffic grows.
- Add auth for read endpoints if sensitive payloads ever appear.
- Implement schema versioning when more tables arrive.
- Consider batching ingest from client tools to reduce HTTP chatter.
- Attach monitoring (Fly health checks, Supabase query insights) when usage increases.
