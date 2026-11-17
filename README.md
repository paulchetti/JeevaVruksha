# Jeeva Vruksha

Jeeva Vruksha is an institution-only virtual clinical patient simulator for MBBS emergency training. It combines dynamic patient vitals, emergency decision tracking, protocol-traceable scoring, and a future constrained Gemini integration for learning feedback.

## Foundation included

- `apps/web`: Next.js PWA learner shell with an interactive adult cardiac-arrest simulation.
- `services/api`: FastAPI service with tenant-aware request context and a deterministic simulation engine.
- `infra`: local PostgreSQL container configuration.

## Run locally

1. Start PostgreSQL: `docker compose -f infra/docker-compose.yml up -d`.
2. In `services/api`, create a virtual environment, install `requirements.txt`, then run `uvicorn app.main:app --reload --port 8000`.
3. In `apps/web`, install packages with `npm install`, then run `npm run dev`.

Open `http://localhost:3000`. The web shell uses a mock college identity until institutional authentication is added.

## Safety boundary

Jeeva Vruksha is for simulation and education only. It must not be used to make real-time patient-care decisions.
