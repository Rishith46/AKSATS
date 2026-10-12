from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Candidate, CandidateExperience
from app.services.experience_years import years_from


def main() -> None:
    with SessionLocal() as db:
        for c in db.scalars(select(Candidate).order_by(Candidate.id)).all():
            sources = dict(c.field_sources or {})
            if c.total_experience_years is not None and sources.get("total_experience_years") != "inferred":
                print(f"Candidate {c.id}: skipped (value was set by a person)")
                continue
            exps = db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == c.id)).all()
            yrs = years_from([{"start": e.start_date, "end": e.end_date, "is_current": e.is_current} for e in exps])
            if yrs is None:
                print(f"Candidate {c.id}: no usable dates, left empty")
                continue
            c.total_experience_years = Decimal(str(yrs))
            sources["total_experience_years"] = "inferred"
            c.field_sources = sources
            print(f"Candidate {c.id}: {yrs} years (inferred)")
        db.commit()


if __name__ == "__main__":
    main()