import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate, CandidateDocument, CandidateNote
from app.models.jobs import Client, Job, Submission
from app.models.system import ActivityLog

log = logging.getLogger("aks_ats.delete")

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.delete("/{cid}")
def delete_candidate(cid: int, confirm_name: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("candidate.delete"))):
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    expected = c.full_name or "DELETE"
    if confirm_name != expected:
        raise HTTPException(status_code=400,
                            detail="Confirmation does not match. Nothing was deleted.")

    subs = db.execute(
        select(Submission, Job.title, Client.name)
        .join(Job, Job.id == Submission.job_id)
        .outerjoin(Client, Client.id == Job.client_id)
        .where(Submission.candidate_id == cid)
    ).all()
    submissions = [{
        "job": title, "client": client, "status": s.status,
        "rate": str(s.rate) if s.rate is not None else None,
        "submitted_at": str(s.submitted_at),
    } for s, title, client in subs]

    docs = db.scalars(select(CandidateDocument).where(CandidateDocument.candidate_id == cid)).all()
    documents = [{
        "filename": d.original_filename, "kind": d.kind, "version_no": d.version_no,
        "sha256": d.sha256,
    } for d in docs]
    paths = [d.storage_path for d in docs]
    note_count = len(db.scalars(select(CandidateNote.id).where(CandidateNote.candidate_id == cid)).all())

    tombstone = {
        "full_name": c.full_name, "email": c.email, "phone": c.phone,
        "location": c.location, "status": c.status,
        "submissions": submissions, "documents": documents, "note_count": note_count,
    }

    db.add(ActivityLog(user_id=user.id, action="candidate.deleted", object_type="candidate",
                       object_id=cid, old_value=tombstone))
    db.delete(c)
    db.commit()

    base = settings.storage_dir.resolve()
    failed = []
    for rel in paths:
        p = (base / rel).resolve()
        if base not in p.parents:
            failed.append(rel)
            log.warning("Skipped file outside storage: %s", rel)
            continue
        try:
            p.unlink(missing_ok=True)
        except OSError:
            failed.append(rel)
            log.exception("Could not delete file %s", rel)
    try:
        (base / "candidates" / str(cid)).rmdir()
    except OSError:
        pass

    return {"deleted_candidate_id": cid, "documents_removed": len(paths) - len(failed),
            "files_not_removed": failed, "submissions_removed": len(submissions)}