"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AttemptState,
  CaseSummary,
  getCases,
  recordAction,
  startAttempt,
} from "../lib/api";
import { AuthControl } from "../components/auth-control";

export default function Home() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [attempt, setAttempt] = useState<AttemptState | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loadingCases, setLoadingCases] = useState(true);
  const [pendingAction, setPendingAction] = useState("");
  const [startingCase, setStartingCase] = useState("");

  const loadCases = useCallback(async () => {
    setLoadingCases(true);
    setError("");
    try {
      setCases(await getCases());
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not load simulations.",
      );
    } finally {
      setLoadingCases(false);
    }
  }, []);

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  const beginAttempt = async (caseId: string) => {
    setStartingCase(caseId);
    setError("");
    try {
      setAttempt(await startAttempt(caseId));
      setReasoning("");
      setNotice("Simulation started. Assess the virtual patient.");
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not start the simulation.",
      );
    } finally {
      setStartingCase("");
    }
  };

  const selectAction = async (actionId: string) => {
    if (!attempt) return;
    setPendingAction(actionId);
    setError("");
    try {
      const updated = await recordAction(
        attempt.attempt_id,
        actionId,
        reasoning,
      );
      setAttempt(updated);
      setReasoning("");
      setNotice(updated.message ?? "Action submitted.");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not record the action.",
      );
    } finally {
      setPendingAction("");
    }
  };

  const completed = attempt?.completed_actions ?? [];

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">JEEVA VRUKSHA</p>
          <h1>{attempt?.case.title ?? "Clinical simulations"}</h1>
        </div>
        <div className="header-controls">
          <AuthControl />
          {attempt && (
            <div className="timer">{attempt.case.duration_minutes} min</div>
          )}
        </div>
      </header>
      <p className="boundary">
        For education and simulation only. Not for real patient care.
      </p>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!attempt ? (
        <section className="case-list" aria-labelledby="case-list-heading">
          <h2 id="case-list-heading">Available simulations</h2>
          {loadingCases ? (
            <p role="status">Loading simulations…</p>
          ) : cases.length === 0 ? (
            <div>
              <p>No simulations are currently available.</p>
              <button
                className="secondary-button"
                onClick={() => void loadCases()}
              >
                Try again
              </button>
            </div>
          ) : (
            cases.map((simulation) => (
              <article className="case-card" key={simulation.id}>
                <div>
                  <h3>{simulation.title}</h3>
                  <p>
                    {simulation.specialty} · {simulation.duration_minutes}{" "}
                    minutes
                  </p>
                </div>
                <button
                  disabled={Boolean(startingCase)}
                  onClick={() => void beginAttempt(simulation.id)}
                >
                  {startingCase === simulation.id
                    ? "Starting…"
                    : "Start simulation"}
                </button>
              </article>
            ))
          )}
          {error && (
            <button
              className="secondary-button"
              onClick={() => void loadCases()}
            >
              Retry loading simulations
            </button>
          )}
        </section>
      ) : (
        <>
          <section className="grid">
            <article className="patient">
              <h2>Virtual patient</h2>
              <div className="vitals">
                {Object.entries(attempt.vitals).map(([name, value]) => (
                  <span key={name}>
                    {name}
                    <strong>{value}</strong>
                  </span>
                ))}
              </div>
              <p className="notice" role="status">
                {notice}
              </p>
            </article>
            <article>
              <h2>Actions</h2>
              <div className="actions">
                {attempt.actions.map(({ id, label }) => (
                  <button
                    key={id}
                    className={completed.includes(id) ? "done" : ""}
                    disabled={
                      Boolean(pendingAction) ||
                      Boolean(startingCase) ||
                      completed.includes(id)
                    }
                    onClick={() => void selectAction(id)}
                  >
                    {completed.includes(id) ? "✓ " : ""}
                    {pendingAction === id ? "Recording…" : label}
                  </button>
                ))}
              </div>
            </article>
          </section>
          <section className="debrief">
            <div>
              <h2>Clinical reasoning</h2>
              <label className="sr-only" htmlFor="reasoning">
                Clinical reasoning for your next action
              </label>
              <textarea
                id="reasoning"
                value={reasoning}
                onChange={(event) => setReasoning(event.target.value)}
                placeholder="Explain what you are prioritising and why…"
              />
              <p>
                Your reasoning is sent with your next action for this
                simulation.
              </p>
            </div>
            <div className="score">
              <p>Current score</p>
              <strong>{attempt.score}</strong>
              <p>{completed.length} actions recorded</p>
            </div>
          </section>
          <button
            className="secondary-button restart-button"
            disabled={Boolean(startingCase) || Boolean(pendingAction)}
            onClick={() => void beginAttempt(attempt.case.id)}
          >
            {startingCase ? "Starting…" : "Start a new attempt"}
          </button>
        </>
      )}
    </main>
  );
}
