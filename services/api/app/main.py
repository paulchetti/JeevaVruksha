import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .auth import AuthContext, get_auth_context
from .simulation import Action, CaseSession, cardiac_arrest_case

load_dotenv()

app = FastAPI(title="Jeeva Vruksha API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, CaseSession] = {}


class ActionRequest(BaseModel):
    action_id: str
    reasoning: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jeeva-vruksha-api"}


@app.get("/v1/cases")
def list_cases(context: AuthContext = Depends(get_auth_context)) -> list[dict]:
    case = cardiac_arrest_case()
    return [{"id": case.id, "title": case.title, "specialty": case.specialty, "duration_minutes": case.duration_minutes}]


@app.post("/v1/cases/{case_id}/attempts")
def start_attempt(case_id: str, context: AuthContext = Depends(get_auth_context)) -> dict:
    case = cardiac_arrest_case()
    if case_id != case.id:
        raise HTTPException(status_code=404, detail="Case not found")
    session = CaseSession.new(case=case, tenant_id=context.tenant_id)
    sessions[session.id] = session
    return session.public_state()


@app.post("/v1/attempts/{attempt_id}/actions")
def record_action(
    attempt_id: str,
    payload: ActionRequest,
    context: AuthContext = Depends(get_auth_context),
) -> dict:
    session = sessions.get(attempt_id)
    if not session or session.tenant_id != context.tenant_id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return session.apply(Action(action_id=payload.action_id, reasoning=payload.reasoning))
