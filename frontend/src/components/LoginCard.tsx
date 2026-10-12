"use client";

import { useState } from "react";
import DocLoader from "@/components/DocLoader";
import { fetchMe, login, type Me } from "@/lib/api";

export default function LoginCard({ onSignedIn }: { onSignedIn: (token: string, me: Me) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      const token = await login(email, password);
      const me = await fetchMe(token);
      setPassword("");
      onSignedIn(token, me);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass w-full max-w-md p-10">
      <p className="rise text-center text-xs tracking-[0.4em] uppercase text-[var(--silver-600)]">
        All Known Services
      </p>
      <h1 className="title-solid mt-3 text-center text-4xl font-bold tracking-tight">
        Applicant Tracking
      </h1>

      {busy ? (
        <div className="my-10 flex justify-center">
          <DocLoader label="Signing in" />
        </div>
      ) : (
        <form onSubmit={onSubmit} className="rise d2 mt-8 space-y-5" noValidate>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@allknownservices.com"
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              required
            />
          </label>
          <p className="form-error" role="alert" aria-live="polite">{error ?? "\u00A0"}</p>
          <button type="submit" className="btn-dark w-full" disabled={!email || !password}>
            Sign in
          </button>
        </form>
      )}
    </section>
  );
}