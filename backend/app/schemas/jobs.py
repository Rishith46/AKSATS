from decimal import Decimal

from pydantic import BaseModel, Field

WORK_MODES = {"Remote", "Hybrid", "Onsite"}
STATUSES = {"Open", "On Hold", "Filled", "Closed"}


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    client: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = None
    required_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    visa_requirements: str | None = Field(default=None, max_length=200)
    rate: Decimal | None = Field(default=None, ge=0)
    status: str = "Open"
    required_skills: list[str] = []
    preferred_skills: list[str] = []


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    client: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = None
    required_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    visa_requirements: str | None = Field(default=None, max_length=200)
    rate: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []