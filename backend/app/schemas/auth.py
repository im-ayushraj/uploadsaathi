from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Indian mobile numbers: 10 digits starting 6-9. Accepts optional +91 / 0 prefix.
MOBILE_PATTERN = r"^[6-9]\d{9}$"


def normalise_mobile(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    mobile: str
    # bcrypt caps at 72 bytes; keep the schema limit below that.
    password: str = Field(min_length=8, max_length=64)

    @field_validator("mobile")
    @classmethod
    def _mobile(cls, v: str) -> str:
        import re

        m = normalise_mobile(v)
        if not re.match(MOBILE_PATTERN, m):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return m

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return " ".join(v.split())


class LoginRequest(BaseModel):
    """identifier is either the email address or the 10-digit mobile number."""

    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=64)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    mobile: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
