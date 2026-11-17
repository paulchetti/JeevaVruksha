from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .simulation import Action, CaseSession, cardiac_arrest_case

app = FastAPI(title="Jeeva Vruksha API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, CaseSession] = {}


class ActionRequest(BaseModel):
    action_id: str
    reasoning: str | None = None


def require_tenant(x_tenant_id: str | None) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Institution identity is required")
    return x_tenant_id


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jeeva-vruksha-api"}


@app.get("/v1/cases")
def list_cases(x_tenant_id: str | None = Header(default=None)) -> list[dict]:
    require_tenant(x_tenant_id)
    case = cardiac_arrest_case()
    return [{"id": case.id, "title": case.title, "specialty": case.specialty, "duration_minutes": case.duration_minutes}]


@app.post("/v1/cases/{case_id}/attempts")
def start_attempt(case_id: str, x_tenant_id: str | None = Header(default=None)) -> dict:
    tenant_id = require_tenant(x_tenant_id)
    case = cardiac_arrest_case()
    if case_id != case.id:
        raise HTTPException(status_code=404, detail="Case not found")
    session = CaseSession.new(case=case, tenant_id=tenant_id)
    sessions[session.id] = session
    return session.public_state()


@app.post("/v1/attempts/{attempt_id}/actions")
def record_action(attempt_id: str, payload: ActionRequest, x_tenant_id: str | None = Header(default=None)) -> dict:
    tenant_id = require_tenant(x_tenant_id)
    session = sessions.get(attempt_id)
    if not session or session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return session.apply(Action(action_id=payload.action_id, reasoning=payload.reasoning))
