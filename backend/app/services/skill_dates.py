from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidates import CandidateExperience, CandidateSkill, Skill
from app.services.skill_history import skill_history
from app.services.skill_match import load_terms


def refresh_skill_dates(db: Session, cand_id: int) -> None:
    """Recomputes years and last-used year for the EXTRACTED skills from the candidate's current jobs.
    Skills a person added or confirmed are never touched. An extracted skill that no dated job
    mentions any more keeps no dates and is treated as listed only."""
    rows = db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == cand_id)).all()
    roles = [{"title": r.title, "description": r.description, "start": r.start_date,
              "end": r.end_date, "is_current": r.is_current} for r in rows]
    hist = skill_history(roles, load_terms(db))
    for cs, name in db.execute(select(CandidateSkill, Skill.name)
                               .join(Skill, Skill.id == CandidateSkill.skill_id)
                               .where(CandidateSkill.candidate_id == cand_id,
                                      CandidateSkill.source == "extracted")).all():
        h = hist.get(name)
        if h:
            cs.years, cs.last_used_year = h["years"], h["last_year"]
            cs.evidence = h["evidence"] or cs.evidence
        else:
            cs.years, cs.last_used_year = None, None