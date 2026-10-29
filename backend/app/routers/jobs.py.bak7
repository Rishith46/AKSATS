import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Skill, SkillAlias
from app.models.jobs import Client, Job, JobSkill
from app.models.system import ActivityLog
from app.schemas.jobs import STATUSES, WORK_MODES, JobCreate, JobUpdate

log = logging.getLogger("aks_ats.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])

SCALARS = ["title", "description", "location", "work_mode", "required_experience_years",
           "visa_requirements", "rate", "status"]


def _like(s: str) -> str:
    return "%" + s.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _check_enums(work_mode, status):
    if work_mode is not None and work_mode not in WORK_MODES:
        raise HTTPException(status_code=400, detail=f"work_mode must be one of: {', '.join(sorted(WORK_MODES))}")
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(STATUSES))}")


def _resolve(db: Session, names: list[str]):
    found: dict[int, str] = {}
    unknown: list[str] = []
    for raw in names:
        t = raw.strip()
        if not t:
            continue
        s = db.scalar(select(Skill).where(func.lower(Skill.name) == t.lower()))
        if s is None:
            s = db.scalar(select(Skill).join(SkillAlias, SkillAlias.skill_id == Skill.id)
                          .where(func.lower(SkillAlias.alias) == t.lower()))
        if s is None:
            unknown.append(t)
        else:
            found[s.id] = s.name
    return found, unknown


def _resolve_both(db: Session, required: list[str], preferred: list[str]):
    req, unk1 = _resolve(db, required)
    pref, unk2 = _resolve(db, preferred)
    unknown = unk1 + unk2
    if unknown:
        raise HTTPException(status_code=400, detail=(
            "Unknown skills: " + ", ".join(unknown) +
            ". Skills must exist in the skills list; nothing was saved."))
    both = set(req) & set(pref)
    if both:
        names = ", ".join(sorted(req[i] for i in both))
        raise HTTPException(status_code=400, detail=f"A skill cannot be both required and preferred: {names}")
    return req, pref


def _client_id(db: Session, name: str | None):
    if name is None or not name.strip():
        return None
    c = db.scalar(select(Client).where(func.lower(Client.name) == name.strip().lower()))
    if c is None:
        c = Client(name=name.strip())
        db.add(c)
        db.flush()
    return c.id


def _skill_names(db: Session, job_id: int):
    rows = db.execute(select(Skill.name, JobSkill.is_required)
                      .join(JobSkill, JobSkill.skill_id == Skill.id)
                      .where(JobSkill.job_id == job_id).order_by(Skill.name)).all()
    return [n for n, r in rows if r], [n for n, r in rows if not r]


def _out(db: Session, j: Job) -> dict:
    client = db.get(Client, j.client_id).name if j.client_id else None
    req, pref = _skill_names(db, j.id)
    return {
        "id": j.id, "title": j.title, "client": client, "description": j.description,
        "location": j.location, "work_mode": j.work_mode,
        "required_experience_years": str(j.required_experience_years) if j.required_experience_years is not None else None,
        "visa_requirements": j.visa_requirements,
        "rate": str(j.rate) if j.rate is not None else None,
        "status": j.status, "owner_id": j.owner_id,
        "created_at": j.created_at, "updated_at": j.updated_at,
        "required_skills": req, "preferred_skills": pref,
    }


def _get(db: Session, jid: int) -> Job:
    j = db.get(Job, jid)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


def _log(db: Session, user: User, action: str, jid: int, old=None, new=None):
    db.add(ActivityLog(user_id=user.id, action=action, object_type="job", object_id=jid,
                       old_value=old, new_value=new))


@router.post("", status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db),
               user: User = Depends(require_permission("job.manage"))):
    _check_enums(body.work_mode, body.status)
    req, pref = _resolve_both(db, body.required_skills, body.preferred_skills)
    j = Job(title=body.title.strip(), client_id=_client_id(db, body.client),
            description=body.description, location=body.location, work_mode=body.work_mode,
            required_experience_years=body.required_experience_years,
            visa_requirements=body.visa_requirements, rate=body.rate,
            status=body.status, owner_id=user.id)
    db.add(j)
    db.flush()
    for sid in req:
        db.add(JobSkill(job_id=j.id, skill_id=sid, is_required=True))
    for sid in pref:
        db.add(JobSkill(job_id=j.id, skill_id=sid, is_required=False))
    db.flush()
    _log(db, user, "job.created", j.id,
         new={"title": j.title, "client": body.client, "required_skills": sorted(req.values()),
              "preferred_skills": sorted(pref.values())})
    db.commit()
    db.refresh(j)
    return _out(db, j)


@router.get("")
def list_jobs(status: str | None = None, q: str | None = None, limit: int = 100, offset: int = 0,
              db: Session = Depends(get_db),
              user: User = Depends(require_permission("candidate.view"))):
    stmt = select(Job).order_by(Job.id.desc())
    if status:
        stmt = stmt.where(Job.status == status)
    if q and q.strip():
        stmt = stmt.where(Job.title.ilike(_like(q), escape="\\"))
    rows = db.scalars(stmt.limit(min(limit, 200)).offset(offset)).all()
    return [_out(db, j) for j in rows]


@router.get("/{jid}")
def get_job(jid: int, db: Session = Depends(get_db),
            user: User = Depends(require_permission("candidate.view"))):
    return _out(db, _get(db, jid))


@router.patch("/{jid}")
def update_job(jid: int, body: JobUpdate, db: Session = Depends(get_db),
               user: User = Depends(require_permission("job.manage"))):
    j = _get(db, jid)
    changes = body.model_dump(exclude_unset=True)
    if "title" in changes and not changes["title"]:
        raise HTTPException(status_code=400, detail="title cannot be empty")
    if "status" in changes and changes["status"] is None:
        raise HTTPException(status_code=400, detail="status cannot be empty")
    _check_enums(changes.get("work_mode"), changes.get("status"))

    old, new = {}, {}
    skills_change = "required_skills" in changes or "preferred_skills" in changes
    if skills_change:
        cur_req, cur_pref = _skill_names(db, jid)
        req, pref = _resolve_both(db, changes.get("required_skills", cur_req),
                                  changes.get("preferred_skills", cur_pref))
        old["required_skills"], old["preferred_skills"] = cur_req, cur_pref
        new["required_skills"], new["preferred_skills"] = sorted(req.values()), sorted(pref.values())

    for k in SCALARS:
        if k in changes:
            old[k] = str(getattr(j, k)) if getattr(j, k) is not None else None
            setattr(j, k, changes[k].strip() if k == "title" else changes[k])
            new[k] = str(getattr(j, k)) if getattr(j, k) is not None else None
    if "client" in changes:
        old["client"] = db.get(Client, j.client_id).name if j.client_id else None
        j.client_id = _client_id(db, changes["client"])
        new["client"] = changes["client"]

    if skills_change:
        db.query(JobSkill).filter(JobSkill.job_id == jid).delete()
        db.flush()
        for sid in req:
            db.add(JobSkill(job_id=jid, skill_id=sid, is_required=True))
        for sid in pref:
            db.add(JobSkill(job_id=jid, skill_id=sid, is_required=False))

    db.flush()
    _log(db, user, "job.edited", jid, old=old, new=new)
    db.commit()
    db.refresh(j)
    return _out(db, j)