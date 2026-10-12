"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { getMatches, SessionError, type MatchCandidate, type MatchResult } from "@/lib/api";

const NM = "Not Mentioned";

const SIGNAL_LABELS: Record<string, string> = {
  required_skills: "Required skills",
  semantic_similarity: "Semantic similarity",
  relevant_experience: "Relevant experience",
  recent_experience: "Recent experience",
  job_title: "Job title",
  location: "Location",
  visa: "Work authorization",
};

const tidy = (s: string | null) => (s ? s.replace(/\s+/g, " ").trim() : "No evidence sentence");

function Card({ c, rank, onOpen }: { c: MatchCandidate; rank: number; onOpen: (id: number) => void }) {
  const entries = Object.entries(c.signals);
  return (
    <article className="match-card">
      <div className="match-top">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase text-[var(--silver-600)]">#{rank}</p>
          <button className="link-name" onClick={() => onOpen(c.candidate_id)}>{c.full_name ?? NM}</button>
          <div className="mt-1 flex flex-wrap gap-2">
            <span className={c.parse_status === "Parsed" ? "badge" : "badge warn"}>{c.parse_status}</span>
            {c.restrictions.map((r, i) => (
              <span key={i} className="badge bad">{r.type}{r.blocking ? " (blocking)" : ""}</span>
            ))}
          </div>
        </div>
        <div className="match-score">
          <span className="match-num">{c.score_floor}</span>
          <span className="text-xs text-[var(--silver-600)]">ranking score, out of 100</span>
          <div className="scorebar" aria-hidden="true"><div className="scorefill" style={{ width: `${Math.min(c.score_floor, 100)}%` }} /></div>
          <span className="text-xs text-[var(--silver-600)]">
            On known data: {c.score ?? "n/a"} &middot; Coverage: {c.coverage_percent}%
          </span>
        </div>
      </div>

      <div className="match-skills">
        <p className="kv-label">Required skills</p>
        <div className="flex flex-wrap gap-1">
          {c.matching_required.map((m) => <span key={m.skill} className="badge">{m.skill}</span>)}
          {c.missing_required.map((m) => <span key={m} className="badge bad">Missing: {m}</span>)}
          {c.matching_required.length + c.missing_required.length === 0 && <span className="text-sm text-[var(--silver-600)]">The job lists none</span>}
        </div>
        <p className="kv-label mt-3">Preferred skills</p>
        <div className="flex flex-wrap gap-1">
          {c.matching_preferred.map((m) => <span key={m.skill} className="badge">{m.skill}</span>)}
          {c.missing_preferred.map((m) => <span key={m} className="badge muted">Missing: {m}</span>)}
          {c.matching_preferred.length + c.missing_preferred.length === 0 && <span className="text-sm text-[var(--silver-600)]">The job lists none</span>}
        </div>
      </div>

      <details className="match-details">
        <summary>Signal breakdown and evidence</summary>
        <div className="table-wrap mt-3">
          <table className="list">
            <thead><tr><th>Signal</th><th>Weight</th><th>Result</th><th>Detail</th></tr></thead>
            <tbody>
              {entries.map(([k, s]) => (
                <tr key={k}>
                  <td className="font-semibold">{SIGNAL_LABELS[k] ?? k}</td>
                  <td>{s.weight}</td>
                  <td>{s.score === null ? "Unknown" : `${Math.round(s.score * 100)}%`}</td>
                  <td className="text-sm text-[var(--silver-600)]">{s.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {[...c.matching_required, ...c.matching_preferred].length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="kv-label">Where the skills appear in the resume</p>
            {[...c.matching_required, ...c.matching_preferred].map((m) => (
              <p key={m.skill} className="text-xs"><span className="font-semibold">{m.skill}:</span> {tidy(m.evidence)}</p>
            ))}
          </div>
        )}
      </details>
    </article>
  );
}

export default function MatchesView({
  token, jobId, onBack, onSessionEnd, onOpenCandidate,
}: { token: string; jobId: number; onBack: () => void; onSessionEnd: () => void; onOpenCandidate: (id: number) => void }) {
  const [data, setData] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await getMatches(token, jobId);
        if (cancelled) return;
        setData(d);
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
  }, [token, jobId, reloadKey, onSessionEnd]);

  return (
    <section className="glass w-full p-6 sm:p-8">
      <button className="btn-ghost" onClick={onBack}>&larr; Back to jobs</button>
      {loading ? (
        <div className="py-16 flex justify-center"><DocLoader label="Scoring candidates" /></div>
      ) : error ? (
        <div className="empty">
          <p className="form-error" role="alert">{error}</p>
          <button className="btn-dark mt-4" onClick={() => { setLoading(true); setError(null); setReloadKey((k) => k + 1); }}>Retry</button>
        </div>
      ) : data ? (
        <div className="fade-in">
          <h1 className="mt-5 text-2xl font-bold tracking-tight">Matches for {data.job_title}</h1>
          <p className="mt-2 text-sm text-[var(--silver-600)]">{data.label}</p>
          <p className="mt-1 text-xs text-[var(--silver-600)]">{data.ranking}</p>
          {data.not_scored.length > 0 && (
            <p className="mt-1 text-xs text-[#7a4a05]">
              Not scored yet: {data.not_scored.map((k) => (SIGNAL_LABELS[k] ?? k).toLowerCase()).join(", ")}.
            </p>
          )}
          {data.candidates.length === 0 ? (
            <div className="empty"><p className="text-lg font-semibold">No candidates to rank</p></div>
          ) : (
            <div className="mt-6 space-y-4">
              {data.candidates.map((c, i) => (
                <Card key={c.candidate_id} c={c} rank={i + 1} onOpen={onOpenCandidate} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}