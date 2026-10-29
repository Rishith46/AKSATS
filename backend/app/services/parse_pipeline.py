import logging
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.candidates import (Candidate, CandidateDocument, CandidateExperience,
                                   CandidateCertification, CandidateEducation, CandidateSkill,
                                   Skill, SkillAlias)
from app.models.system import ActivityLog
from app.services.experience_extract import extract_experiences
from app.services.experience_years import years_from
from app.services.field_extract import extract_fields
from app.services.resume_sections import (
    extract_certifications,
    extract_education,
    extract_resume_skills,
)
from app.services.skill_match import find_skills, load_terms
from app.services.skill_history import skill_history
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

    doc.extracted_text = text
    fields = extract_fields(text)
    sources = dict(cand.field_sources or {})
    filled = []
    for k, v in fields.items():
        source = sources.get(k)
        if v and (not getattr(cand, k) or source in {"extracted", "inferred"}):
            if getattr(cand, k) == v:
                continue
            setattr(cand, k, v)
            sources[k] = "extracted"
            filled.append(k)

    experience_error = None
    try:
        exps = extract_experiences(text)
    except Exception as exc:
        log.exception("Could not extract structured experience for document %s", doc.id)
        exps = []
        experience_error = "Work history could not be structured automatically; review the extracted resume text."
    if exps:
        db.execute(delete(CandidateExperience).where(CandidateExperience.candidate_id == cand.id))
        for e in exps:
            db.add(CandidateExperience(
                candidate_id=cand.id, company=e["company"], title=e["title"],
                start_date=_to_date(e["start"]), end_date=_to_date(e["end"]),
                start_precision=_precision(e["start"]), end_precision=_precision(e["end"]),
                is_current=e["is_current"], description=e.get("description")))

    education = extract_education(text)
    if education:
        db.execute(delete(CandidateEducation).where(CandidateEducation.candidate_id == cand.id))
    existing_education = set()
    for row in education:
        key = (row["institution"], row["degree"], row["field_of_study"],
               row["start_year"], row["end_year"])
        if key not in existing_education:
            db.add(CandidateEducation(candidate_id=cand.id, **row))
            existing_education.add(key)

    certifications = extract_certifications(text)
    if certifications:
        db.execute(delete(CandidateCertification).where(
            CandidateCertification.candidate_id == cand.id
        ))
    existing_certifications = set()
    for row in certifications:
        key = (row["name"], row["issuer"], row["year"])
        if key not in existing_certifications:
            db.add(CandidateCertification(candidate_id=cand.id, **row))
            existing_certifications.add(key)

    exp_years = years_from([{"start": _to_date(e["start"]), "end": _to_date(e["end"]),
                             "is_current": e["is_current"]} for e in exps])
    if exp_years is not None and (cand.total_experience_years is None
                                  or sources.get("total_experience_years") == "inferred"):
        cand.total_experience_years = Decimal(str(exp_years))
        sources["total_experience_years"] = "inferred"

    terms = load_terms(db)
    found_by_name = {item["skill"].casefold(): item for item in find_skills(text, terms)}
    for name in extract_resume_skills(text):
        skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.casefold()))
        if skill is None:
            alias = db.scalar(select(SkillAlias).where(func.lower(SkillAlias.alias) == name.casefold()))
            skill = db.get(Skill, alias.skill_id) if alias else None
        if skill is None:
            skill = Skill(name=name, needs_review=True)
            db.add(skill)
            db.flush()
        found_by_name.setdefault(skill.name.casefold(), {
            "skill": skill.name,
            "evidence": name,
        })
    found = list(found_by_name.values())
    hist = skill_history([{"title": e["title"], "description": e.get("description"),
                           "start": _to_date(e["start"]), "end": _to_date(e["end"]),
                           "is_current": e["is_current"]} for e in exps], terms)
    db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == cand.id,
                                            CandidateSkill.source == "extracted"))
    db.flush()
    existing = {s for (s,) in db.execute(select(CandidateSkill.skill_id)
                                         .where(CandidateSkill.candidate_id == cand.id)).all()}
    for f in found:
        sk = db.scalar(select(Skill).where(Skill.name == f["skill"]))
        if sk and sk.id not in existing:
            db.add(CandidateSkill(candidate_id=cand.id, skill_id=sk.id,
                                  evidence=hist.get(f["skill"], {}).get("evidence") or f["evidence"],
                                  years=hist.get(f["skill"], {}).get("years"),
                                  last_used_year=hist.get(f["skill"], {}).get("last_year"),
                                  source="extracted"))

    cand.field_sources = sources
    missing = [k for k in ("full_name", "email", "phone") if not getattr(cand, k)]
    experience_section_found = bool(
        re.search(
            r"^\s*(?:(?:professional|work|career|employment)\s+)?"
            r"(?:experience|history|employment\s+history|career\s+history|work\s+history)\s*:?\s*$",
            text,
            re.I | re.M,
        )
    )
    if experience_section_found and not exps and experience_error is None:
        experience_error = "Work history was found but could not be structured; review the extracted resume text."
    cand.parse_status = "Needs Review" if missing or experience_error else "Parsed"
    db.add(ActivityLog(user_id=user_id, action="resume.parsed", object_type="candidate",
                       object_id=cand.id,
                       new_value={"document_id": doc.id, "fields_filled": filled,
                                  "experiences": len(exps), "skills": len(found),
                                  "education": len(education), "certifications": len(certifications),
                                  "missing": missing, "partial_reason": experience_error}))
    db.commit()
    return {"status": cand.parse_status, "fields_filled": filled, "experiences": len(exps),
            "education": len(education), "certifications": len(certifications),
            "skills": len(found), "missing": missing, "reason": experience_error}