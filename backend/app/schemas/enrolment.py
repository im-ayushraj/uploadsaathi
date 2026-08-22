from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["male", "female", "transgender"]


class PersonalDetails(BaseModel):
    """Synthetic demo details. No Aadhaar number is collected or stored."""

    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    gender: Gender
    guardian_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    mobile: str | None = Field(default=None, max_length=15)

    @field_validator("date_of_birth")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v.year < 1900:
            raise ValueError("Enter a valid date of birth")
        return v

    @field_validator("full_name", "guardian_name")
    @classmethod
    def _tidy(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v else v


class Address(BaseModel):
    address_line1: str = Field(min_length=3, max_length=160)
    address_line2: str | None = Field(default=None, max_length=160)
    landmark: str | None = Field(default=None, max_length=120)
    village_town_city: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    pincode: str = Field(pattern=r"^[1-9]\d{5}$")


class EnrolmentCreate(BaseModel):
    applicant_type: str = Field(min_length=2, max_length=40)
    portal_id: str = Field(default="aadhaar", max_length=40)


class EnrolmentUpdate(BaseModel):
    """Partial update — the wizard saves one step at a time."""

    applicant_type: str | None = Field(default=None, max_length=40)
    personal_details: PersonalDetails | None = None
    address: Address | None = None


class EnrolmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portal_id: str
    applicant_type: str
    status: str
    personal_details: PersonalDetails | None = None
    address: Address | None = None
    reference_code: str | None = None
    prepared_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EnrolmentProgress(BaseModel):
    """Which wizard steps are done — drives the UI without hardcoding rules in React."""

    applicant_type: bool
    personal_details: bool
    address: bool
    documents: bool
    documents_required: list[str] = []
    documents_accepted: list[str] = []
    can_prepare: bool


class EnrolmentDetail(EnrolmentOut):
    progress: EnrolmentProgress
