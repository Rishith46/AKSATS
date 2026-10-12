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