import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from mmm_common.security import ALL_ROLES


def _roles(v: list[str]) -> list[str]:
    clean = sorted({r.strip().lower() for r in v})
    bad = [r for r in clean if r not in ALL_ROLES]
    if bad:
        raise ValueError(f"Unknown role: {', '.join(bad)}")
    if not clean:
        raise ValueError("Choose at least one role.")
    return clean


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    roles: list[str]
    is_active: bool
    last_login_at: datetime | None = None
    phone: str = ""
    position: str = ""
    country: str = ""


class InviteIn(BaseModel):
    email: EmailStr
    display_name: str = Field(default="", max_length=120)
    roles: list[str] = Field(default_factory=lambda: ["editor"])

    _v = field_validator("roles")(_roles)


class InviteOut(BaseModel):
    id: str
    email: str
    display_name: str
    roles: list[str]
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    invite_url: str | None = None


class AcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(max_length=256)


class InviteInfoOut(BaseModel):
    email: str
    display_name: str
    roles: list[str]


class UserPatch(BaseModel):
    roles: list[str] | None = None
    is_active: bool | None = None

    @field_validator("roles")
    @classmethod
    def _v(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _roles(v)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


PHONE = re.compile(r"^\+[1-9]\d{7,14}$")


def clean_phone(v: str) -> str:
    """Accept '+254 712 345 678', '+254-712-345678' or '(+254) 712345678'; store '+254712345678'."""
    digits = re.sub(r"[\s\-().]", "", v)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not PHONE.match(digits):
        raise ValueError("Write the phone number with the country code, for example +254 712 345 678.")
    return digits


class AccessRequestIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(max_length=40)
    position: str = Field(min_length=2, max_length=120)
    country: str = Field(min_length=2, max_length=80)
    password: str = Field(max_length=256)
    # Hidden form field that people never fill in; bots often do.
    website: str = Field("", max_length=200)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return clean_phone(v)


class AccessRequestOut(BaseModel):
    id: str
    email: str
    display_name: str
    phone: str
    position: str
    country: str
    status: str
    created_at: datetime
    decided_at: datetime | None = None


class ApproveIn(BaseModel):
    roles: list[str] = Field(default_factory=lambda: ["editor"])

    _v = field_validator("roles")(_roles)
