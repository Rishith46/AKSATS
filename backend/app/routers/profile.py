from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.geo import split_location
from app.models.access import User
from app.models.candidates import (Candidate, CandidateDocument, CandidateExperience,
                                   CandidateCertification, CandidateEducation, CandidateSkill,
                                   Skill)
from app.services.experience_edit import format_partial_date
from app.services.resume_export import build_docx, build_pdf, filename_stem

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
    education = db.scalars(select(CandidateEducation)
                           .where(CandidateEducation.candidate_id == cid)
                           .order_by(CandidateEducation.end_year.desc().nulls_last(),
                                     CandidateEducation.id.desc())).all()
    certifications = db.scalars(select(CandidateCertification)
                                .where(CandidateCertification.candidate_id == cid)
                                .order_by(CandidateCertification.year.desc().nulls_last(),
                                          CandidateCertification.id.desc())).all()
    skills = db.execute(
        select(Skill.id, Skill.name, CandidateSkill.evidence, CandidateSkill.source,
               CandidateSkill.years, CandidateSkill.last_used_year)
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
        "country": c.country,
        "availability": c.availability,
        "rate_unit": c.rate_unit,
        "city": split_location(c.location)[0],
        "state": split_location(c.location)[1],
        "visa_status": c.visa_status,
        "rate": str(c.rate) if c.rate is not None else None,
        "total_experience_years": str(c.total_experience_years) if c.total_experience_years is not None else None,
        "status": c.status,
        "parse_status": c.parse_status,
        "field_sources": c.field_sources or {},
        "archived_at": c.archived_at,
        "created_at": c.created_at,
        "experiences": [{
            "id": e.id, "company": e.company, "title": e.title, "location": e.location,
            "description": e.description,
            "start": format_partial_date(e.start_date, e.start_precision),
            "end": format_partial_date(e.end_date, e.end_precision),
            "start_date": e.start_date, "start_precision": e.start_precision,
            "end_date": e.end_date, "end_precision": e.end_precision,
            "is_current": e.is_current,
        } for e in exps],
        "education": [{
            "institution": e.institution,
            "degree": e.degree,
            "field_of_study": e.field_of_study,
            "start_year": e.start_year,
            "end_year": e.end_year,
        } for e in education],
        "certifications": [{
            "name": c.name,
            "issuer": c.issuer,
            "year": c.year,
        } for c in certifications],
        "skills": [{"skill_id": sid, "name": n, "evidence": ev, "source": src,
                    "years": float(y) if y is not None else None, "last_used_year": ly}
                   for sid, n, ev, src, y, ly in skills],
        "documents": [{
            "id": d.id, "kind": d.kind, "filename": d.original_filename,
            "version_no": d.version_no, "is_current": d.is_current,
            "uploaded_at": d.uploaded_at, "extracted_text": d.extracted_text,
        } for d in docs],
    }


@router.get("/{cid}/resume-export")
def export_ats_resume(cid: int, format: str = "docx", db: Session = Depends(get_db),
                      user: User = Depends(require_permission("candidate.view"))):
    if format not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="format must be docx or pdf")
    candidate = db.get(Candidate, cid)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    experiences = db.scalars(
        select(CandidateExperience).where(CandidateExperience.candidate_id == cid)
        .order_by(CandidateExperience.start_date.desc().nulls_last(), CandidateExperience.id.desc())
    ).all()
    education = db.scalars(
        select(CandidateEducation).where(CandidateEducation.candidate_id == cid)
        .order_by(CandidateEducation.end_year.desc().nulls_last(), CandidateEducation.id.desc())
    ).all()
    certifications = db.scalars(
        select(CandidateCertification).where(CandidateCertification.candidate_id == cid)
        .order_by(CandidateCertification.year.desc().nulls_last(), CandidateCertification.id.desc())
    ).all()
    skills = db.execute(
        select(Skill.name, CandidateSkill.years, CandidateSkill.last_used_year,
               CandidateSkill.evidence)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .where(CandidateSkill.candidate_id == cid).order_by(Skill.name)
    ).all()
    content = (build_docx if format == "docx" else build_pdf)(
        candidate, experiences, education, certifications, skills)
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx" else "application/pdf"
    )
    filename = f"{filename_stem(candidate.full_name)}-ats-resume.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )