from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.models.candidates import Candidate
from app.models.jobs import Job
from app.models.system import ResumeIngestion

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=timezone.utc)


@router.get("/summary")
def summary(months: int = Query(12, ge=3, le=24), db: Session = Depends(get_db),
            user: User = Depends(require_permission("user.manage"))):

    now = datetime.now(timezone.utc)
    current_month = _month_start(now.year, now.month)
    month_starts = []
    year, month = now.year, now.month
    for _ in range(months):
        month_starts.append(_month_start(year, month))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    month_starts.reverse()
    since = month_starts[0]

    months_by_key = {
        start.strftime("%Y-%m"): {
            "month": start.date().isoformat(),
            "email_resumes": 0,
            "upload_resumes": 0,
            "job_roles": 0,
            "new_candidates": 0,
        }
        for start in month_starts
    }

    resume_month = func.date_trunc("month", ResumeIngestion.processed_at)
    resume_rows = db.execute(
        select(resume_month,
               ResumeIngestion.source, func.count())
        .where(ResumeIngestion.status == "Processed",
               ResumeIngestion.processed_at >= since)
        .group_by(resume_month, ResumeIngestion.source)
    ).all()
    for month_value, source, count in resume_rows:
        key = month_value.strftime("%Y-%m")
        if key in months_by_key:
            field = "email_resumes" if source == "email" else "upload_resumes"
            months_by_key[key][field] += count

    job_month = func.date_trunc("month", Job.created_at)
    job_rows = db.execute(
        select(job_month, func.count())
        .where(Job.created_at >= since)
        .group_by(job_month)
    ).all()
    for month_value, count in job_rows:
        key = month_value.strftime("%Y-%m")
        if key in months_by_key:
            months_by_key[key]["job_roles"] = count

    active_candidate_filters = (
        Candidate.archived_at.is_(None),
        Candidate.merged_into_id.is_(None),
    )
    candidate_month = func.date_trunc("month", Candidate.created_at)
    candidate_month_rows = db.execute(
        select(candidate_month, func.count())
        .where(Candidate.created_at >= since, *active_candidate_filters)
        .group_by(candidate_month)
    ).all()
    for month_value, count in candidate_month_rows:
        key = month_value.strftime("%Y-%m")
        if key in months_by_key:
            months_by_key[key]["new_candidates"] = count

    parsed_this_month = db.scalar(
        select(func.count()).select_from(ResumeIngestion)
        .where(ResumeIngestion.status == "Processed",
               ResumeIngestion.processed_at >= current_month)
    ) or 0
    open_jobs = db.scalar(
        select(func.count()).select_from(Job).where(Job.status == "Open")
    ) or 0
    active_candidates = db.scalar(
        select(func.count()).select_from(Candidate)
        .where(*active_candidate_filters)
    ) or 0
    candidate_statuses = db.execute(
        select(Candidate.status, func.count())
        .where(*active_candidate_filters)
        .group_by(Candidate.status)
        .order_by(func.lower(Candidate.status))
    ).all()
    candidate_parse_statuses = db.execute(
        select(Candidate.parse_status, func.count())
        .where(*active_candidate_filters)
        .group_by(Candidate.parse_status)
        .order_by(func.lower(Candidate.parse_status))
    ).all()
    awaiting_processing = db.scalar(
        select(func.count()).select_from(ResumeIngestion)
        .where(ResumeIngestion.status.in_(("Received", "Processing")))
    ) or 0
    needs_review = db.scalar(
        select(func.count()).select_from(ResumeIngestion)
        .where(ResumeIngestion.status == "Needs Review")
    ) or 0

    return {
        "generated_at": now,
        "totals": {
            "active_candidates": active_candidates,
            "open_jobs": open_jobs,
            "parsed_this_month": parsed_this_month,
            "awaiting_processing": awaiting_processing,
            "needs_review": needs_review,
        },
        "candidate_statuses": [
            {"status": status or "Unknown", "count": count}
            for status, count in candidate_statuses
        ],
        "candidate_parse_statuses": [
            {"status": status or "Unknown", "count": count}
            for status, count in candidate_parse_statuses
        ],
        "months": list(months_by_key.values()),
        "resume_count_definition": "Successfully parsed inbox resumes, grouped by processing month and source.",
        "candidate_count_definition": "Current non-archived, non-merged candidates only; deleted records are not included.",
    }
