from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import (Candidate, CandidateExperience, CandidateRestriction,
                                   CandidateSkill, Skill)
from app.models.jobs import Job, JobSkill
from app.models.system import MatchConfig
from app.services.matching import (DEFAULT_WEIGHTS, combine, experience_score, location_score,
                                   skills_score, title_score, visa_score)

router = APIRouter(prefix="/jobs", tags=["matching"])


@router.get("/{jid}/matches")
def matches(jid: int, limit: int = 50, db: Session = Depends(get_db),
            user: User = Depends(require_permission("search.use"))):
    job = db.get(Job, jid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cfg = db.scalar(select(MatchConfig).where(MatchConfig.is_active.is_(True)))
    weights = dict(cfg.weights) if cfg and cfg.weights else dict(DEFAULT_WEIGHTS)

    rows = db.execute(select(Skill.name, JobSkill.is_required)
                      .join(JobSkill, JobSkill.skill_id == Skill.id)
                      .where(JobSkill.job_id == jid).order_by(Skill.name)).all()
    req = [n for n, r in rows if r]
    pref = [n for n, r in rows if not r]

    cands = db.scalars(select(Candidate).where(Candidate.archived_at.is_(None),
                                               Candidate.merged_into_id.is_(None))).all()
    ids = [c.id for c in cands]

    skills: dict[int, dict[str, str | None]] = {i: {} for i in ids}
    for cid, name, ev in db.execute(
            select(CandidateSkill.candidate_id, Skill.name, CandidateSkill.evidence)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_id.in_(ids))).all():
        skills[cid][name] = ev
    titles: dict[int, list[str]] = {i: [] for i in ids}
    for cid, t in db.execute(select(CandidateExperience.candidate_id, CandidateExperience.title)
                             .where(CandidateExperience.candidate_id.in_(ids))).all():
        titles[cid].append(t)
    restr: dict[int, list[dict]] = {i: [] for i in ids}
    for r in db.scalars(select(CandidateRestriction).where(CandidateRestriction.candidate_id.in_(ids))).all():
        restr[r.candidate_id].append({"type": r.restriction_type, "blocking": r.is_blocking})

    results = []
    for c in cands:
        have = skills[c.id]
        s_score, s_detail, matching, missing = skills_score(req, have.keys())
        signals = {
            "required_skills": (s_score, s_detail),
            "relevant_experience": experience_score(job.required_experience_years, c.total_experience_years),
            "job_title": title_score(job.title, titles[c.id]),
            "location": location_score(job.location, job.work_mode, c.location),
            "visa": visa_score(job.visa_requirements, c.visa_status),
        }
        score, coverage, breakdown = combine(weights, signals)
        total_w = sum(s["weight"] for s in breakdown.values())
        earned = sum(s["weight"] * s["score"] for s in breakdown.values() if s["score"] is not None)
        floor = round(100 * earned / total_w, 1) if total_w else 0.0
        results.append({
            "score_floor": floor,
            "candidate_id": c.id, "full_name": c.full_name, "parse_status": c.parse_status,
            "score": score, "coverage_percent": coverage, "signals": breakdown,
            "matching_required": [{"skill": s, "evidence": have.get(s)} for s in matching],
            "missing_required": missing,
            "matching_preferred": [{"skill": s, "evidence": have.get(s)} for s in pref if s in have],
            "missing_preferred": [s for s in pref if s not in have],
            "restrictions": restr[c.id],
        })
    results.sort(key=lambda r: (-r["score_floor"], r["candidate_id"]))
    return {
        "job_id": job.id, "job_title": job.title,
        "label": "Internal recruiting match score. Not an objective measure; the recruiter decides.",
        "ranking": "Ranked by score_floor (points earned out of all weights, unknown signals count as zero). score is out of the signals that had data; read it with coverage_percent.",
        "weights": weights,
        "not_scored": ["semantic_similarity", "recent_experience"],
        "candidates": results[:min(limit, 200)],
    }