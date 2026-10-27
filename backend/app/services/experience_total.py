from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidates import Candidate, CandidateExperience
from app.services.experience_years import years_from


def recalc_total(db: Session, cand: Candidate) -> None:
    """Recalculates total experience from the jobs, unless a person set it by hand.
    A value with no label, or labeled confirmed, is treated as set by a person and left alone."""
    sources = dict(cand.field_sources or {})
    if cand.total_experience_years is not None and sources.get("total_experience_years") != "inferred":
        return
    rows = db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == cand.id)).all()
    yrs = years_from([{"start": r.start_date, "end": r.end_date, "is_current": r.is_current} for r in rows])
    if yrs is None:
        cand.total_experience_years = None
        sources.pop("total_experience_years", None)
    else:
        cand.total_experience_years = Decimal(str(yrs))
        sources["total_experience_years"] = "inferred"
    cand.field_sources = sources