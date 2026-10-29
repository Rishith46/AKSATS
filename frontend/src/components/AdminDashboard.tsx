"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { getDashboardSummary, SessionError, type DashboardMonth, type DashboardSummary } from "@/lib/api";

function monthLabel(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", year: "2-digit", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}

function Metric({ label, value, note }: { label: string; value: number; note: string }) {
  return (
    <article className="glass p-5">
      <p className="text-sm text-[var(--silver-600)]">{label}</p>
      <p className="mt-2 text-3xl font-bold">{value.toLocaleString()}</p>
      <p className="mt-1 text-xs text-[var(--silver-600)]">{note}</p>
    </article>
  );
}

function MonthlyCharts({ months }: { months: DashboardMonth[] }) {
  const maxResumes = Math.max(1, ...months.map((m) => m.email_resumes + m.upload_resumes));
  const maxJobs = Math.max(1, ...months.map((m) => m.job_roles));
  const maxCandidates = Math.max(1, ...months.map((m) => m.new_candidates));

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <section className="glass p-5 sm:p-6">
        <h2 className="text-lg font-semibold">Resumes parsed by month</h2>
        <p className="mt-1 text-sm text-[var(--silver-600)]">
          Successful parsing, grouped by when processing completed.
        </p>
        <div className="dashboard-legend mt-4">
          <span><i className="dashboard-dot email" />Email</span>
          <span><i className="dashboard-dot upload" />Drag &amp; drop</span>
        </div>
        <div className="dashboard-chart" role="img" aria-label="Monthly parsed resumes by email and drag-and-drop upload">
          {months.map((m) => {
            const total = m.email_resumes + m.upload_resumes;
            return (
              <div className="dashboard-column" key={m.month} title={`${monthLabel(m.month)}: ${m.email_resumes} email, ${m.upload_resumes} upload`}>
                <span className="dashboard-bar-value">{total || ""}</span>
                <div className="dashboard-bar-track">
                  <div className="dashboard-bar-stack" style={{ height: `${total ? Math.max(4, total / maxResumes * 100) : 0}%` }}>
                    <i className="dashboard-bar email" style={{ height: `${total ? m.email_resumes / total * 100 : 0}%` }} />
                    <i className="dashboard-bar upload" style={{ height: `${total ? m.upload_resumes / total * 100 : 0}%` }} />
                  </div>
                </div>
                <span className="dashboard-month">{monthLabel(m.month)}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="glass p-5 sm:p-6">
        <h2 className="text-lg font-semibold">Job roles created by month</h2>
        <p className="mt-1 text-sm text-[var(--silver-600)]">New job roles by creation date.</p>
        <div className="dashboard-chart dashboard-jobs-chart" role="img" aria-label="Monthly job role creation">
          {months.map((m) => (
            <div className="dashboard-column" key={m.month} title={`${monthLabel(m.month)}: ${m.job_roles} job roles`}>
              <span className="dashboard-bar-value">{m.job_roles || ""}</span>
              <div className="dashboard-bar-track">
                <div className="dashboard-bar-stack" style={{ height: `${m.job_roles ? Math.max(4, m.job_roles / maxJobs * 100) : 0}%` }}>
                  <i className="dashboard-bar jobs" style={{ height: "100%" }} />
                </div>
              </div>
              <span className="dashboard-month">{monthLabel(m.month)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="glass p-5 sm:p-6">
        <h2 className="text-lg font-semibold">Active candidates added by month</h2>
        <p className="mt-1 text-sm text-[var(--silver-600)]">
          New candidates still active in the database; archived and merged records are excluded.
        </p>
        <div className="dashboard-chart dashboard-jobs-chart" role="img" aria-label="Active candidate additions by month">
          {months.map((m) => (
            <div className="dashboard-column" key={m.month} title={`${monthLabel(m.month)}: ${m.new_candidates} candidates`}>
              <span className="dashboard-bar-value">{m.new_candidates || ""}</span>
              <div className="dashboard-bar-track">
                <div className="dashboard-bar-stack" style={{ height: `${m.new_candidates ? Math.max(4, m.new_candidates / maxCandidates * 100) : 0}%` }}>
                  <i className="dashboard-bar jobs" style={{ height: "100%" }} />
                </div>
              </div>
              <span className="dashboard-month">{monthLabel(m.month)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function CandidateBreakdown({ title, items }: { title: string; items: { status: string; count: number }[] }) {
  return (
    <section className="glass p-5 sm:p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {items.length ? (
        <ul className="mt-4 space-y-3">
          {items.map(({ status, count }) => (
            <li className="flex items-center justify-between gap-4 text-sm" key={status}>
              <span>{status}</span>
              <span className="font-semibold tabular-nums">{count.toLocaleString()}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-[var(--silver-600)]">No active candidates</p>
      )}
    </section>
  );
}

export default function AdminDashboard({
  token,
  onSessionEnd,
}: {
  token: string;
  onSessionEnd: () => void;
}) {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getDashboardSummary(token)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        if (reason instanceof SessionError) {
          onSessionEnd();
          return;
        }
        setError(reason instanceof Error ? reason.message : "Could not load the dashboard");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, onSessionEnd]);

  if (loading) {
    return <div className="glass flex justify-center p-12"><DocLoader label="Loading dashboard" /></div>;
  }
  if (error) {
    return <div className="glass p-6"><p className="form-error" role="alert">{error}</p></div>;
  }
  if (!data) return null;

  return (
    <section className="space-y-6">
      <header>
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--silver-600)]">Admin overview</p>
        <h1 className="mt-2 text-3xl font-bold">Recruiting dashboard</h1>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Active candidates" value={data.totals.active_candidates} note="Not archived or merged" />
        <Metric label="Open job roles" value={data.totals.open_jobs} note="Currently marked Open" />
        <Metric label="Resumes parsed this month" value={data.totals.parsed_this_month} note="Successful inbox processing" />
        <Metric label="Awaiting processing" value={data.totals.awaiting_processing} note="Received or currently processing" />
        <Metric label="Needs review" value={data.totals.needs_review} note="Parser or intake needs attention" />
      </div>
      <MonthlyCharts months={data.months} />
      <div className="grid gap-6 xl:grid-cols-2">
        <CandidateBreakdown title="Candidates by status" items={data.candidate_statuses} />
        <CandidateBreakdown title="Candidates by resume parse status" items={data.candidate_parse_statuses} />
      </div>
      <p className="text-xs text-[var(--silver-600)]">
        Resume counts include successfully parsed email and drag-and-drop inbox submissions; duplicates,
        failures, and items needing review are excluded.
      </p>
      <p className="text-xs text-[var(--silver-600)]">{data.candidate_count_definition}</p>
    </section>
  );
}
