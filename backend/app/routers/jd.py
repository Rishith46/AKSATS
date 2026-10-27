from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db, require_permission
from app.models.access import User
from app.services.jd_read import read_jd
from app.services.skill_match import load_terms

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JDIn(BaseModel):
    text: str = Field(min_length=20, max_length=50000)


@router.post("/read-jd")
def read_job_description(body: JDIn, db: Session = Depends(get_db),
                         user: User = Depends(require_permission("job.manage"))):
    """Drafts a job from pasted job-description text. Nothing is saved. The recruiter reviews it."""
    return read_jd(body.text, load_terms(db))