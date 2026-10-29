import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.system import ActivityLog

ATS_DATA_TABLES = [
    "activity_logs",
    "resume_ingestions",
    "gmail_scanned_messages",
    "saved_searches",
    "embeddings",
    "candidate_tags",
    "candidate_skills",
    "candidate_notes",
    "candidate_documents",
    "candidate_certifications",
    "candidate_education",
    "candidate_experiences",
    "candidates",
    "job_skills",
    "job_locations",
    "interviews",
    "submission_events",
    "submissions",
    "job_candidates",
    "jobs",
    "clients",
    "tags",
    "title_mappings",
]


def clear_storage_root(root: Path | None = None) -> None:
    base = (root or settings.storage_dir).resolve()
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
        return
    for child in base.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def reset_ats_data(db: Session, actor_id: int | None = None) -> dict[str, object]:
    table_list = ", ".join(ATS_DATA_TABLES)
    db.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;"))
    if actor_id is not None:
        db.add(ActivityLog(
            user_id=actor_id,
            action="ats.reset",
            object_type="ats",
            new_value={"scope": "all_data", "message": "ATS data reset"},
        ))
    db.commit()
    clear_storage_root()
    return {"ok": True, "message": "All ATS data was cleared."}
