import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, require_permission
from app.models.access import User
from app.models.system import ActivityLog, ResumeIngestion

log = logging.getLogger("aks_ats.inbox")

router = APIRouter(prefix="/inbox", tags=["inbox"])

MAX_BYTES = 20 * 1024 * 1024
MAX_FILES = 50
ALLOWED = {"pdf", "doc", "docx"}


@router.post("/upload", status_code=201)
def upload(files: list[UploadFile] = File(...), db: Session = Depends(get_db),
           user: User = Depends(require_permission("document.upload"))):
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"At most {MAX_FILES} files per upload")

    saved = []
    rows = []
    try:
        for f in files:
            name = os.path.basename(f.filename or "")[:500] or "unnamed"
            ext = Path(name).suffix.lower().lstrip(".")
            data = f.file.read(MAX_BYTES + 1)
            problem = None
            if ext not in ALLOWED:
                problem = "Unsupported file type"
            elif not data:
                problem = "File is empty"
            elif len(data) > MAX_BYTES:
                problem = "File is larger than 20 MB"

            row = ResumeIngestion(source="upload", original_filename=name)
            if problem:
                row.status = "Failed"
                row.issues = {"reason": problem}
            else:
                rel = f"inbox/{uuid.uuid4().hex}.{ext}"
                full = settings.storage_dir / rel
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_bytes(data)
                saved.append(full)
                row.status = "Received"
                row.staged_path = rel
            db.add(row)
            rows.append(row)

        db.flush()
        ok = sum(1 for r in rows if r.status == "Received")
        db.add(ActivityLog(user_id=user.id, action="inbox.received", object_type="inbox",
                           new_value={"received": ok, "failed": len(rows) - ok}))
        db.commit()
    except Exception:
        db.rollback()
        for p in saved:
            p.unlink(missing_ok=True)
        log.exception("Inbox upload failed")
        raise

    items = [{"id": r.id, "filename": r.original_filename, "status": r.status,
              "issues": r.issues} for r in rows]
    return {"received": sum(1 for i in items if i["status"] == "Received"),
            "failed": sum(1 for i in items if i["status"] == "Failed"),
            "items": items}


@router.get("")
def list_inbox(limit: int = 100, db: Session = Depends(get_db),
               user: User = Depends(require_permission("candidate.view"))):
    counts = dict(db.execute(
        select(ResumeIngestion.status, func.count()).group_by(ResumeIngestion.status)).all())
    q = select(ResumeIngestion).order_by(ResumeIngestion.id.desc()).limit(min(limit, 200))
    rows = db.scalars(q).all()
    return {
        "total": sum(counts.values()),
        "by_status": counts,
        "items": [{
            "id": r.id, "filename": r.original_filename, "status": r.status,
            "issues": r.issues, "candidate_id": r.candidate_id,
            "received_at": r.received_at, "processed_at": r.processed_at,
        } for r in rows],
    }