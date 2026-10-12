import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate, CandidateDocument
from app.services.parse_pipeline import parse_document

log = logging.getLogger("aks_ats.parse_api")

router = APIRouter(prefix="/candidates/{cid}/documents/{doc_id}", tags=["parsing"])


@router.post("/parse")
def parse(cid: int, doc_id: int, db: Session = Depends(get_db),
          user: User = Depends(require_permission("candidate.edit"))):
    if not db.get(Candidate, cid):
        raise HTTPException(status_code=404, detail="Candidate not found")
    doc = db.get(CandidateDocument, doc_id)
    if not doc or doc.candidate_id != cid:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.kind != "resume":
        raise HTTPException(status_code=400, detail="Only resume documents can be parsed")
    try:
        return parse_document(db, doc_id, user_id=user.id)
    except Exception:
        db.rollback()
        log.exception("Parsing failed for document %s", doc_id)
        raise HTTPException(status_code=500, detail="Parsing failed; see server log")