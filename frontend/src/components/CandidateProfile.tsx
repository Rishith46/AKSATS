"use client";

import { useEffect, useState } from "react";
import CandidateNotes from "@/components/CandidateNotes";
import CandidateEditForm from "@/components/CandidateEditForm";
import CandidateSupportingDocuments from "@/components/CandidateSupportingDocuments";
import DocLoader from "@/components/DocLoader";
import {
  getATSResumeExport, getCandidateDocument, getProfile, reparseResume, SessionError, type Profile,
} from "@/lib/api";
import { useVisa } from "@/lib/visa";

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
  token, id, canEdit, canUploadDocuments, startEditing = false, onBack, onSessionEnd,
}: {
  token: string;
  id: number;
  canEdit: boolean;
  canUploadDocuments: boolean;
  startEditing?: boolean;
  onBack: () => void;
  onSessionEnd: () => void;
}) {
  const [p, setP] = useState<Profile | null>(null);
  const { label: visaLabel } = useVisa(token);
  const [editing, setEditing] = useState(startEditing);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [parsingDocument, setParsingDocument] = useState<number | null>(null);
  const [parseMessage, setParseMessage] = useState<string | null>(null);
  const [resumeBusy, setResumeBusy] = useState<string | null>(null);
  const [resumeMessage, setResumeMessage] = useState<string | null>(null);
  const [pdfPreview, setPdfPreview] = useState<{ filename: string; url: string } | null>(null);

  useEffect(() => {
    const url = pdfPreview?.url;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [pdfPreview?.url]);

  function updateSupportingDocument(document: Profile["documents"][number]) {
    setP((current) => current ? {
      ...current,
      documents: [
        ...current.documents.filter((item) => item.slot !== document.slot),
        document,
      ],
    } : current);
  }

  function removeSupportingDocument(documentId: number) {
    setP((current) => current ? {
      ...current,
      documents: current.documents.filter((document) => document.id !== documentId),
    } : current);
  }

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

  async function reparse(documentId: number) {
    setParsingDocument(documentId);
    setParseMessage(null);
    try {
      const result = await reparseResume(token, id, documentId);
      setParseMessage(
        result.status !== "Parsed"
          ? `Parsing needs review: ${result.reason ?? (result.missing?.length ? `Missing ${result.missing.join(", ")}.` : result.status)}`
          : `Resume parsed: ${result.fields_filled?.length ?? 0} fields, ${result.experiences ?? 0} jobs, ` +
            `${result.education ?? 0} education records, ${result.certifications ?? 0} certifications, ` +
            `${result.skills ?? 0} skills.`
      );
      setLoading(true);
      setReloadKey((key) => key + 1);
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setParseMessage(err instanceof Error ? err.message : "Could not parse this resume");
    } finally {
      setParsingDocument(null);
    }
  }

  function saveBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function exportATSResume(format: "docx" | "pdf") {
    setResumeBusy(`export-${format}`);
    setResumeMessage(null);
    try {
      const blob = await getATSResumeExport(token, id, format);
      const extension = format === "docx" ? "docx" : "pdf";
      const name = (p?.full_name ?? "candidate").replace(/[^A-Za-z0-9._-]+/g, "-");
      saveBlob(blob, `${name || "candidate"}-ats-resume.${extension}`);
      setResumeMessage("Exported the ATS-managed resume. The original upload was not changed.");
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setResumeMessage(err instanceof Error ? err.message : "Could not export the ATS resume");
    } finally {
      setResumeBusy(null);
    }
  }

  async function openOriginal(documentId: number, filename: string) {
    setResumeBusy(`document-${documentId}`);
    setResumeMessage(null);
    try {
      const blob = await getCandidateDocument(token, id, documentId);
      if (/\.pdf$/i.test(filename)) {
        setPdfPreview({ filename, url: URL.createObjectURL(blob) });
      } else {
        saveBlob(blob, filename);
      }
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setResumeMessage(err instanceof Error ? err.message : "Could not open the original resume");
    } finally {
      setResumeBusy(null);
    }
  }

  if (editing) {
    return (
      <CandidateEditForm
        token={token}
        id={id}
        onSessionEnd={onSessionEnd}
        onClose={() => {
          setEditing(false);
          setLoading(true);
          setReloadKey((k) => k + 1);
        }}
      />
    );
  }

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
              {canEdit && <button className="btn-dark" onClick={() => setEditing(true)}>Edit candidate</button>}
            </div>
          </div>

          <div className="match-card mt-5">
            <h2 className="font-semibold">ATS-managed resume</h2>
            <p className="mt-1 text-sm text-[var(--silver-600)]">
              Update verified experience, skill evidence, years, and last-used dates with Edit candidate.
              Export creates a separate resume from saved ATS details; it never replaces the uploaded file.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-dark" onClick={() => void exportATSResume("docx")}
                disabled={resumeBusy !== null}>
                {resumeBusy === "export-docx" ? "Preparing..." : "Export ATS resume (.docx)"}
              </button>
              <button className="btn-ghost" onClick={() => void exportATSResume("pdf")}
                disabled={resumeBusy !== null}>
                {resumeBusy === "export-pdf" ? "Preparing..." : "Export ATS resume (.pdf)"}
              </button>
            </div>
            {resumeMessage && <p className="mt-3 text-sm" role="status">{resumeMessage}</p>}
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
            <Field label="Work authorization" value={visaLabel(p.visa_status)} source={p.field_sources.visa_status} />
            <Field label="Rate" value={p.rate} source={p.field_sources.rate} />
            <Field label="Rate unit" value={p.rate_unit} source={p.field_sources.rate_unit} />
            <Field label="Total experience (years)" value={p.total_experience_years} source={p.field_sources.total_experience_years} />
            <Field label="Availability" value={p.availability} source={p.field_sources.availability} />
            <Field label="Country" value={p.country} source={p.field_sources.country} />
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
                    {e.location && <p className="text-xs text-[var(--silver-600)]">{e.location}</p>}
                    <p className="text-xs text-[var(--silver-600)]">
                      {start ?? NM} to {end ?? NM}
                    </p>
                    {e.description && <p className="mt-2 whitespace-pre-wrap text-sm">{e.description}</p>}
                  </li>
                );
              })}
            </ol>
          )}

          <h2 className="section-title">Education</h2>
          {p.education.length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No education details were structured from the resume.</p>
          ) : (
            <ol className="timeline">
              {p.education.map((e, i) => (
                <li key={`${e.institution ?? "education"}-${i}`} className="timeline-item">
                  <p className="font-semibold">{e.degree ?? e.field_of_study ?? NM}</p>
                  {e.field_of_study && e.degree && <p className="text-sm">{e.field_of_study}</p>}
                  <p className="text-sm">{e.institution ?? NM}</p>
                  {(e.start_year || e.end_year) && (
                    <p className="text-xs text-[var(--silver-600)]">
                      {e.start_year ?? ""}{e.start_year && e.end_year ? " to " : ""}{e.end_year ?? ""}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}

          <h2 className="section-title">Certifications</h2>
          {p.certifications.length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No certifications were structured from the resume.</p>
          ) : (
            <ul className="space-y-2">
              {p.certifications.map((cert, i) => (
                <li key={`${cert.name}-${i}`} className="match-card">
                  <p className="font-semibold">{cert.name}</p>
                  <p className="text-sm text-[var(--silver-600)]">
                    {[cert.issuer, cert.year].filter(Boolean).join(" · ") || NM}
                  </p>
                </li>
              ))}
            </ul>
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

          <h2 className="section-title">DL, Visa &amp; other documents</h2>
          <CandidateSupportingDocuments
            token={token}
            candidateId={p.id}
            documents={p.documents}
            canUpload={canUploadDocuments}
            onUpload={updateSupportingDocument}
            onRemove={removeSupportingDocument}
            onOpen={(documentId, filename) => void openOriginal(documentId, filename)}
            onSessionEnd={onSessionEnd}
          />

          <h2 className="section-title">Resume and other documents</h2>
          {parseMessage && <p className="mb-3 text-sm" role="status">{parseMessage}</p>}
          {p.documents.filter((document) => !document.slot).length === 0 ? (
            <p className="text-sm text-[var(--silver-600)]">No documents.</p>
          ) : (
            <div className="table-wrap">
              <table className="list">
                <thead><tr><th>File</th><th>Type</th><th>Version</th><th>Uploaded</th></tr></thead>
                <tbody>
                  {p.documents.filter((document) => !document.slot).map((d) => (
                    <tr key={d.id}>
                      <td className="font-semibold">
                        {d.filename}
                        {d.kind === "resume" && (
                          <button
                            className="btn-ghost ml-2"
                            onClick={() => void openOriginal(d.id, d.filename)}
                            disabled={resumeBusy !== null}
                          >
                            {resumeBusy === `document-${d.id}`
                              ? "Opening..."
                              : /\.pdf$/i.test(d.filename) ? "Preview original" : "Download original"}
                          </button>
                        )}
                        {d.extracted_text && (
                          <details className="mt-2 max-w-xl">
                            <summary className="cursor-pointer text-xs font-normal text-[var(--silver-600)]">
                              View all extracted text
                            </summary>
                            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-[var(--silver-100)] p-3 text-xs font-normal">
                              {d.extracted_text}
                            </pre>
                          </details>
                        )}
                      </td>
                      <td>{d.kind}</td>
                      <td>
                        {d.version_no ? `v${d.version_no}` : NM}
                        {d.is_current && <span className="badge ml-2">Current</span>}
                        {canEdit && d.kind === "resume" && (
                          <button
                            className="btn-ghost ml-2"
                            disabled={parsingDocument === d.id}
                            onClick={() => void reparse(d.id)}
                          >
                            {parsingDocument === d.id ? "Parsing..." : "Parse again"}
                          </button>
                        )}
                      </td>
                      <td className="whitespace-nowrap">{fmtDay(d.uploaded_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {pdfPreview && (
            <div className="match-card mt-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold">PDF preview: {pdfPreview.filename}</h3>
                <button className="btn-ghost" onClick={() => setPdfPreview(null)}>Close preview</button>
              </div>
              <iframe className="mt-3 h-[75vh] w-full rounded-lg border border-[var(--silver-200)]"
                src={pdfPreview.url} title={`Original resume ${pdfPreview.filename}`} />
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}