"use client";

import { signIn, signOut, useSession } from "next-auth/react";

export function AuthControl() {
  const { data: session, status } = useSession();
  if (process.env.NEXT_PUBLIC_OIDC_ENABLED !== "true") return null;
  if (status === "loading")
    return <span className="auth-status">Checking sign-in…</span>;

  if (session) {
    return (
      <button
        className="auth-button"
        onClick={() => void signOut({ callbackUrl: "/" })}
      >
        Sign out
      </button>
    );
  }

  return (
    <button className="auth-button" onClick={() => void signIn("institution")}>
      Institutional sign-in
    </button>
  );
}
