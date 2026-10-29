"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { SessionError } from "@/lib/api";
import {
  ApiError, addExperience, addSkill, editExperience, getFullProfile, patchCandidate,
  removeExperience, removeSkill, type FullProfile,
} from "@/lib/edit";
import {
  buildPatch, checkEmail, checkLastYear, checkLinkedIn, checkPartialDate, checkPhone, checkRate,
  checkYears, formFromProfile, type FormState,
} from "@/lib/validate";
import { useVisa } from "@/lib/visa";

const NM = "Not Mentioned";

type ExpForm = {
  id: number | null;
  company: string;
  title: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  description: string;
};

const BLANK_EXP: ExpForm = { id: null, company: "", title: "", location: "", start: "", end: "", current: false, description: "" };

function Field({
  label, value, onChange, error, placeholder, span,
}: { label: string; value: string; onChange: (v: string) => void; error?: string; placeholder?: string; span?: boolean }) {
  return (
    <label className={"field" + (span ? " span-all" : "")}>
      <span>{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-invalid={error ? true : undefined}
      />
      {error && <small className="mt-1 block text-xs text-[#b42318]">{error}</small>}
    </label>
  );
}

export default function CandidateEditForm({
  token, id, onClose, onSessionEnd,
}: { token: string; id: number; onClose: () => void; onSessionEnd: () => void }) {
  const [prof, setProf] = useState<FullProfile | null>(null);
  const [initial, setInitial] = useState<FormState | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirmLeave, setConfirmLeave] = useState(false);
  const { options: visaOptions } = useVisa(token);

  const [skillName, setSkillName] = useState("");
  const [skillYears, setSkillYears] = useState("");
  const [skillLast, setSkillLast] = useState("");
  const [skillEvidence, setSkillEvidence] = useState("");
  const [editingSkillId, setEditingSkillId] = useState<number | null>(null);
  const [skillMsg, setSkillMsg] = useState<string | null>(null);
  const [unknownSkill, setUnknownSkill] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [exp, setExp] = useState<ExpForm | null>(null);
  const [expError, setExpError] = useState<string | null>(null);
  const [expMsg, setExpMsg] = useState<string | null>(null);
  const [removing, setRemoving] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await getFullProfile(token, id);
        if (cancelled) return;
        const f = formFromProfile(p);
        setProf(p);
        setInitial(f);
        setForm(f);
        setLoadError(null);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof SessionError) {
          onSessionEnd();
          return;
        }
        setLoadError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, id, onSessionEnd]);

  async function reload(resetForm: boolean) {
    const p = await getFullProfile(token, id);
    setProf(p);
    if (resetForm) {
      const f = formFromProfile(p);
      setInitial(f);
      setForm(f);
    }
  }

  function messageFrom(err: unknown): string | null {
    if (err instanceof SessionError) {
      onSessionEnd();
      return null;
    }
    return err instanceof Error ? err.message : "Something went wrong";
  }

  function setField(k: keyof FormState, v: string) {
    setForm((f) => (f ? { ...f, [k]: v } : f));
    setSaveMsg(null);
    setConfirmLeave(false);
  }

  const dirty = initial !== null && form !== null && Object.keys(buildPatch(initial, form)).length > 0;

  async function save() {
    if (!form || !initial || saving) return;
    const errs: Record<string, string> = {};
    const checks: [string, string | null][] = [
      ["email", checkEmail(form.email)],
      ["phone", checkPhone(form.phone)],
      ["linkedin", checkLinkedIn(form.linkedin)],
      ["rate", checkRate(form.rate)],
    ];
    for (const [k, m] of checks) if (m) errs[k] = m;
    setErrors(errs);
    if (Object.keys(errs).length > 0) {
      setSaveMsg({ ok: false, text: "Please fix the highlighted fields." });
      return;
    }
    const patch = buildPatch(initial, form);
    if (Object.keys(patch).length === 0) {
      setSaveMsg({ ok: true, text: "No changes to save." });
      return;
    }
    setSaving(true);
    setSaveMsg(null);
    try {
      await patchCandidate(token, id, patch);
      await reload(true);
      setSaveMsg({ ok: true, text: "Saved." });
    } catch (err) {
      const m = messageFrom(err);
      if (m) setSaveMsg({ ok: false, text: m });
    } finally {
      setSaving(false);
    }
  }

  async function submitSkill(createNew: boolean) {
    const name = createNew && unknownSkill ? unknownSkill : skillName.trim();
    if (!name) {
      setSkillMsg("Enter a skill name.");
      return;
    }
    const bad = checkYears(skillYears) ?? checkLastYear(skillLast);
    if (bad) {
      setSkillMsg(bad);
      return;
    }
    const body: Record<string, unknown> = { name };
    if (editingSkillId !== null || skillEvidence.trim()) {
      body.evidence = skillEvidence.trim() || null;
    }
    if (editingSkillId !== null) {
      body.years = skillYears.trim() === "" ? null : Number(skillYears);
      body.last_used_year = skillLast.trim() === "" ? null : Number(skillLast);
    } else {
      if (skillYears.trim() !== "") body.years = Number(skillYears);
      if (skillLast.trim() !== "") body.last_used_year = Number(skillLast);
    }
    if (createNew) body.create_if_missing = true;
    setBusy(true);
    setSkillMsg(null);
    try {
      await addSkill(token, id, body);
      await reload(false);
      setSkillName("");
      setSkillYears("");
      setSkillLast("");
      setSkillEvidence("");
      setEditingSkillId(null);
      setUnknownSkill(null);
      setSkillMsg(`${name} saved.`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setUnknownSkill(name);
      } else {
        const m = messageFrom(err);
        if (m) setSkillMsg(m);
      }
    } finally {
      setBusy(false);
    }
  }

  function editSkill(skill: FullProfile["skills"][number]) {
    setEditingSkillId(skill.skill_id);
    setSkillName(skill.name);
    setSkillYears(skill.years === null ? "" : String(skill.years));
    setSkillLast(skill.last_used_year === null ? "" : String(skill.last_used_year));
    setSkillEvidence(skill.evidence ?? "");
    setUnknownSkill(null);
    setSkillMsg(null);
  }

  function cancelSkillEdit() {
    setEditingSkillId(null);
    setSkillName("");
    setSkillYears("");
    setSkillLast("");
    setSkillEvidence("");
    setUnknownSkill(null);
  }

  async function dropSkill(skillId: number) {
    setBusy(true);
    setSkillMsg(null);
    try {
      const r = await removeSkill(token, id, skillId);
      await reload(false);
      setSkillMsg(r.note ? `${r.removed} removed. ${r.note}` : `${r.removed} removed.`);
    } catch (err) {
      const m = messageFrom(err);
      if (m) setSkillMsg(m);
    } finally {
      setBusy(false);
    }
  }

  async function saveExp() {
    if (!exp) return;
    const bad = checkPartialDate(exp.start) ?? checkPartialDate(exp.end);
    if (bad) {
      setExpError(bad);
      return;
    }
    if (!exp.company.trim() && !exp.title.trim()) {
      setExpError("Enter a company or a title.");
      return;
    }
    if (exp.current && exp.end.trim() !== "") {
      setExpError("A current job cannot have an end date.");
      return;
    }
    const body = {
      company: exp.company, title: exp.title, location: exp.location, start: exp.start, end: exp.end,
      is_current: exp.current, description: exp.description,
    };
    setBusy(true);
    setExpError(null);
    try {
      if (exp.id === null) await addExperience(token, id, body);
      else await editExperience(token, id, exp.id, body);
      await reload(false);
      setExp(null);
      setExpMsg("Job saved.");
    } catch (err) {
      const m = messageFrom(err);
      if (m) setExpError(m);
    } finally {
      setBusy(false);
    }
  }

  async function dropExp(eid: number) {
    setBusy(true);
    setExpMsg(null);
    try {
      await removeExperience(token, id, eid);
      await reload(false);
      setRemoving(null);
      setExpMsg("Job removed.");
    } catch (err) {
      const m = messageFrom(err);
      if (m) setExpMsg(m);
    } finally {
      setBusy(false);
    }
  }

  function leave() {
    if (dirty) setConfirmLeave(true);
    else onClose();
  }

  const setExpField = (k: keyof ExpForm, v: string | boolean) => setExp((x) => (x ? { ...x, [k]: v } : x));

  return (
    <section className="glass w-full p-6 sm:p-8">
      {loading ? (
        <div className="py-16 flex justify-center"><DocLoader label="Loading candidate" /></div>
      ) : loadError || !prof || !form ? (
        <div className="empty">
          <p className="form-error" role="alert">{loadError ?? "Could not load the candidate"}</p>
          <button className="btn-ghost mt-4" onClick={onClose}>Back</button>
        </div>
      ) : (
        <div className="fade-in">
          <h1 className="text-2xl font-bold tracking-tight">Edit candidate</h1>
          <p className="mt-1 text-sm text-[var(--silver-600)]">{prof.full_name ?? NM}</p>

          <h2 className="section-title">Contact</h2>
          <div className="form-grid">
            <Field label="Full name" value={form.fullName} onChange={(v) => setField("fullName", v)} />
            <Field label="Email" value={form.email} onChange={(v) => setField("email", v)} error={errors.email} placeholder="name@example.com" />
            <Field label="Phone" value={form.phone} onChange={(v) => setField("phone", v)} error={errors.phone} placeholder="(555) 010-0000" />
            <Field label="LinkedIn" value={form.linkedin} onChange={(v) => setField("linkedin", v)} error={errors.linkedin} placeholder="linkedin.com/in/..." />
          </div>

          <h2 className="section-title">Current location</h2>
          <div className="form-grid">
            <Field label="City" value={form.city} onChange={(v) => setField("city", v)} />
            <Field label="State" value={form.state} onChange={(v) => setField("state", v)} placeholder="TX or Texas" />
            <Field label="Country" value={form.country} onChange={(v) => setField("country", v)} placeholder="United States" />
          </div>
          <p className="mt-2 text-xs text-[var(--silver-600)]">
            Leave the country blank for a US location. A state outside the US needs the country written.
          </p>

          <h2 className="section-title">Recruiting</h2>
          <div className="form-grid">
            <label className="field">
              <span>Visa status</span>
              <select value={form.visa} onChange={(e) => setField("visa", e.target.value)}>
                <option value="">Not mentioned</option>
                {form.visa !== "" && !visaOptions.some((o) => o.value === form.visa) && (
                  <option value={form.visa}>{form.visa}</option>
                )}
                {visaOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <Field label="Expected or offered rate" value={form.rate} onChange={(v) => setField("rate", v)} error={errors.rate} placeholder="e.g. 65" />
            <label className="field">
              <span>Rate unit</span>
              <select value={form.rateUnit} onChange={(e) => setField("rateUnit", e.target.value)}>
                <option value="hour">per hour</option>
                <option value="year">per year</option>
              </select>
            </label>
            <Field label="Availability" value={form.availability} onChange={(v) => setField("availability", v)} placeholder="e.g. Immediate, 2 weeks notice" />
          </div>
          <p className="mt-3 text-sm text-[var(--silver-600)]">
            Estimated total experience: {prof.total_experience_years ? `${Number(prof.total_experience_years)} years` : NM}
            {prof.field_sources.total_experience_years ? ` (${prof.field_sources.total_experience_years})` : ""}. It is calculated from the jobs below.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button className="btn-dark" onClick={save} disabled={saving || !dirty}>{saving ? "Saving..." : "Save details"}</button>
            <button className="btn-ghost" onClick={leave} disabled={saving}>Cancel</button>
            {saveMsg && (
              <span className={"text-sm " + (saveMsg.ok ? "text-[var(--silver-600)]" : "text-[#b42318]")} role="status">{saveMsg.text}</span>
            )}
          </div>
          {confirmLeave && (
            <p className="mt-3 text-sm text-[#7a4a05]" role="alert">
              You have unsaved changes to the details.{" "}
              <button className="underline" onClick={onClose}>Discard them</button>{" "}
              <button className="underline" onClick={() => setConfirmLeave(false)}>Keep editing</button>
            </p>
          )}

          <h2 className="section-title">Skills</h2>
          <p className="mb-3 text-xs text-[var(--silver-600)]">
            Add only verified experience. Years and last-used dates affect match scoring; evidence appears in match notes and the ATS resume.
          </p>
          <div className="space-y-2">
            {prof.skills.length === 0 && <span className="text-sm text-[var(--silver-600)]">No skills yet.</span>}
            {prof.skills.map((s) => (
              <div key={s.skill_id} className="match-card flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold">{s.name}</p>
                  <p className="text-xs text-[var(--silver-600)]">
                    {[s.years !== null ? `${s.years} years` : null, s.last_used_year ? `last used ${s.last_used_year}` : null]
                      .filter(Boolean).join(" · ") || "No duration or recency recorded"}
                  </p>
                  {s.evidence && <p className="mt-1 text-sm">{s.evidence}</p>}
                </div>
                <div className="flex gap-2">
                  <button className="btn-ghost" onClick={() => editSkill(s)} disabled={busy}>Edit</button>
                  <button className="btn-ghost" aria-label={`Remove ${s.name}`} onClick={() => dropSkill(s.skill_id)} disabled={busy}>&times;</button>
                </div>
              </div>
            ))}
          </div>
          <div className="form-grid mt-4">
            <Field label="Skill" value={skillName} onChange={(v) => { setSkillName(v); setUnknownSkill(null); }} placeholder="e.g. Python or K8s" />
            <Field label="Years used" value={skillYears} onChange={setSkillYears} placeholder="optional" />
            <Field label="Last used (year)" value={skillLast} onChange={setSkillLast} placeholder="optional, e.g. 2026" />
            <label className="field span-all">
              <span>Resume evidence / impact</span>
              <textarea rows={3} value={skillEvidence} onChange={(e) => setSkillEvidence(e.target.value)}
                placeholder="Add a factual example from the candidate's experience" />
            </label>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button className="btn-dark" onClick={() => submitSkill(false)} disabled={busy}>
              {editingSkillId === null ? "Add skill" : "Save skill"}
            </button>
            {editingSkillId !== null && <button className="btn-ghost" onClick={cancelSkillEdit} disabled={busy}>Cancel edit</button>}
            <span className="text-xs text-[var(--silver-600)]">Adding a skill that is already listed updates its years.</span>
          </div>
          {unknownSkill && (
            <p className="mt-3 text-sm text-[#7a4a05]" role="alert">
              &ldquo;{unknownSkill}&rdquo; is not in the skills list.{" "}
              <button className="underline" onClick={() => submitSkill(true)} disabled={busy}>Add it as a new skill</button>{" "}
              <button className="underline" onClick={() => setUnknownSkill(null)}>Cancel</button>
            </p>
          )}
          {skillMsg && <p className="mt-3 text-sm text-[var(--silver-600)]" role="status">{skillMsg}</p>}

          <h2 className="section-title">Work experience</h2>
          <button className="btn-ghost" onClick={() => { setExp({ ...BLANK_EXP }); setExpError(null); setExpMsg(null); }} disabled={busy || exp !== null}>
            Add a job
          </button>
          {exp && (
            <div className="match-card mt-4">
              <div className="form-grid">
                <Field label="Company" value={exp.company} onChange={(v) => setExpField("company", v)} />
                <Field label="Title" value={exp.title} onChange={(v) => setExpField("title", v)} />
                <Field label="Location" value={exp.location} onChange={(v) => setExpField("location", v)} />
                <Field label="Start" value={exp.start} onChange={(v) => setExpField("start", v)} placeholder="YYYY-MM or YYYY" />
                <Field label="End" value={exp.end} onChange={(v) => setExpField("end", v)} placeholder="YYYY-MM or YYYY" />
                <label className="field">
                  <span>Current job</span>
                  <input type="checkbox" checked={exp.current} onChange={(e) => setExpField("current", e.target.checked)} />
                </label>
                <label className="field span-all">
                  <span>Responsibilities</span>
                  <textarea rows={4} value={exp.description} onChange={(e) => setExpField("description", e.target.value)} />
                </label>
              </div>
              {expError && <p className="form-error mt-2" role="alert">{expError}</p>}
              <div className="mt-3 flex gap-3">
                <button className="btn-dark" onClick={saveExp} disabled={busy}>{exp.id === null ? "Add job" : "Save job"}</button>
                <button className="btn-ghost" onClick={() => { setExp(null); setExpError(null); }} disabled={busy}>Cancel</button>
              </div>
            </div>
          )}
          {expMsg && <p className="mt-3 text-sm text-[var(--silver-600)]" role="status">{expMsg}</p>}
          <div className="mt-4 space-y-3">
            {prof.experiences.length === 0 && <p className="text-sm text-[var(--silver-600)]">No jobs recorded.</p>}
            {prof.experiences.map((e) => (
              <div key={e.id} className="match-card">
                <p className="font-semibold">{e.title ?? NM}{e.company ? ` \u00b7 ${e.company}` : ""}</p>
                <p className="text-xs text-[var(--silver-600)]">
                  {e.start ?? NM} to {e.is_current ? "Present" : e.end ?? NM}{e.location ? ` \u00b7 ${e.location}` : ""}
                </p>
                {e.description && (
                  <p className="mt-2 text-sm text-[var(--silver-600)]">
                    {e.description.length > 220 ? e.description.slice(0, 220) + "..." : e.description}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button className="btn-ghost" disabled={busy || exp !== null} onClick={() => {
                    setExp({ id: e.id, company: e.company ?? "", title: e.title ?? "", location: e.location ?? "",
                             start: e.start ?? "", end: e.end ?? "", current: e.is_current, description: e.description ?? "" });
                    setExpError(null);
                    setExpMsg(null);
                  }}>Edit</button>
                  {removing === e.id ? (
                    <span className="text-sm">
                      Remove this job?{" "}
                      <button className="underline" onClick={() => dropExp(e.id)} disabled={busy}>Yes, remove</button>{" "}
                      <button className="underline" onClick={() => setRemoving(null)}>Keep it</button>
                    </span>
                  ) : (
                    <button className="btn-ghost" disabled={busy} onClick={() => setRemoving(e.id)}>Remove</button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 flex items-center gap-3">
            <button className="btn-dark" onClick={leave}>Done</button>
            <span className="text-xs text-[var(--silver-600)]">Returns to the profile with the latest data.</span>
          </div>
        </div>
      )}
    </section>
  );
}