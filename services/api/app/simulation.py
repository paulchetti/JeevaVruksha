from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class CaseDefinition:
    id: str
    title: str
    specialty: str
    duration_minutes: int
    initial_vitals: dict[str, str]
    actions: dict[str, dict]


def cardiac_arrest_case() -> CaseDefinition:
    return CaseDefinition(
        id="adult-cardiac-arrest-v1",
        title="Adult cardiac arrest in emergency room",
        specialty="Emergency medicine",
        duration_minutes=12,
        initial_vitals={"BP": "Not recordable", "HR": "0", "SpO2": "72%", "Rhythm": "VF"},
        actions={
            "call-code": {"label": "Call resuscitation team", "points": 10, "critical": True},
            "start-cpr": {"label": "Start high quality CPR", "points": 30, "critical": True},
            "attach-defib": {"label": "Attach defibrillator", "points": 15, "critical": True},
            "defibrillate": {"label": "Deliver shock for VF", "points": 25, "critical": True, "requires": "attach-defib"},
            "give-epinephrine": {"label": "Administer epinephrine", "points": 10, "requires": "start-cpr"},
            "order-ecg": {"label": "Order ECG", "points": -5, "unsafe": "ECG order delays immediate resuscitation"},
        },
    )


@dataclass
class Action:
    action_id: str
    reasoning: str | None = None


@dataclass
class CaseSession:
    id: str
    tenant_id: str
    case: CaseDefinition
    started_at: datetime
    completed_actions: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    score: int = 0

    @classmethod
    def new(cls, case: CaseDefinition, tenant_id: str) -> "CaseSession":
        return cls(id=str(uuid4()), tenant_id=tenant_id, case=case, started_at=datetime.now(timezone.utc))

    def apply(self, action: Action) -> dict:
        definition = self.case.actions.get(action.action_id)
        if not definition:
            return {**self.public_state(), "message": "Action is unavailable in this case."}
        if action.action_id in self.completed_actions:
            return {**self.public_state(), "message": "Action already recorded."}
        prerequisite = definition.get("requires")
        if prerequisite and prerequisite not in self.completed_actions:
            return {**self.public_state(), "message": f"Complete {self.case.actions[prerequisite]['label']} first."}
        self.completed_actions.append(action.action_id)
        self.score = max(0, self.score + definition["points"])
        event = {"action": definition["label"], "at": datetime.now(timezone.utc).isoformat(), "reasoning": action.reasoning}
        self.events.append(event)
        message = definition.get("unsafe") or "Action recorded. Reassess the patient and continue resuscitation."
        return {**self.public_state(), "message": message}

    def public_state(self) -> dict:
        critical = [key for key, item in self.case.actions.items() if item.get("critical")]
        missed = [self.case.actions[key]["label"] for key in critical if key not in self.completed_actions]
        return {
            "attempt_id": self.id,
            "case": {"id": self.case.id, "title": self.case.title, "duration_minutes": self.case.duration_minutes},
            "vitals": self.case.initial_vitals,
            "actions": [{"id": key, "label": item["label"]} for key, item in self.case.actions.items()],
            "completed_actions": self.completed_actions.copy(),
            "timeline": self.events,
            "score": self.score,
            "missed_critical_actions": missed,
            "educational_use_only": True,
        }
