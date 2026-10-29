"use client";

import { useState } from "react";
import Image from "next/image";
import DocLoader from "@/components/DocLoader";
import { fetchMe, login, type Me } from "@/lib/api";

export default function LoginCard({ onSignedIn }: { onSignedIn: (token: string, me: Me) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    const formData = new FormData(e.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");
    if (!email || !password) {
      setError("Enter your email and password");
      return;
    }

    setBusy(true);
    try {
      const token = await login(email, password);
      const me = await fetchMe(token);
      onSignedIn(token, me);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass w-full max-w-md p-10">
      <Image
        className="company-logo-login"
        src="/company-logo.png"
        alt="All Known Services"
        width={512}
        height={127}
        priority
      />
      <h1 className="title-solid mt-4 text-center text-3xl font-bold tracking-tight">
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
              name="email"
              autoComplete="username"
              placeholder="you@allknownservices.com"
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <div className="password-control">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                autoComplete="current-password"
                placeholder="Your password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <p className="form-error" role="alert" aria-live="polite">{error ?? "\u00A0"}</p>
          <button type="submit" className="btn-dark w-full">
            Sign in
          </button>
        </form>
      )}
    </section>
  );
}