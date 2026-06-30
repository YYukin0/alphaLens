# DeepEquity Railway Deployment

Deploy DeepEquity as **five Railway services** from one GitHub repo using **Docker** (not Nixpacks at repo root).

## Why the build was failing

Railway was building the **repository root**, which has no `package.json` or Python app. Nixpacks cannot detect a build target and Docker fails with **"Failed to build image"**.

**Fix:** create separate services with **Root Directory** set to `backend` or `frontend`, and use the Dockerfiles in those folders.

---

## Architecture on Railway

| Service | Root Directory | Config file | Start command |
|---------|----------------|-------------|---------------|
| **backend** | `backend` | `/backend/railway.toml` | `/app/scripts/entrypoint.sh api` |
| **celery-worker** | `backend` | `/backend/railway.worker.toml` | `/app/scripts/entrypoint.sh worker` |
| **frontend** | `frontend` | `/frontend/railway.toml` | (Dockerfile CMD) |
| **PostgreSQL** | — | Railway plugin | — |
| **Redis** | — | Railway plugin | — |

---

## Step-by-step setup

### 1. Create project from GitHub

1. Open [railway.app/new](https://railway.app/new)
2. Click **Deploy from GitHub repo**
3. Select **`YYukin0/alphaLens`**

### 2. Add PostgreSQL and Redis

1. In the project canvas, click **+ New**
2. Choose **Database → PostgreSQL**
3. Click **+ New** again → **Database → Redis**

### 3. Create the backend API service

1. Click **+ New → GitHub Repo** (same repo) **or** duplicate the first service
2. Open **Settings**
3. Set **Root Directory** → `backend`
4. Set **Config file path** → `/backend/railway.toml`
5. Open **Variables** and add:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `APP_ENV` | `production` |
| `SEC_USER_AGENT` | `DeepEquity contact@YOUR_EMAIL.com` |
| `CORS_ORIGINS` | `https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}` |
| `OPENAI_API_KEY` | *(optional)* your OpenAI key |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `AUTO_EXTRACT_EVENTS` | `true` |

6. Open **Settings → Networking → Generate Domain** (public URL for API)

### 4. Create the Celery worker service

1. **+ New → GitHub Repo** (same repo)
2. **Root Directory** → `backend`
3. **Config file path** → `/backend/railway.worker.toml`
4. **Variables** (same as backend, plus):

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `APP_ENV` | `production` |
| `SEC_USER_AGENT` | same as backend |
| `SKIP_MIGRATIONS` | `true` |
| `OPENAI_API_KEY` | same as backend (if using events) |

5. **Do not** expose a public domain for the worker.

### 5. Create the frontend service

1. **+ New → GitHub Repo** (same repo)
2. **Root Directory** → `frontend`
3. **Config file path** → `/frontend/railway.toml`
4. **Variables**:

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://${{backend.RAILWAY_PUBLIC_DOMAIN}}/api/v1` |

Replace `backend` with your actual backend service name if different.

5. **Settings → Networking → Generate Domain** (public URL for the app)

### 6. Redeploy after linking domains

After the backend gets a public domain:

1. Update frontend `VITE_API_BASE_URL` if needed
2. Update backend `CORS_ORIGINS` to the frontend public URL
3. Click **Deploy** on backend, celery-worker, and frontend

---

## Health checks

| Service | Path |
|---------|------|
| Backend | `/api/v1/health` |
| Frontend | `/` |

Migrations run automatically on backend startup (`alembic upgrade head`).

---

## Verify deployment

Replace URLs with your Railway domains.

```bash
# Health
curl https://YOUR-BACKEND.up.railway.app/api/v1/health

# SEC sync
curl -X POST https://YOUR-BACKEND.up.railway.app/api/v1/filings/sync \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","limit":3}'

# Yahoo prices
curl -X POST https://YOUR-BACKEND.up.railway.app/api/v1/prices/sync \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","period":"1y"}'

# Filing reader (use an id from filings list)
curl https://YOUR-BACKEND.up.railway.app/api/v1/filings/detail/1
```

Open the frontend public URL in a browser and walk through Companies → Filings → View filing.

---

## Production checklist

- [ ] Backend deployed and healthy (`/api/v1/health` → 200)
- [ ] Frontend deployed and loads at public URL
- [ ] PostgreSQL connected (`DATABASE_URL` reference)
- [ ] Redis connected (`REDIS_URL` reference)
- [ ] Celery worker running (check worker logs for `celery@... ready`)
- [ ] Alembic migrations applied (backend logs: `Running database migrations...`)
- [ ] SEC sync verified (POST `/filings/sync`)
- [ ] Yahoo sync verified (POST `/prices/sync`)
- [ ] Filing reader verified (open filing detail in UI)
- [ ] Public URL working for friends

---

## Troubleshooting

### "Failed to build image"

- Confirm **Root Directory** is `backend` or `frontend`, not empty
- Confirm **Config file path** points to `/backend/railway.toml` or `/frontend/railway.toml`
- Builder must be **Dockerfile**, not Nixpacks

### Frontend shows API errors / CORS

- Set `CORS_ORIGINS` on backend to your frontend URL (include `https://`)
- Rebuild frontend after changing `VITE_API_BASE_URL` (build-time variable)

### Celery jobs not running

- Confirm worker service uses `railway.worker.toml`
- Confirm `REDIS_URL` matches on backend and worker
- Check worker logs for connection errors

### SEC 403 errors

- Set a real email in `SEC_USER_AGENT` (SEC requires identifiable User-Agent)
