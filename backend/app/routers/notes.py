from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate, CandidateNote
from app.models.system import ActivityLog
from app.schemas.notes import NoteCreate, NoteOut

router = APIRouter(prefix="/candidates/{cid}/notes", tags=["notes"])


def _candidate(db: Session, cid: int) -> Candidate:
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


@router.post("", response_model=NoteOut, status_code=201)
def add_note(cid: int, body: NoteCreate, db: Session = Depends(get_db),
             user: User = Depends(require_permission("note.add"))):
    _candidate(db, cid)
    note = CandidateNote(candidate_id=cid, author_id=user.id, body=body.body.strip())
    db.add(note)
    db.flush()
    db.add(ActivityLog(user_id=user.id, action="note.added", object_type="candidate",
                       object_id=cid, new_value={"note_id": note.id}))
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteOut])
def list_notes(cid: int, db: Session = Depends(get_db),
               user: User = Depends(require_permission("candidate.view"))):
    _candidate(db, cid)
    q = select(CandidateNote).where(CandidateNote.candidate_id == cid).order_by(CandidateNote.id.desc())
    return db.scalars(q).all()