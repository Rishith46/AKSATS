import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import AfterValidator

from app.geo import normalize_country
from app.visa import check_visa

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_CHARS = re.compile(r"^[0-9+()\-.\s xX]+$")


def _clean(v):
    if v is None:
        return None
    v = v.strip()
    return v or None


def _email(v):
    v = _clean(v)
    if v is not None and not EMAIL_RE.match(v):
        raise ValueError("email is not a valid address")
    return v


def _phone(v):
    v = _clean(v)
    if v is None:
        return None
    digits = re.sub(r"\D", "", v)
    if not PHONE_CHARS.match(v) or not 7 <= len(digits) <= 15:
        raise ValueError("phone must contain 7 to 15 digits")
    return v


def _linkedin(v):
    v = _clean(v)
    if v is not None and not re.search(r"linkedin\.com/", v, re.I):
        raise ValueError("LinkedIn must be a linkedin.com address")
    return v


# Blank text means not mentioned and is stored as null.
Text = Annotated[str | None, AfterValidator(_clean)]
Email = Annotated[str | None, AfterValidator(_email)]
Phone = Annotated[str | None, AfterValidator(_phone)]
LinkedIn = Annotated[str | None, AfterValidator(_linkedin)]
Visa = Annotated[str | None, AfterValidator(check_visa)]
Country = Annotated[str | None, AfterValidator(normalize_country)]


class CandidateCreate(BaseModel):
    full_name: Text = Field(default=None, max_length=200)
    email: Email = Field(default=None, max_length=255)
    phone: Phone = Field(default=None, max_length=50)
    linkedin_url: LinkedIn = Field(default=None, max_length=500)
    location: Text = Field(default=None, max_length=200)
    country: Country = Field(default=None, max_length=100)
    visa_status: Visa = Field(default=None, max_length=100)
    rate: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    rate_unit: Literal["hour", "year"] | None = None
    total_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    status: str = Field(default="New", max_length=50)
    current_requirement: Text = Field(default=None, max_length=300)
    availability: Text = Field(default=None, max_length=200)


class CandidateUpdate(BaseModel):
    full_name: Text = Field(default=None, max_length=200)
    email: Email = Field(default=None, max_length=255)
    phone: Phone = Field(default=None, max_length=50)
    linkedin_url: LinkedIn = Field(default=None, max_length=500)
    location: Text = Field(default=None, max_length=200)
    city: Text = Field(default=None, max_length=100)
    state: Text = Field(default=None, max_length=100)
    country: Country = Field(default=None, max_length=100)
    visa_status: Visa = Field(default=None, max_length=100)
    rate: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    rate_unit: Literal["hour", "year"] | None = None
    total_experience_years: Decimal | None = Field(default=None, ge=0, le=60)
    status: str | None = Field(default=None, max_length=50)
    current_requirement: Text = Field(default=None, max_length=300)
    availability: Text = Field(default=None, max_length=200)
    recruiter_id: int | None = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    location: str | None
    country: str | None
    availability: str | None
    visa_status: str | None
    rate: Decimal | None
    rate_unit: str | None
    total_experience_years: Decimal | None
    status: str
    current_requirement: str | None
    recruiter_id: int | None
    parse_status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime