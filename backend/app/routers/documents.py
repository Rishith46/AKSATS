import hashlib
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate, CandidateDocument
from app.models.system import ActivityLog
from app.schemas.documents import DocumentOut

log = logging.getLogger("aks_ats.documents")

router = APIRouter(prefix="/candidates/{cid}/documents", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024
KINDS = {"resume", "certification", "work_authorization", "interview_notes", "other"}
RESUME_EXT = {"pdf", "doc", "docx"}
ALLOWED_EXT = RESUME_EXT | {"txt", "png", "jpg", "jpeg"}
SUPPORTING_DOCUMENT_SLOTS = {
    "drivers_license": "Driver's License",
    "visa": "Visa",
    "other_1": "Other Document 1",
    "other_2": "Other Document 2",
    "other_3": "Other Document 3",
}
NAMED_DOCUMENT_SLOTS = {"other_1", "other_2", "other_3"}


def _safe_storage_path(relative_path: str) -> Path | None:
    base = settings.storage_dir.resolve()
    path = (base / relative_path).resolve()
    if base not in path.parents:
        return None
    return path


def _candidate(db: Session, cid: int) -> Candidate:
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(cid: int, file: UploadFile = File(...), kind: str = Form("resume"),
                    db: Session = Depends(get_db),
                    user: User = Depends(require_permission("document.upload"))):
    _candidate(db, cid)
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of: {', '.join(sorted(KINDS))}")

    name = os.path.basename(file.filename or "")[:500]
    ext = Path(name).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if kind == "resume" and ext not in RESUME_EXT:
        raise HTTPException(status_code=400, detail="Resumes must be pdf, doc or docx")

    data = file.file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 20 MB")

    digest = hashlib.sha256(data).hexdigest()
    dup = db.scalar(select(CandidateDocument.id).where(
        CandidateDocument.candidate_id == cid,
        CandidateDocument.kind == kind,
        CandidateDocument.sha256 == digest))
    if dup:
        raise HTTPException(status_code=409, detail=f"Identical file already uploaded (document {dup})")

    version = None
    is_current = False
    if kind == "resume":
        last = db.scalar(select(func.max(CandidateDocument.version_no)).where(
            CandidateDocument.candidate_id == cid, CandidateDocument.kind == "resume"))
        version = (last or 0) + 1
        is_current = True
        db.execute(update(CandidateDocument).where(
            CandidateDocument.candidate_id == cid,
            CandidateDocument.kind == "resume",
            CandidateDocument.is_current.is_(True)).values(is_current=False))

    rel = f"candidates/{cid}/{uuid.uuid4().hex}.{ext}"
    full = settings.storage_dir / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    try:
        doc = CandidateDocument(
            candidate_id=cid, kind=kind, original_filename=name or "unnamed",
            storage_path=rel, mime_type=file.content_type, size_bytes=len(data),
            sha256=digest, version_no=version, is_current=is_current, uploaded_by=user.id)
        db.add(doc)
        db.flush()
        db.add(ActivityLog(user_id=user.id, action="document.uploaded", object_type="candidate",
                           object_id=cid,
                           new_value={"document_id": doc.id, "kind": kind,
                                      "version_no": version, "filename": name}))
        db.commit()
    except Exception:
        db.rollback()
        full.unlink(missing_ok=True)
        log.exception("Document upload failed for candidate %s", cid)
        raise
    db.refresh(doc)
    return doc


@router.post("/slots", response_model=DocumentOut)
def upload_supporting_document(
    cid: int,
    file: UploadFile = File(...),
    slot: str = Form(...),
    display_name: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("document.upload")),
):
    _candidate(db, cid)
    if slot not in SUPPORTING_DOCUMENT_SLOTS:
        raise HTTPException(
            status_code=400,
            detail=f"slot must be one of: {', '.join(SUPPORTING_DOCUMENT_SLOTS)}",
        )

    custom_name = (display_name or "").strip()
    if slot in NAMED_DOCUMENT_SLOTS:
        if not custom_name:
            raise HTTPException(status_code=422, detail="A name is required for this document")
        if len(custom_name) > 100:
            raise HTTPException(status_code=422, detail="Document name must be at most 100 characters")
    else:
        custom_name = SUPPORTING_DOCUMENT_SLOTS[slot]

    name = os.path.basename(file.filename or "")[:500]
    if Path(name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Supporting documents must be PDF files")
    data = file.file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 20 MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")

    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(CandidateDocument).where(
        CandidateDocument.candidate_id == cid,
        CandidateDocument.slot == slot,
    ))
    duplicate = db.scalar(select(CandidateDocument.id).where(
        CandidateDocument.candidate_id == cid,
        CandidateDocument.sha256 == digest,
        CandidateDocument.id != (existing.id if existing else -1),
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail=f"Identical file already uploaded (document {duplicate})")

    rel = f"candidates/{cid}/{uuid.uuid4().hex}.pdf"
    full = settings.storage_dir / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    previous_path = _safe_storage_path(existing.storage_path) if existing else None
    try:
        if existing:
            existing.original_filename = name or "document.pdf"
            existing.storage_path = rel
            existing.mime_type = "application/pdf"
            existing.size_bytes = len(data)
            existing.sha256 = digest
            existing.uploaded_by = user.id
            existing.display_name = custom_name
            doc = existing
            action = "document.replaced"
        else:
            doc = CandidateDocument(
                candidate_id=cid,
                kind="supporting_document",
                slot=slot,
                display_name=custom_name,
                original_filename=name or "document.pdf",
                storage_path=rel,
                mime_type="application/pdf",
                size_bytes=len(data),
                sha256=digest,
                version_no=None,
                is_current=False,
                uploaded_by=user.id,
            )
            db.add(doc)
            action = "document.uploaded"
        db.flush()
        db.add(ActivityLog(
            user_id=user.id,
            action=action,
            object_type="candidate",
            object_id=cid,
            new_value={"document_id": doc.id, "slot": slot, "display_name": custom_name},
        ))
        db.commit()
    except Exception:
        db.rollback()
        full.unlink(missing_ok=True)
        log.exception("Supporting document upload failed for candidate %s, slot %s", cid, slot)
        raise

    if previous_path and previous_path != full:
        try:
            previous_path.unlink(missing_ok=True)
        except OSError:
            log.exception("Could not remove replaced supporting document %s", previous_path)
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_supporting_document(
    cid: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("document.upload")),
):
    _candidate(db, cid)
    doc = db.get(CandidateDocument, doc_id)
    if not doc or doc.candidate_id != cid or doc.slot not in SUPPORTING_DOCUMENT_SLOTS:
        raise HTTPException(status_code=404, detail="Supporting document not found")
    relative_path = doc.storage_path
    db.add(ActivityLog(
        user_id=user.id,
        action="document.deleted",
        object_type="candidate",
        object_id=cid,
        old_value={"document_id": doc.id, "slot": doc.slot, "display_name": doc.display_name},
    ))
    db.delete(doc)
    db.commit()
    path = _safe_storage_path(relative_path)
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            log.exception("Could not remove supporting document %s", path)
    return None


@router.get("", response_model=list[DocumentOut])
def list_documents(cid: int, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("candidate.view"))):
    _candidate(db, cid)
    q = select(CandidateDocument).where(CandidateDocument.candidate_id == cid) \
        .order_by(CandidateDocument.id.desc())
    return db.scalars(q).all()


@router.get("/{doc_id}/download")
def download_document(cid: int, doc_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("candidate.view"))):
    _candidate(db, cid)
    doc = db.get(CandidateDocument, doc_id)
    if not doc or doc.candidate_id != cid:
        raise HTTPException(status_code=404, detail="Document not found")
    base = settings.storage_dir.resolve()
    path = (base / doc.storage_path).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=doc.mime_type or "application/octet-stream",
                        filename=doc.original_filename)