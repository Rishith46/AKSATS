from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate, CandidateExperience, CandidateSkill, Skill
from app.models.system import ActivityLog
from app.services.experience_edit import check_experience, format_partial_date, parse_partial_date
from app.services.experience_total import recalc_total
from app.services.skill_dates import refresh_skill_dates
from app.services.skill_lookup import find_skill

router = APIRouter(prefix="/candidates/{cid}", tags=["candidate-edit"])
THIS_YEAR = date.today().year


def _nonblank(v):
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


def _blank_none(v):
    return (v.strip() or None) if v is not None else None


Name = Annotated[str, AfterValidator(_nonblank)]
Opt = Annotated[str | None, AfterValidator(_blank_none)]


class SkillIn(BaseModel):
    name: Name = Field(max_length=150)
    years: Decimal | None = Field(default=None, ge=0, le=60)
    last_used_year: int | None = Field(default=None, ge=1970, le=THIS_YEAR + 1)
    create_if_missing: bool = False


class SkillPatch(BaseModel):
    years: Decimal | None = Field(default=None, ge=0, le=60)
    last_used_year: int | None = Field(default=None, ge=1970, le=THIS_YEAR + 1)


class ExpIn(BaseModel):
    company: Opt = Field(default=None, max_length=200)
    title: Opt = Field(default=None, max_length=200)
    location: Opt = Field(default=None, max_length=200)
    start: Opt = Field(default=None, max_length=10)
    end: Opt = Field(default=None, max_length=10)
    is_current: bool = False
    description: Opt = Field(default=None, max_length=30000)


class ExpPatch(BaseModel):
    company: Opt = Field(default=None, max_length=200)
    title: Opt = Field(default=None, max_length=200)
    location: Opt = Field(default=None, max_length=200)
    start: Opt = Field(default=None, max_length=10)
    end: Opt = Field(default=None, max_length=10)
    is_current: bool | None = None
    description: Opt = Field(default=None, max_length=30000)


def _cand(db: Session, cid: int) -> Candidate:
    c = db.get(Candidate, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


def _log(db: Session, user: User, action: str, cid: int, old=None, new=None) -> None:
    db.add(ActivityLog(user_id=user.id, action=action, object_type="candidate",
                       object_id=cid, old_value=old, new_value=new))


def _skill_out(cs: CandidateSkill, name: str, created: bool = False) -> dict:
    return {"skill_id": cs.skill_id, "name": name,
            "years": float(cs.years) if cs.years is not None else None,
            "last_used_year": cs.last_used_year, "source": cs.source,
            "evidence": cs.evidence, "created": created}


def _get_cs(db: Session, cid: int, skill_id: int):
    cs = db.scalar(select(CandidateSkill).where(CandidateSkill.candidate_id == cid,
                                                CandidateSkill.skill_id == skill_id))
    if not cs:
        raise HTTPException(status_code=404, detail="This candidate does not have that skill")
    return cs


@router.post("/skills", status_code=201)
def add_skill(cid: int, body: SkillIn, response: Response, db: Session = Depends(get_db),
              user: User = Depends(require_permission("candidate.edit"))):
    _cand(db, cid)
    skill = find_skill(db, body.name)
    created = False
    if skill is None:
        if not body.create_if_missing:
            raise HTTPException(status_code=409, detail=(
                f"Unknown skill: {body.name}. It is not in the skills list. Confirm to add it as a new skill."))
        skill = Skill(name=body.name)
        db.add(skill)
        db.flush()
        created = True
    cs = db.scalar(select(CandidateSkill).where(CandidateSkill.candidate_id == cid,
                                                CandidateSkill.skill_id == skill.id))
    if cs:
        old = {"years": float(cs.years) if cs.years is not None else None, "last_used_year": cs.last_used_year}
        if "years" in body.model_fields_set:
            cs.years = body.years
        if "last_used_year" in body.model_fields_set:
            cs.last_used_year = body.last_used_year
        cs.source = "confirmed"
        response.status_code = 200
        action = "candidate.skill_updated"
    else:
        old = None
        cs = CandidateSkill(candidate_id=cid, skill_id=skill.id, years=body.years,
                            last_used_year=body.last_used_year, source="confirmed")
        db.add(cs)
        action = "candidate.skill_added"
    db.flush()
    _log(db, user, action, cid, old=old,
         new={"skill": skill.name, "years": float(cs.years) if cs.years is not None else None,
              "last_used_year": cs.last_used_year, "new_to_skills_list": created})
    db.commit()
    return _skill_out(cs, skill.name, created)


@router.patch("/skills/{skill_id}")
def patch_skill(cid: int, skill_id: int, body: SkillPatch, db: Session = Depends(get_db),
                user: User = Depends(require_permission("candidate.edit"))):
    _cand(db, cid)
    cs = _get_cs(db, cid, skill_id)
    name = db.get(Skill, skill_id).name
    old = {"years": float(cs.years) if cs.years is not None else None, "last_used_year": cs.last_used_year}
    if "years" in body.model_fields_set:
        cs.years = body.years
    if "last_used_year" in body.model_fields_set:
        cs.last_used_year = body.last_used_year
    cs.source = "confirmed"
    db.flush()
    _log(db, user, "candidate.skill_updated", cid, old=old,
         new={"skill": name, "years": float(cs.years) if cs.years is not None else None,
              "last_used_year": cs.last_used_year})
    db.commit()
    return _skill_out(cs, name)


@router.delete("/skills/{skill_id}")
def delete_skill(cid: int, skill_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("candidate.edit"))):
    _cand(db, cid)
    cs = _get_cs(db, cid, skill_id)
    name = db.get(Skill, skill_id).name
    was = cs.source
    db.delete(cs)
    _log(db, user, "candidate.skill_removed", cid, old={"skill": name, "source": was})
    db.commit()
    note = "A skill read from the resume comes back if the resume is parsed again." if was == "extracted" else None
    return {"removed": name, "note": note}


def _exp_out(e: CandidateExperience) -> dict:
    return {"id": e.id, "company": e.company, "title": e.title, "location": e.location,
            "start": format_partial_date(e.start_date, e.start_precision),
            "end": format_partial_date(e.end_date, e.end_precision),
            "is_current": e.is_current, "description": e.description}


def _summary(e: CandidateExperience) -> dict:
    o = _exp_out(e)
    return {k: o[k] for k in ("id", "company", "title", "start", "end", "is_current")}


def _total(c: Candidate):
    return str(c.total_experience_years) if c.total_experience_years is not None else None


def _refresh(db: Session, c: Candidate) -> None:
    db.flush()
    recalc_total(db, c)
    db.flush()
    refresh_skill_dates(db, c.id)


def _get_exp(db: Session, cid: int, eid: int) -> CandidateExperience:
    e = db.get(CandidateExperience, eid)
    if not e or e.candidate_id != cid:
        raise HTTPException(status_code=404, detail="Experience not found for this candidate")
    return e


@router.post("/experiences", status_code=201)
def add_experience(cid: int, body: ExpIn, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("candidate.edit"))):
    c = _cand(db, cid)
    try:
        sd, sp = parse_partial_date(body.start)
        ed, ep = parse_partial_date(body.end)
        check_experience(body.company, body.title, sd, ed, body.is_current)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    e = CandidateExperience(candidate_id=cid, company=body.company, title=body.title, location=body.location,
                            start_date=sd, start_precision=sp, end_date=ed, end_precision=ep,
                            is_current=body.is_current, description=body.description)
    db.add(e)
    _refresh(db, c)
    _log(db, user, "candidate.experience_added", cid, new=_summary(e))
    db.commit()
    return {"experience": _exp_out(e), "total_experience_years": _total(c)}


@router.patch("/experiences/{eid}")
def edit_experience(cid: int, eid: int, body: ExpPatch, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("candidate.edit"))):
    c = _cand(db, cid)
    e = _get_exp(db, cid, eid)
    old = _summary(e)
    given = body.model_fields_set
    company = body.company if "company" in given else e.company
    title = body.title if "title" in given else e.title
    is_current = body.is_current if body.is_current is not None else e.is_current
    sd, sp, ed, ep = e.start_date, e.start_precision, e.end_date, e.end_precision
    try:
        if "start" in given:
            sd, sp = parse_partial_date(body.start)
        if "end" in given:
            ed, ep = parse_partial_date(body.end)
        elif body.is_current:
            ed, ep = None, None
        check_experience(company, title, sd, ed, is_current)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    e.company, e.title = company, title
    if "location" in given:
        e.location = body.location
    if "description" in given:
        e.description = body.description
    e.start_date, e.start_precision, e.end_date, e.end_precision, e.is_current = sd, sp, ed, ep, is_current
    _refresh(db, c)
    _log(db, user, "candidate.experience_edited", cid, old=old, new=_summary(e))
    db.commit()
    return {"experience": _exp_out(e), "total_experience_years": _total(c)}


@router.delete("/experiences/{eid}")
def delete_experience(cid: int, eid: int, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("candidate.edit"))):
    c = _cand(db, cid)
    e = _get_exp(db, cid, eid)
    old = _summary(e)
    db.delete(e)
    _refresh(db, c)
    _log(db, user, "candidate.experience_removed", cid, old=old)
    db.commit()
    return {"removed": eid, "total_experience_years": _total(c)}