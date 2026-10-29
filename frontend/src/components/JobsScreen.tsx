"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import MatchesView from "@/components/MatchesView";
import {
  deleteJob, getSkillReviewList, listJobs, readJobDescription, reviewSkill, saveJob, SessionError,
  type Job, type SkillReviewList,
} from "@/lib/api";
import { useVisa } from "@/lib/visa";

const NM = "Not Mentioned";
const MODES = ["Remote", "Hybrid", "Onsite"];
const STATUSES = ["Open", "On Hold", "Filled", "Closed"];
const PREFS = [
  { value: "", label: "Not set" },
  { value: "relocation_ok", label: "Relocation OK" },
  { value: "relocation_not_ok", label: "Relocation Not OK" },
  { value: "multiple", label: "Multiple locations" },
];
const PREF_LABEL: Record<string, string> = Object.fromEntries(PREFS.map((p) => [p.value, p.label]));
const PREF_HELP: Record<string, string> = {
  "": "No rule is applied. Location only adds a small bonus to the match score.",
  relocation_ok: "Candidates anywhere in the US are eligible. Relocation is acceptable; it does not mean it is paid for.",
  relocation_not_ok: "Only candidates in the job's state are eligible, for example anyone in Texas for a Dallas, TX job.",
  multiple: "Add each location with its own relocation setting. A candidate qualifies if any one location accepts them.",
};

type LocRow = { city: string; state: string; ok: boolean };
type SkillMark = "Correct" | "Neutral" | "Wrong";
type SkillChoice = { name: string; mark: SkillMark };
type JobFull = Job & {
  location_preference: string | null;
  locations: { city: string | null; state: string; relocation_ok: boolean }[];
};

type Form = {
  title: string; client: string; description: string; location: string; workMode: string;
  years: string; visa: string[]; rate: string; status: string; required: string; preferred: string;
  pref: string; locs: LocRow[];
};

const BLANK: Form = {
  title: "", client: "", description: "", location: "", workMode: "",
  years: "", visa: [], rate: "", status: "Open", required: "", preferred: "",
  pref: "", locs: [],
};

function fromJob(j: JobFull): Form {
  return {
    title: j.title, client: j.client ?? "", description: j.description ?? "", location: j.location ?? "",
    workMode: j.work_mode ?? "", years: j.required_experience_years ?? "", visa: j.visa_requirements ?? [],
    rate: j.rate ?? "", status: j.status, required: j.required_skills.join(", "), preferred: j.preferred_skills.join(", "),
    pref: j.location_preference ?? "",
    locs: j.locations.map((l) => ({ city: l.city ?? "", state: l.state, ok: l.relocation_ok })),
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
  if (f.pref === "relocation_not_ok" && !/,\s*[A-Za-z]/.test(f.location)) {
    return { error: "Relocation Not OK needs a job location with a US state, for example Dallas, TX" };
  }
  if (f.pref === "multiple") {
    if (f.locs.length === 0) return { error: "Add at least one location" };
    if (f.locs.some((l) => !l.state.trim())) return { error: "Each location needs a state" };
  }
  return {
    payload: {
      title: f.title.trim(), client: orNull(f.client), description: orNull(f.description),
      location: orNull(f.location), work_mode: orNull(f.workMode), required_experience_years: years,
      visa_requirements: f.visa, rate, status: f.status,
      required_skills: splitList(f.required), preferred_skills: splitList(f.preferred),
      location_preference: f.pref === "" ? null : f.pref,
      ...(f.pref === "multiple"
        ? { locations: f.locs.map((l) => ({ city: orNull(l.city), state: l.state.trim(), relocation_ok: l.ok })) }
        : {}),
    },
  };
}

function statusTone(s: string) {
  if (s === "Open") return "badge";
  if (s === "On Hold") return "badge warn";
  return "badge muted";
}

function JobForm({
  initial, heading, token, onCancel, onSubmit, onSessionEnd,
}: {
  initial: Form; heading: string; token: string; onCancel: () => void;
  onSubmit: (p: Record<string, unknown>) => Promise<void>; onSessionEnd: () => void;
}) {
  const [f, setF] = useState<Form>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jdText, setJdText] = useState("");
  const [readingJD, setReadingJD] = useState(false);
  const [jdMessage, setJdMessage] = useState<string | null>(null);
  const [hasParsedJD, setHasParsedJD] = useState(false);
  const [skillChoices, setSkillChoices] = useState<SkillChoice[]>([]);
  const { options: visaOptions, error: visaError } = useVisa(token);
  const set = (k: keyof Form, v: string) => setF((p) => ({ ...p, [k]: v }));
  const setLoc = (i: number, patch: Partial<LocRow>) =>
    setF((p) => ({ ...p, locs: p.locs.map((l, n) => (n === i ? { ...l, ...patch } : l)) }));

  async function fillFromJD() {
    if (readingJD) return;
    setReadingJD(true);
    setError(null);
    setJdMessage(null);
    setHasParsedJD(false);
    try {
      const draft = await readJobDescription(token, jdText);
      setHasParsedJD(true);
      setF((p) => ({
        ...p,
        title: draft.title ?? p.title,
        client: draft.client ?? p.client,
        description: jdText,
        location: draft.location ?? p.location,
        workMode: draft.work_mode ?? p.workMode,
        years: draft.required_experience_years === null ? p.years : String(draft.required_experience_years),
        visa: draft.visa_requirements.length ? draft.visa_requirements : p.visa,
        rate: draft.rate === null ? p.rate : String(draft.rate),
      }));
      const required = new Set(draft.required_skills.map((name) => name.toLowerCase()));
      const preferred = new Set(draft.preferred_skills.map((name) => name.toLowerCase()));
      setSkillChoices(draft.skill_suggestions.map((name) => ({
        name,
        mark: required.has(name.toLowerCase()) ? "Correct"
          : preferred.has(name.toLowerCase()) ? "Neutral" : "Wrong",
      })));
      const details = [
        ...draft.notes,
        ...(draft.unrecognized.length ? [`Review unrecognized requirements: ${draft.unrecognized.join(", ")}`] : []),
      ];
      setJdMessage(details.length ? `Draft filled. ${details.join(" ")}` : "Draft filled. Review the fields before saving.");
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not read the job description");
    } finally {
      setReadingJD(false);
    }
  }

  async function submit() {
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
      <div className="mt-6">
        {heading === "New job" && (
          <div className="match-card mb-5">
            <label className="field">
              <span>Paste a job description to fill the form</span>
              <textarea rows={5} value={jdText} onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the full job description here" />
            </label>
            <button className="btn-ghost mt-3" type="button" disabled={readingJD || jdText.trim().length < 20}
              onClick={() => void fillFromJD()}>{readingJD ? "Reading..." : "Fill fields from JD"}</button>
            {jdMessage && <p className="mt-3 text-sm text-[var(--silver-600)]" role="status">{jdMessage}</p>}
          </div>
        )}
        {heading === "New job" && hasParsedJD && (
          <div className="match-card mb-5">
            <h2 className="font-semibold">Review extracted skills</h2>
            <p className="mt-1 text-sm text-[var(--silver-600)]">
              Mark each skill: Correct adds it to Required Skills, Neutral adds it to Preferred Skills,
              and Wrong excludes it.
            </p>
            {skillChoices.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--silver-600)]">
                No skill candidates were extracted. You can still add skills manually in the fields below.
              </p>
            ) : (
              <>
                <div className="mt-4 space-y-3">
                  {skillChoices.map(({ name, mark }, index) => (
                    <div key={`${name}-${index}`} className="flex flex-col gap-2 border-b border-[var(--silver-200)] pb-3 sm:flex-row sm:items-center">
                      <span className="min-w-0 flex-1 font-medium">{name}</span>
                      <label className="field sm:w-48">
                        <span className="sr-only">Mark {name}</span>
                        <select value={mark} onChange={(e) => {
                          const nextMark = e.target.value as SkillMark;
                          setSkillChoices((previous) => previous.map((choice, i) =>
                            i === index ? { ...choice, mark: nextMark } : choice));
                        }}>
                          <option value="Correct">Correct — Required</option>
                          <option value="Neutral">Neutral — Preferred</option>
                          <option value="Wrong">Wrong — Exclude</option>
                        </select>
                      </label>
                    </div>
                  ))}
                </div>
                <button className="btn-ghost mt-4" type="button" onClick={() => {
                  setF((previous) => ({
                    ...previous,
                    required: skillChoices.filter((choice) => choice.mark === "Correct")
                      .map((choice) => choice.name).join(", "),
                    preferred: skillChoices.filter((choice) => choice.mark === "Neutral")
                      .map((choice) => choice.name).join(", "),
                  }));
                }}>Apply skill choices</button>
              </>
            )}
          </div>
        )}
        <div className="form-grid">
          <label className="field span-all"><span>Job title *</span>
            <input value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. Senior Java Developer" /></label>
          <label className="field"><span>Client</span>
            <input value={f.client} onChange={(e) => set("client", e.target.value)} placeholder="Client name" /></label>
          <label className="field"><span>Location</span>
            <input value={f.location} onChange={(e) => set("location", e.target.value)} placeholder="City, State" /></label>
          <label className="field"><span>Location preference</span>
            <select value={f.pref} onChange={(e) => setF((p) => ({ ...p, pref: e.target.value }))}>
              {PREFS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select></label>
          <label className="field"><span>Work mode</span>
            <select value={f.workMode} onChange={(e) => set("workMode", e.target.value)}>
              <option value="">Not specified</option>
              {MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select></label>
          <p className="span-all text-xs text-[var(--silver-600)]">{PREF_HELP[f.pref] ?? ""}</p>

          {f.pref === "multiple" && (
            <div className="span-all space-y-3">
              {f.locs.map((l, i) => (
                <div key={i} className="match-card">
                  <div className="form-grid">
                    <label className="field"><span>City (optional)</span>
                      <input value={l.city} onChange={(e) => setLoc(i, { city: e.target.value })} placeholder="e.g. Austin" /></label>
                    <label className="field"><span>State</span>
                      <input value={l.state} onChange={(e) => setLoc(i, { state: e.target.value })} placeholder="TX or Texas" /></label>
                    <label className="field"><span>Relocation</span>
                      <select value={l.ok ? "ok" : "not"} onChange={(e) => setLoc(i, { ok: e.target.value === "ok" })}>
                        <option value="not">Relocation Not OK</option>
                        <option value="ok">Relocation OK</option>
                      </select></label>
                  </div>
                  <button className="btn-ghost mt-3" type="button"
                    onClick={() => setF((p) => ({ ...p, locs: p.locs.filter((_, n) => n !== i) }))}>Remove this location</button>
                </div>
              ))}
              <button className="btn-ghost" type="button"
                onClick={() => setF((p) => ({ ...p, locs: [...p.locs, { city: "", state: "", ok: false }] }))}>Add a location</button>
            </div>
          )}

          <label className="field"><span>Status</span>
            <select value={f.status} onChange={(e) => set("status", e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label className="field"><span>Required experience (years)</span>
            <input type="number" min="0" step="0.5" onWheel={(e) => e.currentTarget.blur()} value={f.years} onChange={(e) => set("years", e.target.value)} placeholder="e.g. 5" /></label>
          <label className="field"><span>Rate</span>
            <input type="number" min="0" step="0.01" onWheel={(e) => e.currentTarget.blur()} value={f.rate} onChange={(e) => set("rate", e.target.value)} placeholder="e.g. 70" /></label>
          <fieldset className="span-all min-w-0 border-0 p-0">
            <legend className="mb-2 text-xs tracking-[0.18em] uppercase text-[var(--silver-600)]">Visa requirements</legend>
            {visaError && <p className="form-error mb-2" role="alert">{visaError}</p>}
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
              {visaOptions.map((option) => (
                <label key={option.value} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={f.visa.includes(option.value)}
                    onChange={(e) => setF((p) => ({
                      ...p,
                      visa: e.target.checked
                        ? [...p.visa, option.value]
                        : p.visa.filter((value) => value !== option.value),
                    }))} />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="field span-all"><span>Required skills (comma separated)</span>
            <input value={f.required} onChange={(e) => set("required", e.target.value)} placeholder="e.g. Java, Spring Boot, AWS" /></label>
          <label className="field span-all"><span>Preferred skills (comma separated)</span>
            <input value={f.preferred} onChange={(e) => set("preferred", e.target.value)} placeholder="e.g. Docker, Kubernetes" /></label>
          <p className="span-all text-xs text-[var(--silver-600)]">
            Skills not already in the catalog are added to the skill review queue when you save.
          </p>
          <label className="field span-all"><span>Description</span>
            <textarea rows={6} value={f.description} onChange={(e) => set("description", e.target.value)} placeholder="Paste the job description" /></label>
        </div>
        <p className="form-error mt-3" role="alert" aria-live="polite">{error ?? "\u00A0"}</p>
        <div className="flex gap-3">
          <button className="btn-dark" onClick={submit} disabled={saving}>{saving ? "Saving..." : "Save job"}</button>
          <button className="btn-ghost" onClick={onCancel} disabled={saving}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

export default function JobsScreen({
  token, onSessionEnd, canManageJobs, canDeleteJobs, onOpenCandidate,
}: {
  token: string; onSessionEnd: () => void; canManageJobs: boolean; canDeleteJobs: boolean;
  onOpenCandidate: (id: number) => void;
}) {
  const [jobs, setJobs] = useState<JobFull[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editing, setEditing] = useState<JobFull | "new" | null>(null);
  const [matchJob, setMatchJob] = useState<JobFull | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [skillReview, setSkillReview] = useState<SkillReviewList | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [mergeTargets, setMergeTargets] = useState<Record<number, number | "">>({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = (await listJobs(token)) as unknown as JobFull[];
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

  async function loadSkillReview() {
    setReviewLoading(true);
    setReviewError(null);
    try {
      setSkillReview(await getSkillReviewList(token));
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setReviewError(err instanceof Error ? err.message : "Could not load skills for review");
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleSkillReview(skillId: number, canonicalSkillId: number | null) {
    setReviewError(null);
    try {
      await reviewSkill(token, skillId, canonicalSkillId);
      await loadSkillReview();
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setReviewError(err instanceof Error ? err.message : "Could not review this skill");
    }
  }

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
    if (reviewOpen) void loadSkillReview();
  }

  async function handleDelete(job: JobFull) {
    if (!window.confirm(`Permanently delete "${job.title}" and its submissions/interviews?`)) return;
    setDeletingId(job.id);
    setError(null);
    try {
      await deleteJob(token, job.id);
      setLoading(true);
      setReloadKey((key) => key + 1);
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not delete the job");
    } finally {
      setDeletingId(null);
    }
  }

  if (matchJob !== null) {
    return <MatchesView key={matchJob.id} token={token} jobId={matchJob.id} onBack={() => setMatchJob(null)} onSessionEnd={onSessionEnd} onOpenCandidate={onOpenCandidate} />;
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
          token={token}
          onSessionEnd={onSessionEnd}
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
        {canManageJobs && <button className="btn-dark" onClick={() => setEditing("new")}>New job</button>}
      </div>

      {canManageJobs && <div className="mb-5">
        <button
          className="btn-ghost"
          onClick={() => {
            const opening = !reviewOpen;
            setReviewOpen(opening);
            if (opening) void loadSkillReview();
          }}
          aria-expanded={reviewOpen}
        >
          {reviewOpen ? "Hide skill review" : "Review new skills"}
        </button>
        {reviewOpen && (
          <div className="match-card mt-3">
            <h2 className="font-semibold">New skills to review</h2>
            <p className="mt-1 text-sm text-[var(--silver-600)]">
              Approve a skill to keep it as a separate catalog entry, or merge it into an existing skill.
            </p>
            {reviewLoading ? (
              <div className="py-6 flex justify-center"><DocLoader label="Loading skills for review" /></div>
            ) : reviewError ? (
              <p className="form-error mt-3" role="alert">{reviewError}</p>
            ) : skillReview?.pending.length === 0 ? (
              <p className="mt-3 text-sm text-[var(--silver-600)]">No skills are waiting for review.</p>
            ) : skillReview && (
              <div className="mt-4 space-y-3">
                {skillReview.pending.map((skill) => (
                  <div key={skill.id} className="flex flex-col gap-3 border-b border-[var(--silver-200)] pb-3 sm:flex-row sm:items-center">
                    <span className="min-w-32 font-medium">{skill.name}</span>
                    <button className="btn-ghost" onClick={() => void handleSkillReview(skill.id, null)}>
                      Approve as new skill
                    </button>
                    <select
                      className="min-w-0 flex-1"
                      aria-label={`Merge ${skill.name} into`}
                      value={mergeTargets[skill.id] ?? ""}
                      onChange={(e) => setMergeTargets((old) => ({
                        ...old, [skill.id]: e.target.value === "" ? "" : Number(e.target.value),
                      }))}
                    >
                      <option value="">Select existing skill to merge</option>
                      {skillReview.approved.map((target) => (
                        <option key={target.id} value={target.id}>{target.name}</option>
                      ))}
                    </select>
                    <button
                      className="btn-ghost"
                      disabled={!mergeTargets[skill.id]}
                      onClick={() => void handleSkillReview(skill.id, mergeTargets[skill.id] || null)}
                    >
                      Merge
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>}

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
                    {j.location_preference && (
                      <div className="mt-1">
                        <span className="badge">{PREF_LABEL[j.location_preference] ?? j.location_preference}</span>
                      </div>
                    )}
                    {j.location_preference === "multiple" && j.locations.map((l, n) => (
                      <div key={n} className="text-xs text-[var(--silver-600)]">
                        {(l.city ? l.city + ", " : "") + l.state} &middot; {l.relocation_ok ? "relocation OK" : "relocation not OK"}
                      </div>
                    ))}
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
                  <td>
                    <button className="btn-ghost" onClick={(e) => { e.stopPropagation(); setMatchJob(j); }}>Matches</button>
                    {canDeleteJobs && (
                      <button
                        className="btn-ghost ml-2"
                        disabled={deletingId === j.id}
                        onClick={(e) => { e.stopPropagation(); void handleDelete(j); }}
                      >
                        {deletingId === j.id ? "Deleting..." : "Delete"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}