"use client";
import { useState } from "react";

const actions = [
  ["call-code", "Call resuscitation team"], ["start-cpr", "Start high quality CPR"],
  ["attach-defib", "Attach defibrillator"], ["defibrillate", "Deliver shock for VF"],
  ["give-epinephrine", "Administer epinephrine"], ["order-ecg", "Order ECG"],
] as const;

export default function Home() {
  const [completed, setCompleted] = useState<string[]>([]);
  const [reasoning, setReasoning] = useState("");
  const [notice, setNotice] = useState("Assess the patient immediately. This is a simulation.");
  const select = (id: string, label: string) => {
    if (completed.includes(id)) return;
    if (id === "defibrillate" && !completed.includes("attach-defib")) return setNotice("Attach the defibrillator before delivering a shock.");
    if (id === "give-epinephrine" && !completed.includes("start-cpr")) return setNotice("Start high quality CPR first.");
    setCompleted([...completed, id]);
    setNotice(id === "order-ecg" ? "ECG order recorded. In VF arrest, do not delay immediate resuscitation." : `${label} recorded. Continue reassessment.`);
  };
  const score = completed.reduce((n, id) => n + ({"call-code":10,"start-cpr":30,"attach-defib":15,"defibrillate":25,"give-epinephrine":10,"order-ecg":-5}[id] ?? 0), 0);
  return <main>
    <header><div><p className="eyebrow">JEEVA VRUKSHA</p><h1>Adult cardiac arrest</h1></div><div className="timer">12:00</div></header>
    <p className="boundary">For education and simulation only. Never use this tool for live patient care.</p>
    <section className="grid">
      <article className="patient"><h2>Virtual patient</h2><p>Male, 56. Collapsed in the emergency room. Unresponsive, no pulse.</p><div className="vitals"><span>BP<strong>Not recordable</strong></span><span>HR<strong>0</strong></span><span>SpO2<strong>72%</strong></span><span>Rhythm<strong>VF</strong></span></div><p className="notice">{notice}</p></article>
      <article><h2>Actions</h2><div className="actions">{actions.map(([id,label]) => <button key={id} className={completed.includes(id) ? "done" : ""} onClick={() => select(id,label)}>{completed.includes(id) ? "✓ " : ""}{label}</button>)}</div></article>
    </section>
    <section className="debrief"><div><h2>Clinical reasoning</h2><textarea value={reasoning} onChange={e => setReasoning(e.target.value)} placeholder="Explain what you are prioritising and why..." /><p>Gemini feedback will be constrained to case facts and reviewed protocol rules.</p></div><div className="score"><p>Current score</p><strong>{Math.max(0, score)}</strong><p>{completed.length} actions recorded</p></div></section>
  </main>;
}
