"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { listCandidatesFiltered, SessionError, type CandidateFilters, type CandidateRow } from "@/lib/api";
import { useVisa } from "@/lib/visa";

const NM = "Not Mentioned";
const EMPTY = { q: "", location: "", title: "", skill: "", minExp: "", visa: "" };
type Draft = typeof EMPTY;

function toFilters(d: Draft): CandidateFilters {
  const f: CandidateFilters = {};
  if (d.q.trim()) f.q = d.q.trim();
  if (d.location.trim()) f.location = d.location.trim();
  if (d.title.trim()) f.title = d.title.trim();
  if (d.visa) f.visa = d.visa;
  const skills = d.skill.split(",").map((s) => s.trim()).filter(Boolean);
  if (skills.length) f.skills = skills;
  const n = parseFloat(d.minExp);
  if (d.minExp.trim() !== "" && !isNaN(n) && n >= 0) f.minExperience = n;
  return f;
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? NM : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function fmtYears(v: string | null) {
  if (v === null || v === undefined) return NM;
  const n = Number(v);
  return isNaN(n) ? NM : `${n} yrs`;
}

function parseTone(s: string) {
  if (s === "Parsed") return "badge";
  if (s.startsWith("Possible Duplicate") || s === "Needs Review") return "badge warn";
  return "badge muted";
}

export default function CandidateList({
  token, onSessionEnd, onOpen,
}: { token: string; onSessionEnd: () => void; onOpen: (id: number) => void }) {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [applied, setApplied] = useState<Draft>(EMPTY);
  const [reloadKey, setReloadKey] = useState(0);
  const [rows, setRows] = useState<CandidateRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { options: visaOptions, label: visaLabel } = useVisa(token);

  const active = Object.values(applied).some((v) => v.trim() !== "");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listCandidatesFiltered(token, includeArchived, toFilters(applied));
        if (cancelled) return;
        setRows(data);
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
  }, [token, includeArchived, applied, reloadKey, onSessionEnd]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setApplied({ ...draft });
  }

  function clear() {
    setDraft(EMPTY);
    setApplied({ ...EMPTY });
    setLoading(true);
    setError(null);
  }

  function toggleArchived() {
    setLoading(true);
    setError(null);
    setIncludeArchived((v) => !v);
  }

  function retry() {
    setLoading(true);
    setError(null);
    setReloadKey((k) => k + 1);
  }

  function set(k: keyof Draft, v: string) {
    setDraft((d) => ({ ...d, [k]: v }));
  }

  return (
    <section className="glass w-full p-6 sm:p-8">
      <div className="list-head">
        <div>
          <p className="text-xs tracking-[0.4em] uppercase text-[var(--silver-600)]">Candidates</p>
          {!loading && !error && rows && (
            <p className="mt-1 text-sm text-[var(--silver-600)]">
              {rows.length === 0 ? "No candidates to show" : `Showing ${rows.length} ${rows.length === 1 ? "candidate" : "candidates"}`}
            </p>
          )}
        </div>
        <label className="switch">
          <input type="checkbox" checked={includeArchived} onChange={toggleArchived} />
          <span className="track"><span className="knob" /></span>
          <span className="switch-label">Include archived</span>
        </label>
      </div>

      <form className="filters" onSubmit={submit}>
        <label className="field">
          <span>Search</span>
          <input value={draft.q} onChange={(e) => set("q", e.target.value)} placeholder="Name, email or phone" />
        </label>
        <label className="field">
          <span>Location</span>
          <input value={draft.location} onChange={(e) => set("location", e.target.value)} placeholder="City or state" />
        </label>
        <label className="field">
          <span>Job title</span>
          <input value={draft.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. Engineer" />
        </label>
        <label className="field">
          <span>Skills</span>
          <input value={draft.skill} onChange={(e) => set("skill", e.target.value)} placeholder="e.g. Java, AWS" />
        </label>
        <label className="field">
          <span>Min. years</span>
          <input type="number" min="0" step="0.5" onWheel={(e) => e.currentTarget.blur()} value={draft.minExp} onChange={(e) => set("minExp", e.target.value)} placeholder="e.g. 5" />
        </label>
        <label className="field">
          <span>Visa status</span>
          <select value={draft.visa} onChange={(e) => set("visa", e.target.value)}>
            <option value="">Any</option>
            {visaOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        <div className="filter-actions">
          <button type="submit" className="btn-dark">Search</button>
          <button type="button" className="btn-ghost" onClick={clear}>Clear</button>
        </div>
      </form>

      {loading ? (
        <div className="py-16 flex justify-center">
          <DocLoader label="Loading candidates" />
        </div>
      ) : error ? (
        <div className="empty">
          <p className="form-error" role="alert">{error}</p>
          <button className="btn-dark mt-4" onClick={retry}>Retry</button>
        </div>
      ) : rows && rows.length === 0 ? (
        <div className="empty">
          {active ? (
            <>
              <p className="text-lg font-semibold">No candidates match these filters</p>
              <p className="mt-1 text-sm text-[var(--silver-600)]">Try fewer filters, or clear them to see everyone.</p>
              <button className="btn-ghost mt-4" onClick={clear}>Clear filters</button>
            </>
          ) : (
            <>
              <p className="text-lg font-semibold">No candidates yet</p>
              <p className="mt-1 text-sm text-[var(--silver-600)]">Candidates appear here once resumes are processed.</p>
            </>
          )}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="list">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Location</th>
                <th>Experience (est.)</th>
                <th>Visa</th>
                <th>Status</th>
                <th>Resume parsing</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {rows!.map((c, i) => (
                <tr
                  key={c.id}
                  className="row-in clickable"
                  tabIndex={0}
                  onClick={() => onOpen(c.id)}
                  onKeyDown={(e) => { if (e.key === "Enter") onOpen(c.id); }}
                  style={{ animationDelay: `${Math.min(i, 12) * 40}ms` }}
                >
                  <td>
                    <div className="font-semibold">
                      {c.full_name ?? NM}
                      {c.archived_at && <span className="badge muted ml-2">Archived</span>}
                    </div>
                    <div className="text-xs text-[var(--silver-600)]">{c.email ?? NM}</div>
                  </td>
                  <td>{c.location ?? NM}</td>
                  <td className="whitespace-nowrap">{fmtYears(c.total_experience_years)}</td>
                  <td>{visaLabel(c.visa_status) ?? NM}</td>
                  <td><span className="badge">{c.status}</span></td>
                  <td><span className={parseTone(c.parse_status)}>{c.parse_status}</span></td>
                  <td className="whitespace-nowrap">{fmtDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}