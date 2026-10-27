from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    location_preference: Mapped[str | None] = mapped_column(String(30))
    work_mode: Mapped[str | None] = mapped_column(String(20))  # Remote / Hybrid / Onsite
    required_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    visa_requirements: Mapped[str | None] = mapped_column(String(200))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(30), server_default="Open")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, server_default="true")
    min_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))


class JobCandidate(Base):
    __tablename__ = "job_candidates"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(30), server_default="New")
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    """One row per submission; resubmissions create new rows."""
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), server_default="Submitted")
    rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)


class SubmissionEvent(Base):
    __tablename__ = "submission_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)


class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str | None] = mapped_column(String(50))
    outcome: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)

class JobLocation(Base):
    """One entry of a job with the Multiple locations preference. Each has its own relocation setting."""
    __tablename__ = "job_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    relocation_ok: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer, server_default="0")