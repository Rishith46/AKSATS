from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

WORK_MODES = {"Remote", "Hybrid", "Onsite"}
STATUSES = {"Open", "On Hold", "Filled", "Closed"}
Preference = Literal["relocation_ok", "relocation_not_ok", "multiple"]


class LocationIn(BaseModel):
    city: str | None = Field(default=None, max_length=100)
    state: str = Field(max_length=50)
    relocation_ok: bool


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    client: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = None
    location_preference: Preference | None = None
    locations: list[LocationIn] = []
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
    location_preference: Preference | None = None
    locations: list[LocationIn] | None = None
    required_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    visa_requirements: str | None = Field(default=None, max_length=200)
    rate: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []