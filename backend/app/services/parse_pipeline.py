import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.candidates import (Candidate, CandidateDocument, CandidateExperience,
                                   CandidateSkill, Skill)
from app.models.system import ActivityLog
from app.services.experience_extract import extract_experiences
from app.services.experience_years import years_from
from app.services.field_extract import extract_fields
from app.services.skill_match import find_skills, load_terms
from app.services.text_extract import ExtractionError, extract_text

log = logging.getLogger("aks_ats.parse")


def _to_date(v):
    if not v:
        return None
    parts = v.split("-")
    return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, 1)


def _precision(v):
    if not v:
        return None
    return "month" if len(v) == 7 else "year"


def parse_document(db: Session, doc_id: int, user_id: int | None = None) -> dict:
    doc = db.get(CandidateDocument, doc_id)
    if not doc:
        raise ValueError("Document not found")
    cand = db.get(Candidate, doc.candidate_id)
    path = (settings.storage_dir / doc.storage_path)

    try:
        text = extract_text(Path(path))
    except ExtractionError as exc:
        cand.parse_status = "Needs Review"
        db.add(ActivityLog(user_id=user_id, action="resume.parse_failed", object_type="candidate",
                           object_id=cand.id, new_value={"document_id": doc.id, "reason": str(exc)}))
        db.commit()
        return {"status": "Needs Review", "reason": str(exc)}

    fields = extract_fields(text)
    sources = dict(cand.field_sources or {})
    filled = []
    for k, v in fields.items():
        if v and not getattr(cand, k):
            setattr(cand, k, v)
            sources[k] = "extracted"
            filled.append(k)

    exps = extract_experiences(text)
    db.execute(delete(CandidateExperience).where(CandidateExperience.candidate_id == cand.id))
    for e in exps:
        db.add(CandidateExperience(
            candidate_id=cand.id, company=e["company"], title=e["title"],
            start_date=_to_date(e["start"]), end_date=_to_date(e["end"]),
            start_precision=_precision(e["start"]), end_precision=_precision(e["end"]),
            is_current=e["is_current"]))

    exp_years = years_from([{"start": _to_date(e["start"]), "end": _to_date(e["end"]),
                             "is_current": e["is_current"]} for e in exps])
    if exp_years is not None and (cand.total_experience_years is None
                                  or sources.get("total_experience_years") == "inferred"):
        cand.total_experience_years = Decimal(str(exp_years))
        sources["total_experience_years"] = "inferred"

    terms = load_terms(db)
    found = find_skills(text, terms)
    db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == cand.id,
                                            CandidateSkill.source == "extracted"))
    db.flush()
    existing = {s for (s,) in db.execute(select(CandidateSkill.skill_id)
                                         .where(CandidateSkill.candidate_id == cand.id)).all()}
    for f in found:
        sk = db.scalar(select(Skill).where(Skill.name == f["skill"]))
        if sk and sk.id not in existing:
            db.add(CandidateSkill(candidate_id=cand.id, skill_id=sk.id,
                                  evidence=f["evidence"], source="extracted"))

    cand.field_sources = sources
    missing = [k for k in ("full_name", "email", "phone") if not getattr(cand, k)]
    cand.parse_status = "Needs Review" if missing else "Parsed"
    db.add(ActivityLog(user_id=user_id, action="resume.parsed", object_type="candidate",
                       object_id=cand.id,
                       new_value={"document_id": doc.id, "fields_filled": filled,
                                  "experiences": len(exps), "skills": len(found),
                                  "missing": missing}))
    db.commit()
    return {"status": cand.parse_status, "fields_filled": filled, "experiences": len(exps),
            "skills": len(found), "missing": missing}