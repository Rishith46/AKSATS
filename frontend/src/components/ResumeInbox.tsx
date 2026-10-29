"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { getInbox, SessionError, uploadResumes, type InboxData, type UploadResult } from "@/lib/api";

const OK_EXT = ["pdf", "doc", "docx"];
const MAX_FILES = 50;
const STATUSES = ["Received", "Processing", "Processed", "Needs Review", "Duplicate", "Failed"];

function extOf(name: string) {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i + 1).toLowerCase();
}

function fmtTime(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "Not Mentioned" : d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function tone(s: string) {
  if (s === "Processed") return "badge";
  if (s === "Needs Review" || s === "Duplicate") return "badge warn";
  if (s === "Failed") return "badge bad";
  return "badge muted";
}

export default function ResumeInbox({ token, onSessionEnd }: { token: string; onSessionEnd: () => void }) {
  const [data, setData] = useState<InboxData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [rejected, setRejected] = useState<string[]>([]);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  const busyRows = (data?.by_status["Received"] ?? 0) + (data?.by_status["Processing"] ?? 0);

  const load = useCallback(async () => {
    try {
      const d = await getInbox(token);
      setData(d);
      setError(null);
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [token, onSessionEnd]);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  useEffect(() => {
    if (busyRows === 0) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [busyRows, load]);

  async function handleFiles(list: FileList | File[]) {
    if (uploading) return;
    const all = Array.from(list);
    const good = all.filter((f) => OK_EXT.includes(extOf(f.name)));
    const bad = all.filter((f) => !OK_EXT.includes(extOf(f.name))).map((f) => f.name);
    setRejected(bad);
    setResult(null);
    setUploadError(null);
    if (good.length === 0) return;
    if (good.length > MAX_FILES) {
      setUploadError(`Choose at most ${MAX_FILES} files at a time (you chose ${good.length}).`);
      return;
    }
    setUploading(true);
    try {
      setResult(await uploadResumes(token, good));
      setReloadKey((k) => k + 1);
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <section className="glass w-full p-6 sm:p-8">
      <p className="text-xs tracking-[0.4em] uppercase text-[var(--silver-600)]">Resume Inbox</p>
      <p className="mt-2 text-sm text-[var(--silver-600)]" role="status">
        {data?.email_polling
          ? "Gmail polling is enabled. Confirmed resume attachments are added and parsed automatically."
          : "Gmail polling is not configured. Configure Google OAuth in the backend to import application resumes automatically."}
      </p>

      <div
        className={"dropzone" + (dragging ? " active" : "")}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => !uploading && input.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && !uploading) input.current?.click(); }}
        aria-label="Upload resumes"
      >
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.doc,.docx"
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        {uploading ? (
          <DocLoader label="Uploading" />
        ) : (
          <>
            <p className="text-lg font-semibold">{dragging ? "Release to upload" : "Drop resumes here"}</p>
            <p className="mt-1 text-sm text-[var(--silver-600)]">or click to choose files. PDF, DOC or DOCX, up to {MAX_FILES} at a time.</p>
          </>
        )}
      </div>

      {uploadError && <p className="form-error mt-3" role="alert">{uploadError}</p>}
      {rejected.length > 0 && (
        <p className="mt-3 text-sm text-[#7a4a05]" role="status">
          Not uploaded (unsupported type): {rejected.join(", ")}
        </p>
      )}
      {result && (
        <div className="result-box" role="status">
          <p className="font-semibold">
            {result.received} received{result.failed > 0 ? `, ${result.failed} failed` : ""}
          </p>
          {result.items.filter((i) => i.status === "Failed").map((i) => (
            <p key={i.id} className="text-sm text-[#b42318]">{i.filename}: {i.issues?.reason ?? "Failed"}</p>
          ))}
        </div>
      )}

      <div className="mt-8">
        {loading ? (
          <div className="py-12 flex justify-center"><DocLoader label="Loading inbox" /></div>
        ) : error ? (
          <div className="empty">
            <p className="form-error" role="alert">{error}</p>
            <button className="btn-dark mt-4" onClick={() => { setLoading(true); setReloadKey((k) => k + 1); }}>Retry</button>
          </div>
        ) : data && data.total === 0 ? (
          <div className="empty">
            <p className="text-lg font-semibold">Inbox is empty</p>
            <p className="mt-1 text-sm text-[var(--silver-600)]">Uploaded resumes appear here with their processing status.</p>
          </div>
        ) : data ? (
          <>
            <div className="status-strip">
              {STATUSES.filter((s) => (data.by_status[s] ?? 0) > 0).map((s) => (
                <span key={s} className={tone(s)}>{s}: {data.by_status[s]}</span>
              ))}
              {busyRows > 0 && <span className="text-xs text-[var(--silver-600)]">Refreshing automatically</span>}
            </div>
            <div className="table-wrap mt-3">
              <table className="list">
                <thead>
                  <tr><th>File</th><th>Source</th><th>Status</th><th>Note</th><th>Received</th></tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr key={r.id}>
                      <td className="font-semibold">{r.filename}</td>
                      <td>{r.source === "email" ? "Email" : "Upload"}</td>
                      <td><span className={tone(r.status)}>{r.status}</span></td>
                      <td className="text-sm text-[var(--silver-600)]">{r.issues?.reason ?? ""}</td>
                      <td className="whitespace-nowrap">{fmtTime(r.received_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}