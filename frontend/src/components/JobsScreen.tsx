"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { listJobs, saveJob, SessionError, type Job } from "@/lib/api";

const NM = "Not Mentioned";
const MODES = ["Remote", "Hybrid", "Onsite"];
const STATUSES = ["Open", "On Hold", "Filled", "Closed"];

type Form = {
  title: string; client: string; description: string; location: string; workMode: string;
  years: string; visa: string; rate: string; status: string; required: string; preferred: string;
};

const BLANK: Form = {
  title: "", client: "", description: "", location: "", workMode: "",
  years: "", visa: "", rate: "", status: "Open", required: "", preferred: "",
};

function fromJob(j: Job): Form {
  return {
    title: j.title, client: j.client ?? "", description: j.description ?? "", location: j.location ?? "",
    workMode: j.work_mode ?? "", years: j.required_experience_years ?? "", visa: j.visa_requirements ?? "",
    rate: j.rate ?? "", status: j.status, required: j.required_skills.join(", "), preferred: j.preferred_skills.join(", "),
  };
}

const splitList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const orNull = (s: string) => (s.trim() === "" ? null : s.trim());

function toPayload(f: Form): { payload?: Record<string, unknown>; error?: string } {
  if (!f.title.trim()) return { error: "Job title is required" };
  const years = f.years.trim() === "" ? null : Number(f.years);
  const rate = f.rate.trim() === "" ? null : Number(f.rate);
  if (years !== null && (isNaN(years) || years < 0)) return { error: "Required experience must be a number, 0 or more" };
  if (rate !== null && (isNaN(rate) || rate < 0)) return { error: "Rate must be a number, 0 or more" };
  return {
    payload: {
      title: f.title.trim(), client: orNull(f.client), description: orNull(f.description),
      location: orNull(f.location), work_mode: orNull(f.workMode), required_experience_years: years,
      visa_requirements: orNull(f.visa), rate, status: f.status,
      required_skills: splitList(f.required), preferred_skills: splitList(f.preferred),
    },
  };
}

function statusTone(s: string) {
  if (s === "Open") return "badge";
  if (s === "On Hold") return "badge warn";
  return "badge muted";
}

function JobForm({
  initial, heading, onCancel, onSubmit,
}: { initial: Form; heading: string; onCancel: () => void; onSubmit: (p: Record<string, unknown>) => Promise<void> }) {
  const [f, setF] = useState<Form>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof Form, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    const r = toPayload(f);
    if (r.error || !r.payload) {
      setError(r.error ?? "Please check the fields");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit(r.payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the job");
      setSaving(false);
    }
  }

  return (
    <div className="fade-in">
      <button className="btn-ghost" onClick={onCancel} type="button">&larr; Back to jobs</button>
      <h1 className="mt-5 text-2xl font-bold tracking-tight">{heading}</h1>
      <form onSubmit={submit} className="mt-6" noValidate>
        <div className="form-grid">
          <label className="field span-all"><span>Job title *</span>
            <input value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. Senior Java Developer" /></label>
          <label className="field"><span>Client</span>
            <input value={f.client} onChange={(e) => set("client", e.target.value)} placeholder="Client name" /></label>
          <label className="field"><span>Location</span>
            <input value={f.location} onChange={(e) => set("location", e.target.value)} placeholder="City, State" /></label>
          <label className="field"><span>Work mode</span>
            <select value={f.workMode} onChange={(e) => set("workMode", e.target.value)}>
              <option value="">Not specified</option>
              {MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select></label>
          <label className="field"><span>Status</span>
            <select value={f.status} onChange={(e) => set("status", e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label className="field"><span>Required experience (years)</span>
            <input type="number" min="0" step="0.5" onWheel={(e) => e.currentTarget.blur()} value={f.years} onChange={(e) => set("years", e.target.value)} placeholder="e.g. 5" /></label>
          <label className="field"><span>Rate</span>
            <input type="number" min="0" step="0.01" onWheel={(e) => e.currentTarget.blur()} value={f.rate} onChange={(e) => set("rate", e.target.value)} placeholder="e.g. 70" /></label>
          <label className="field span-all"><span>Visa requirements</span>
            <input value={f.visa} onChange={(e) => set("visa", e.target.value)} placeholder="e.g. USC or GC" /></label>
          <label className="field span-all"><span>Required skills (comma separated)</span>
            <input value={f.required} onChange={(e) => set("required", e.target.value)} placeholder="e.g. Java, Spring Boot, AWS" /></label>
          <label className="field span-all"><span>Preferred skills (comma separated)</span>
            <input value={f.preferred} onChange={(e) => set("preferred", e.target.value)} placeholder="e.g. Docker, Kubernetes" /></label>
          <label className="field span-all"><span>Description</span>
            <textarea rows={6} value={f.description} onChange={(e) => set("description", e.target.value)} placeholder="Paste the job description" /></label>
        </div>
        <p className="form-error mt-3" role="alert" aria-live="polite">{error ?? "\u00A0"}</p>
        <div className="flex gap-3">
          <button type="submit" className="btn-dark" disabled={saving}>{saving ? "Saving..." : "Save job"}</button>
          <button type="button" className="btn-ghost" onClick={onCancel} disabled={saving}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export default function JobsScreen({ token, onSessionEnd, onOpenCandidate }: { token: string; onSessionEnd: () => void; onOpenCandidate: (id: number) => void }) {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Job | "new" | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listJobs(token);
        if (cancelled) return;
        setJobs(data);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof SessionError) {
          onSessionEnd();
          return;
        }
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, reloadKey, onSessionEnd]);

  async function handleSave(payload: Record<string, unknown>) {
    try {
      await saveJob(token, editing === "new" || editing === null ? null : editing.id, payload);
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      throw err;
    }
    setEditing(null);
    setLoading(true);
    setReloadKey((k) => k + 1);
  }

  if (editing !== null) {
    return (
      <section className="glass w-full p-6 sm:p-8">
        <JobForm
          key={editing === "new" ? "new" : editing.id}
          initial={editing === "new" ? BLANK : fromJob(editing)}
          heading={editing === "new" ? "New job" : "Edit job"}
          onCancel={() => setEditing(null)}
          onSubmit={handleSave}
        />
      </section>
    );
  }

  return (
    <section className="glass w-full p-6 sm:p-8">
      <div className="list-head">
        <div>
          <p className="text-xs tracking-[0.4em] uppercase text-[var(--silver-600)]">Jobs</p>
          {!loading && !error && jobs && (
            <p className="mt-1 text-sm text-[var(--silver-600)]">
              {jobs.length === 0 ? "No jobs to show" : `Showing ${jobs.length} ${jobs.length === 1 ? "job" : "jobs"}`}
            </p>
          )}
        </div>
        <button className="btn-dark" onClick={() => setEditing("new")}>New job</button>
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><DocLoader label="Loading jobs" /></div>
      ) : error ? (
        <div className="empty">
          <p className="form-error" role="alert">{error}</p>
          <button className="btn-dark mt-4" onClick={() => { setLoading(true); setError(null); setReloadKey((k) => k + 1); }}>Retry</button>
        </div>
      ) : jobs && jobs.length === 0 ? (
        <div className="empty">
          <p className="text-lg font-semibold">No jobs yet</p>
          <p className="mt-1 text-sm text-[var(--silver-600)]">Create a job to start matching candidates.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="list">
            <thead>
              <tr>
                <th>Job</th><th>Location</th><th>Experience</th><th>Rate</th><th>Status</th><th>Required skills</th><th></th>
              </tr>
            </thead>
            <tbody>
              {jobs!.map((j, i) => (
                <tr
                  key={j.id}
                  className="row-in clickable"
                  tabIndex={0}
                  onClick={() => setEditing(j)}
                  onKeyDown={(e) => { if (e.key === "Enter") setEditing(j); }}
                  style={{ animationDelay: `${Math.min(i, 12) * 40}ms` }}
                >
                  <td>
                    <div className="font-semibold">{j.title}</div>
                    <div className="text-xs text-[var(--silver-600)]">{j.client ?? NM}</div>
                  </td>
                  <td>
                    <div>{j.location ?? NM}</div>
                    <div className="text-xs text-[var(--silver-600)]">{j.work_mode ?? NM}</div>
                  </td>
                  <td className="whitespace-nowrap">
                    {j.required_experience_years !== null ? `${Number(j.required_experience_years)} yrs` : NM}
                  </td>
                  <td className="whitespace-nowrap">{j.rate !== null ? Number(j.rate) : NM}</td>
                  <td><span className={statusTone(j.status)}>{j.status}</span></td>
                  <td>
                    {j.required_skills.length === 0 ? (
                      <span className="text-sm text-[var(--silver-600)]">{NM}</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {j.required_skills.map((s) => <span key={s} className="badge">{s}</span>)}
                      </div>
                    )}
                  </td>
                  <td></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}