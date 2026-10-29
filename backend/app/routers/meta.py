from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import CandidateSkill, Skill, SkillAlias
from app.models.jobs import JobSkill
from app.models.system import ActivityLog
from app.services.reset_ats import reset_ats_data
from app.visa import VISA_OPTIONS

router = APIRouter(prefix="/meta", tags=["meta"])
RESET_ATS_ALLOWED_EMAIL = "vamshi@allknownservices.com"


@router.get("/visa-statuses")
def visa_statuses(user: User = Depends(require_permission("candidate.view"))):
    return [{"value": v, "label": label} for v, label in VISA_OPTIONS]


class SkillReviewIn(BaseModel):
    canonical_skill_id: int | None = None


@router.get("/skills/review")
def skills_for_review(db: Session = Depends(get_db),
                      user: User = Depends(require_permission("job.manage"))):
    pending = db.scalars(select(Skill).where(Skill.needs_review.is_(True)).order_by(func.lower(Skill.name))).all()
    approved = db.scalars(select(Skill).where(Skill.needs_review.is_(False)).order_by(func.lower(Skill.name))).all()
    return {
        "pending": [{"id": skill.id, "name": skill.name} for skill in pending],
        "approved": [{"id": skill.id, "name": skill.name} for skill in approved],
    }


@router.post("/reset")
def reset_ats(db: Session = Depends(get_db),
              user: User = Depends(require_permission("ats.reset"))):
    if user.email.casefold() != RESET_ATS_ALLOWED_EMAIL:
        raise HTTPException(status_code=403, detail="Only Vamshi can reset ATS data")
    result = reset_ats_data(db, actor_id=user.id)
    return result


@router.post("/skills/{skill_id}/review")
def review_skill(skill_id: int, body: SkillReviewIn, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("job.manage"))):
    skill = db.get(Skill, skill_id)
    if skill is None or not skill.needs_review:
        raise HTTPException(status_code=404, detail="Pending skill not found")

    if body.canonical_skill_id is None:
        skill.needs_review = False
        db.add(ActivityLog(user_id=user.id, action="skill.approved", object_type="skill",
                           object_id=skill.id, new_value={"name": skill.name}))
        db.commit()
        return {"id": skill.id, "name": skill.name, "merged": False}

    canonical = db.get(Skill, body.canonical_skill_id)
    if canonical is None or canonical.needs_review or canonical.id == skill.id:
        raise HTTPException(status_code=422, detail="Choose a different approved skill to merge into")

    name_taken = db.scalar(select(Skill.id).where(
        func.lower(Skill.name) == skill.name.lower(), Skill.id != skill.id))
    alias = db.scalar(select(SkillAlias).where(func.lower(SkillAlias.alias) == skill.name.lower()))
    if name_taken is not None or (alias is not None and alias.skill_id != canonical.id):
        raise HTTPException(status_code=409, detail="This skill name is already used by another skill")

    # Keep one association per job/candidate when merging duplicate catalog entries.
    for job_skill in db.scalars(select(JobSkill).where(JobSkill.skill_id == skill.id)).all():
        existing = db.scalar(select(JobSkill).where(
            JobSkill.job_id == job_skill.job_id, JobSkill.skill_id == canonical.id))
        if existing:
            existing.is_required = existing.is_required or job_skill.is_required
            if existing.min_years is None:
                existing.min_years = job_skill.min_years
            db.delete(job_skill)
        else:
            job_skill.skill_id = canonical.id

    for candidate_skill in db.scalars(
        select(CandidateSkill).where(CandidateSkill.skill_id == skill.id)
    ).all():
        existing = db.scalar(select(CandidateSkill).where(
            CandidateSkill.candidate_id == candidate_skill.candidate_id,
            CandidateSkill.skill_id == canonical.id))
        if existing:
            existing.years = max(
                (value for value in (existing.years, candidate_skill.years) if value is not None),
                default=None,
            )
            existing.last_used_year = max(
                (value for value in (existing.last_used_year, candidate_skill.last_used_year) if value is not None),
                default=None,
            )
            if candidate_skill.evidence and candidate_skill.evidence not in (existing.evidence or ""):
                existing.evidence = "\n".join(filter(None, (existing.evidence, candidate_skill.evidence)))
            if existing.source != "confirmed":
                existing.source = candidate_skill.source
            if existing.evidence is None:
                existing.evidence = candidate_skill.evidence
            db.delete(candidate_skill)
        else:
            candidate_skill.skill_id = canonical.id

    for skill_alias in db.scalars(select(SkillAlias).where(SkillAlias.skill_id == skill.id)).all():
        existing_alias = db.scalar(select(SkillAlias).where(
            func.lower(SkillAlias.alias) == skill_alias.alias.lower()))
        if existing_alias is None:
            skill_alias.skill_id = canonical.id
        elif existing_alias.skill_id == canonical.id:
            db.delete(skill_alias)

    if alias is None:
        db.add(SkillAlias(skill_id=canonical.id, alias=skill.name))
    elif alias.skill_id == skill.id:
        alias.skill_id = canonical.id
    db.add(ActivityLog(user_id=user.id, action="skill.merged", object_type="skill",
                       object_id=canonical.id,
                       old_value={"name": skill.name, "skill_id": skill.id},
                       new_value={"name": canonical.name, "skill_id": canonical.id}))
    db.delete(skill)
    db.commit()
    return {"id": canonical.id, "name": canonical.name, "merged": True}