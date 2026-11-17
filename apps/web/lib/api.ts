export interface CaseSummary {
  id: string;
  title: string;
  specialty: string;
  duration_minutes: number;
}

export interface AttemptState {
  attempt_id: string;
  case: {
    id: string;
    title: string;
    duration_minutes: number;
  };
  vitals: Record<string, string>;
  actions: { id: string; label: string }[];
  completed_actions: string[];
  timeline: {
    action: string;
    at: string;
    reasoning: string | null;
  }[];
  score: number;
  missed_critical_actions: string[];
  educational_use_only: boolean;
  message?: string;
}

const DEMO_TENANT_ID = process.env.NEXT_PUBLIC_DEMO_TENANT_ID;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (DEMO_TENANT_ID) {
    headers.set("X-Tenant-ID", DEMO_TENANT_ID);
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new Error(
      "Could not reach the simulation API. Check that it is running and try again.",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `The simulation API returned an error (${response.status}).`;
    throw new Error(detail);
  }

  return payload as T;
}

export function getCases(): Promise<CaseSummary[]> {
  return request("/v1/cases");
}

export function startAttempt(caseId: string): Promise<AttemptState> {
  return request(`/v1/cases/${encodeURIComponent(caseId)}/attempts`, {
    method: "POST",
  });
}

export function recordAction(
  attemptId: string,
  actionId: string,
  reasoning: string,
): Promise<AttemptState> {
  return request(`/v1/attempts/${encodeURIComponent(attemptId)}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_id: actionId, reasoning: reasoning || null }),
  });
}
