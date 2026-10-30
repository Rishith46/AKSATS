"use client";

import { useState } from "react";
import {
  deleteSupportingDocument, SessionError, type Profile, type SupportingDocumentSlot,
  uploadSupportingDocument,
} from "@/lib/api";

const SLOTS: { id: SupportingDocumentSlot; label: string; needsName: boolean }[] = [
  { id: "drivers_license", label: "Driver's License (DL)", needsName: false },
  { id: "visa", label: "Visa", needsName: false },
  { id: "other_1", label: "Other document 1", needsName: true },
  { id: "other_2", label: "Other document 2", needsName: true },
  { id: "other_3", label: "Other document 3", needsName: true },
];

type SupportingDocument = Profile["documents"][number];

export default function CandidateSupportingDocuments({
  token,
  candidateId,
  documents,
  canUpload,
  onUpload,
  onRemove,
  onOpen,
  onSessionEnd,
}: {
  token: string;
  candidateId: number;
  documents: SupportingDocument[];
  canUpload: boolean;
  onUpload: (document: SupportingDocument) => void;
  onRemove: (documentId: number) => void;
  onOpen: (documentId: number, filename: string) => void;
  onSessionEnd: () => void;
}) {
  const [names, setNames] = useState<Record<string, string>>(() =>
    Object.fromEntries(documents.filter((document) => document.slot)
      .map((document) => [document.slot!, document.display_name ?? ""]))
  );
  const [busySlot, setBusySlot] = useState<SupportingDocumentSlot | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function upload(slot: typeof SLOTS[number], file: File | undefined) {
    if (!file) return;
    if (slot.needsName && !names[slot.id]?.trim()) {
      setMessage(`Enter a name for ${slot.label.toLowerCase()} before uploading.`);
      return;
    }
    if (!/\.pdf$/i.test(file.name)) {
      setMessage("Supporting documents must be PDF files.");
      return;
    }

    setBusySlot(slot.id);
    setMessage(null);
    try {
      const document = await uploadSupportingDocument(
        token,
        candidateId,
        slot.id,
        file,
        slot.needsName ? names[slot.id].trim() : undefined,
      );
      onUpload(document);
      setMessage(`${slot.label} PDF saved.`);
    } catch (error) {
      if (error instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not upload this PDF.");
    } finally {
      setBusySlot(null);
    }
  }

  async function remove(document: SupportingDocument, label: string) {
    if (!window.confirm(`Remove ${document.display_name ?? label}?`)) return;
    setBusySlot(document.slot as SupportingDocumentSlot);
    setMessage(null);
    try {
      await deleteSupportingDocument(token, candidateId, document.id);
      onRemove(document.id);
      setMessage(`${document.display_name ?? label} removed.`);
    } catch (error) {
      if (error instanceof SessionError) {
        onSessionEnd();
        return;
      }
      setMessage(error instanceof Error ? error.message : "Could not remove this document.");
    } finally {
      setBusySlot(null);
    }
  }

  return (
    <div>
      <p className="mb-4 text-sm text-[var(--silver-600)]">
        Upload up to five supporting PDFs: one DL, one Visa, and three documents named by the recruiter.
        Each slot can contain one PDF and may be replaced later.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {SLOTS.map((slot) => {
          const document = documents.find((item) => item.slot === slot.id);
          const name = names[slot.id] ?? document?.display_name ?? "";
          const busy = busySlot === slot.id;
          return (
            <article className="supporting-document-card" key={slot.id}>
              <h3 className="font-semibold">{slot.needsName ? (name || slot.label) : slot.label}</h3>
              {slot.needsName && (
                <label className="field mt-3">
                  <span>Recruiter-provided document name</span>
                  <input
                    value={name}
                    maxLength={100}
                    placeholder="e.g. Background check"
                    disabled={!canUpload || busy}
                    onChange={(event) => setNames((current) => ({ ...current, [slot.id]: event.target.value }))}
                  />
                </label>
              )}
              {document ? (
                <div className="mt-3">
                  <p className="break-all text-sm">{document.filename}</p>
                  <p className="mt-1 text-xs text-[var(--silver-600)]">
                    Uploaded {new Date(document.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-[var(--silver-600)]">No PDF uploaded</p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {document && (
                  <>
                    <button className="btn-ghost" disabled={busy}
                      onClick={() => onOpen(document.id, document.filename)}>Preview PDF</button>
                    {canUpload && (
                      <button className="btn-ghost" disabled={busy}
                        onClick={() => void remove(document, slot.label)}>Remove</button>
                    )}
                  </>
                )}
                {canUpload && (
                  <label className="btn-ghost cursor-pointer">
                    {busy ? "Uploading..." : document ? "Replace PDF" : "Upload PDF"}
                    <input
                      className="sr-only"
                      type="file"
                      accept="application/pdf,.pdf"
                      disabled={busy || (slot.needsName && !name.trim())}
                      onChange={(event) => {
                        const file = event.currentTarget.files?.[0];
                        event.currentTarget.value = "";
                        void upload(slot, file);
                      }}
                    />
                  </label>
                )}
              </div>
            </article>
          );
        })}
      </div>
      {message && <p className="mt-3 text-sm" role="status">{message}</p>}
    </div>
  );
}
