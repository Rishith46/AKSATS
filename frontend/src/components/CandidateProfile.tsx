"use client";

import { useEffect, useState } from "react";
import CandidateNotes from "@/components/CandidateNotes";
import DocLoader from "@/components/DocLoader";
import { getProfile, SessionError, type Profile } from "@/lib/api";

const NM = "Not Mentioned";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function fmtExp(date: string | null, precision: string | null): string | null {
  if (!date) return null;
  const [y, m] = date.split("-");
  if (precision === "month" && m) return `${MONTHS[parseInt(m, 10) - 1] ?? ""} ${y}`.trim();
  return y;
}

function fmtDay(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? NM : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function Field({ label, value, source }: { label: string; value: string | null; source?: string }) {
  return (
    <div className="kv">
      <span className="kv-label">{label}</span>
      <span className={value ? "kv-value" : "kv-value muted-text"}>{value ?? NM}</span>
      {value && source && <span className="src-tag">{source}</span>}
    </div>
  );
}

export default function CandidateProfile({
  token, id, onBack, onSessionEnd,
}: { token: string; id: number; onBack: () => void; onSessionEnd: () => void }) {
  const [p, setP] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getProfile(token, id);
        if (cancelled) return;
        setP(data);
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
  }, [token, id, reloadKey, onSessionEnd]);

  return (
    <section className="glass w-full p-6 sm:p-8">
      <button className="btn-ghost" onClick={onBack}>&larr; Back to candidates</button>

      {loading ? (
        <div className="py-16 flex justify-center"><DocLoader label="Loading profile" /></div>
      ) : error ? (
        <div className="empty">
          <p className="form-error" role="alert">{error}</p>
          <button className="btn-dark mt-4" onClick={() => { setLoading(true); setError(null); setReloadKey((k) => k + 1); }}>Retry</button>
        </div>
      ) : p ? (
        <div className="fade-in">
          <div className="profile-head">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{p.full_name ?? NM}</h1>
              <p className="mt-1 text-sm text-[var(--silver-600)]">Added {fmtDay(p.created_at)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="badge">{p.status}</span>
              <span className={p.parse_status === "Parsed" ? "badge" : "badge warn"}>{p.parse_status}</span>
              {p.archived_at && <span className="badge muted">Archived</span>}
            </div>
          </div>

          <h2 className="section-title">Contact</h2>
          <div className="profile-grid">
            <Field label="Email" value={p.email} source={p.field_sources.email} />
            <Field label="Phone" value={p.phone} source={p.field_sources.phone} />
            <Field label="Location" value={p.location} source={p.field_sources.location} />
            <Field label="LinkedIn" value={p.linkedin_url} source={p.field_sources.linkedin_url} />
          </div>

          <h2 className="section-title">Recruiting</h2>
          <div className="profile-grid">
            <Field label="Work authorization" value={p.visa_status} source={p.field_sources.visa_status} />
            <Field label="Rate" value={p.rate} source={p.field_sources.rate} />
            <Field label="Total experience (years)" value={p.total_experience_years} source={p.field_sources.total_experience_years} />
          </div>

          <h2 className="section-title">Experience</h2>
          {p.experiences.length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No work history found in the resume.</p>
          ) : (
            <ol className="timeline">
              {p.experiences.map((e) => {
                const start = fmtExp(e.start_date, e.start_precision);
                const end = e.is_current ? "Present" : fmtExp(e.end_date, e.end_precision);
                return (
                  <li key={e.id} className="timeline-item">
                    <p className="font-semibold">{e.title ?? NM}</p>
                    <p className="text-sm">{e.company ?? NM}</p>
                    <p className="text-xs text-[var(--silver-600)]">
                      {start ?? NM} to {end ?? NM}
                    </p>
                  </li>
                );
              })}
            </ol>
          )}

          <h2 className="section-title">Skills</h2>
          {p.skills.length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No skills matched in the resume.</p>
          ) : (
            <div className="skill-grid">
              {p.skills.map((s) => (
                <div key={s.name} className="skill-card">
                  <p className="font-semibold">{s.name}</p>
                  <p className="mt-1 text-xs text-[var(--silver-600)]">{s.evidence ?? "No evidence sentence"}</p>
                </div>
              ))}
            </div>
          )}

          <h2 className="section-title">Notes</h2>
          <CandidateNotes token={token} id={p.id} onSessionEnd={onSessionEnd} />

          <h2 className="section-title">Documents</h2>
          {p.documents.length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No documents.</p>
          ) : (
            <div className="table-wrap">
              <table className="list">
                <thead><tr><th>File</th><th>Type</th><th>Version</th><th>Uploaded</th></tr></thead>
                <tbody>
                  {p.documents.map((d) => (
                    <tr key={d.id}>
                      <td className="font-semibold">{d.filename}</td>
                      <td>{d.kind}</td>
                      <td>
                        {d.version_no ? `v${d.version_no}` : NM}
                        {d.is_current && <span className="badge ml-2">Current</span>}
                      </td>
                      <td className="whitespace-nowrap">{fmtDay(d.uploaded_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}