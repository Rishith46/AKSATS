from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import (Candidate, CandidateDocument, CandidateExperience,
                                   CandidateSkill, Skill)

router = APIRouter(prefix="/candidates", tags=["profile"])


@router.get("/{cid}/profile")
def get_profile(cid: int, db: Session = Depends(get_db),
                user: User = Depends(require_permission("candidate.view"))):
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    exps = db.scalars(select(CandidateExperience)
                      .where(CandidateExperience.candidate_id == cid)
                      .order_by(CandidateExperience.start_date.desc().nulls_last(),
                                CandidateExperience.id.desc())).all()
    skills = db.execute(
        select(Skill.name, CandidateSkill.evidence, CandidateSkill.source)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == cid).order_by(Skill.name)).all()
    docs = db.scalars(select(CandidateDocument)
                      .where(CandidateDocument.candidate_id == cid)
                      .order_by(CandidateDocument.id.desc())).all()

    return {
        "id": c.id,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "linkedin_url": c.linkedin_url,
        "location": c.location,
        "visa_status": c.visa_status,
        "rate": str(c.rate) if c.rate is not None else None,
        "total_experience_years": str(c.total_experience_years) if c.total_experience_years is not None else None,
        "status": c.status,
        "parse_status": c.parse_status,
        "field_sources": c.field_sources or {},
        "archived_at": c.archived_at,
        "created_at": c.created_at,
        "experiences": [{
            "id": e.id, "company": e.company, "title": e.title,
            "start_date": e.start_date, "start_precision": e.start_precision,
            "end_date": e.end_date, "end_precision": e.end_precision,
            "is_current": e.is_current,
        } for e in exps],
        "skills": [{"name": n, "evidence": ev, "source": src} for n, ev, src in skills],
        "documents": [{
            "id": d.id, "kind": d.kind, "filename": d.original_filename,
            "version_no": d.version_no, "is_current": d.is_current,
            "uploaded_at": d.uploaded_at,
        } for d in docs],
    }