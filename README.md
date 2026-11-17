# Jeeva Vruksha

Jeeva Vruksha is an institution-only virtual clinical patient simulator for MBBS emergency training. It combines dynamic patient vitals, emergency decision tracking, protocol-traceable scoring, and a future constrained Gemini integration for learning feedback.

## Foundation included

- `apps/web`: Next.js PWA learner shell with an interactive adult cardiac-arrest simulation.
- `services/api`: FastAPI service with tenant-aware request context and a deterministic simulation engine.
- `infra`: local PostgreSQL container configuration.

## Run locally

1. Optionally start PostgreSQL: `docker compose -f infra/docker-compose.yml up -d`. The current demo API does not use the database; it stores attempts in process memory.
2. In `services/api`, create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, then run `uvicorn app.main:app --reload --port 8000`.
3. In `apps/web`, copy `.env.example` to `.env.local`, install packages with `npm install`, then run `npm run dev`.

Open `http://localhost:3000`. Local development uses a demo tenant header; institutional sign-in is available after configuring an OIDC provider.

The local demo sends `NEXT_PUBLIC_DEMO_TENANT_ID` as an `X-Tenant-ID` header. It is only a development stub, is visible to browser users, and is not authentication or a tenant-security boundary. Attempts are currently stored in API process memory and are lost when the API restarts. Do not deploy this demo configuration as a multi-college service.

Run the API and deterministic simulation tests from `services/api` with `python -m unittest discover -s tests`.
In `apps/web`, run `npm run lint`, `npm run format:check`, and `npm run typecheck` to validate the frontend.

The API database schema is versioned with Alembic. Set `DATABASE_URL` in `services/api/.env` to a PostgreSQL connection string before running `alembic upgrade head` from `services/api`. The current demo API does not yet read or write simulation data through this schema; authentication and persistence are upcoming milestones.

Institutional sign-in uses a configurable OIDC provider. The web server keeps the provider access token in its encrypted, HTTP-only NextAuth session and proxies API requests server-side; the browser never receives that token. Configure the OIDC issuer/client credentials and `NEXTAUTH_SECRET` in the web server environment. Configure `AUTH_MODE=oidc`, `APP_ENV=production`, the matching `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`, and `DATABASE_URL` in the API environment. The API accepts signed RS256 JWT access tokens only, and rejects identities without an enrolled membership and active institution subscription. OIDC sign-in alone does not create an account; invitation issuance and acceptance are the next milestone.

## Safety boundary

Jeeva Vruksha is for education and simulation only. Not for real patient care.
