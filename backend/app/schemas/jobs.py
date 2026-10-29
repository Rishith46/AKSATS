from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.visa import VISA_VALUES

WORK_MODES = {"Remote", "Hybrid", "Onsite"}
STATUSES = {"Open", "On Hold", "Filled", "Closed"}
Preference = Literal["relocation_ok", "relocation_not_ok", "multiple"]


class LocationIn(BaseModel):
    city: str | None = Field(default=None, max_length=100)
    state: str = Field(max_length=50)
    relocation_ok: bool


def _visa_requirements(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    unknown = sorted(set(value) - set(VISA_VALUES))
    if unknown:
        raise ValueError(f"visa_requirements must use the visa options: {', '.join(unknown)}")
    return list(dict.fromkeys(value)) or None


def _parse_legacy_visa_value(value):
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return value


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    client: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = None
    location_preference: Preference | None = None
    locations: list[LocationIn] = []
    required_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    visa_requirements: list[str] | None = Field(default=None, max_length=10)
    rate: Decimal | None = Field(default=None, ge=0)
    status: str = "Open"
    required_skills: list[str] = []
    preferred_skills: list[str] = []

    @field_validator("visa_requirements", mode="before")
    @classmethod
    def parse_visa_requirements(cls, value):
        return _parse_legacy_visa_value(value)

    @field_validator("visa_requirements")
    @classmethod
    def validate_visa_requirements(cls, value):
        return _visa_requirements(value)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    client: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    location: str | None = Field(default=None, max_length=200)
    work_mode: str | None = None
    location_preference: Preference | None = None
    locations: list[LocationIn] | None = None
    required_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    visa_requirements: list[str] | None = Field(default=None, max_length=10)
    rate: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []

    @field_validator("visa_requirements", mode="before")
    @classmethod
    def parse_visa_requirements(cls, value):
        return _parse_legacy_visa_value(value)

    @field_validator("visa_requirements")
    @classmethod
    def validate_visa_requirements(cls, value):
        return _visa_requirements(value)