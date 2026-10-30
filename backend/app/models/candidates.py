from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Table, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

candidate_tags = Table(
    "candidate_tags",
    Base.metadata,
    Column("candidate_id", ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    category: Mapped[str | None] = mapped_column(String(100))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class SkillAlias(Base):
    __tablename__ = "skill_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(150), unique=True)


class TitleMapping(Base):
    __tablename__ = "title_mappings"
    __table_args__ = (UniqueConstraint("title_a", "title_b", name="uq_title_pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title_a: Mapped[str] = mapped_column(String(200))
    title_b: Mapped[str] = mapped_column(String(200))
    relatedness: Mapped[Decimal] = mapped_column(Numeric(3, 2))


class Candidate(TimestampMixin, Base):
    """NULL in a field means 'Not Mentioned'. field_sources labels each value as
    extracted / inferred / confirmed."""
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(200), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), index=True)
    location: Mapped[str | None] = mapped_column(String(200), index=True)
    country: Mapped[str | None] = mapped_column(String(100))
    availability: Mapped[str | None] = mapped_column(String(200))
    visa_status: Mapped[str | None] = mapped_column(String(100))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    rate_unit: Mapped[str | None] = mapped_column(String(20), server_default="hour")
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    status: Mapped[str] = mapped_column(String(50), server_default="New")
    current_requirement: Mapped[str | None] = mapped_column(String(300))
    recruiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    parse_status: Mapped[str] = mapped_column(String(60), server_default="Not Parsed")
    field_sources: Mapped[dict | None] = mapped_column(JSONB)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id", ondelete="SET NULL"))

    experiences: Mapped[list["CandidateExperience"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    education: Mapped[list["CandidateEducation"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    certifications: Mapped[list["CandidateCertification"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    skills: Mapped[list["CandidateSkill"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    documents: Mapped[list["CandidateDocument"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    notes: Mapped[list["CandidateNote"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    tags: Mapped[list[Tag]] = relationship(secondary=candidate_tags)


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    company: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    start_precision: Mapped[str | None] = mapped_column(String(10))
    end_precision: Mapped[str | None] = mapped_column(String(10))
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="false")
    description: Mapped[str | None] = mapped_column(Text)


class CandidateEducation(Base):
    __tablename__ = "candidate_education"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str | None] = mapped_column(String(200))
    degree: Mapped[str | None] = mapped_column(String(200))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)


class CandidateCertification(Base):
    __tablename__ = "candidate_certifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    issuer: Mapped[str | None] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(Integer)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    last_used_year: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), server_default="extracted")


class CandidateDocument(Base):
    """Also serves as resume versions: kind='resume' + version_no + is_current."""
    __tablename__ = "candidate_documents"
    __table_args__ = (
        Index("uq_candidate_current_resume", "candidate_id", unique=True,
              postgresql_where=text("is_current AND kind = 'resume'")),
        UniqueConstraint("candidate_id", "slot", name="uq_candidate_document_slot"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    original_filename: Mapped[str] = mapped_column(String(500))
    storage_path: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    version_no: Mapped[int | None] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="false")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    slot: Mapped[str | None] = mapped_column(String(30))
    display_name: Mapped[str | None] = mapped_column(String(100))


class CandidateNote(Base):
    __tablename__ = "candidate_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateRestriction(Base):
    __tablename__ = "candidate_restrictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    restriction_type: Mapped[str] = mapped_column(String(60))
    is_blocking: Mapped[bool] = mapped_column(Boolean, server_default="false")
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (UniqueConstraint("candidate_a_id", "candidate_b_id", name="uq_duplicate_pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_a_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    candidate_b_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    signals: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    review_status: Mapped[str] = mapped_column(String(30), server_default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())