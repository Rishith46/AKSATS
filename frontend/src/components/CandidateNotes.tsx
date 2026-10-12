"use client";

import { useEffect, useState } from "react";
import DocLoader from "@/components/DocLoader";
import { addNote, listNotes, SessionError, type Note } from "@/lib/api";

function fmtTime(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? "Not Mentioned"
    : d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function CandidateNotes({
  token, id, onSessionEnd,
}: { token: string; id: number; onSessionEnd: () => void }) {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listNotes(token, id);
        if (cancelled) return;
        setNotes(data);
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

  async function save() {
    const body = text.trim();
    if (!body || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const n = await addNote(token, id, body);
      setNotes((prev) => [n, ...(prev ?? [])]);
      setText("");
    } catch (err) {
      if (err instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setSaveError(err instanceof Error ? err.message : "Could not save the note");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="note-box">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write a note about this candidate"
          maxLength={10000}
          rows={3}
          aria-label="New note"
        />
        <div className="note-actions">
          <span className="text-xs text-[var(--silver-600)]">{text.length} / 10000</span>
          <button className="btn-dark" onClick={save} disabled={!text.trim() || saving}>
            {saving ? "Saving..." : "Add note"}
          </button>
        </div>
        <p className="form-error" role="alert" aria-live="polite">{saveError ?? "\u00A0"}</p>
      </div>

      {loading ? (
        <div className="py-8 flex justify-center"><DocLoader label="Loading notes" /></div>
      ) : error ? (
        <div className="empty">
          <p className="form-error" role="alert">{error}</p>
          <button className="btn-dark mt-4" onClick={() => { setLoading(true); setError(null); setReloadKey((k) => k + 1); }}>Retry</button>
        </div>
      ) : notes && notes.length === 0 ? (
        <p className="text-sm text-[var(--silver-600)]">No notes yet.</p>
      ) : (
        <ul className="note-list">
          {notes?.map((n) => (
            <li key={n.id} className="note-item">
              <p className="note-body">{n.body}</p>
              <p className="note-meta">{n.author_id ? `User ${n.author_id}` : "Unknown user"} &middot; {fmtTime(n.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}