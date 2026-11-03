from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Level = Literal["international", "continental", "national"]
UnitStatus = Literal["established", "forming"]
Topic = Literal["general", "start_chapter", "partner", "volunteer"]
SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def _url(v: str) -> str:
    v = v.strip()
    if v and not v.startswith(("https://", "http://")):
        raise ValueError("Links must start with https://")
    return v


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Units ----


class UnitIn(BaseModel):
    slug: str = Field(min_length=2, max_length=60, pattern=SLUG)
    name: str = Field(min_length=2, max_length=120)
    short_name: str = Field("", max_length=30)
    level: Level
    parent_id: str | None = None
    country_code: str = Field("", max_length=2)
    city: str = Field("", max_length=80)
    status: UnitStatus = "established"
    website_url: str = Field("", max_length=300)
    email: str = Field("", max_length=200)
    phone: str = Field("", max_length=40)
    summary: str = Field("", max_length=4000)
    position: int = 100
    hidden: bool = False

    @field_validator("website_url")
    @classmethod
    def _u(cls, v: str) -> str:
        return _url(v)

    @field_validator("country_code")
    @classmethod
    def _cc(cls, v: str) -> str:
        v = v.strip().lower()
        if v and (len(v) != 2 or not v.isalpha()):
            raise ValueError("Use the two-letter country code, e.g. ke for Kenya.")
        return v


class UnitPatch(BaseModel):
    slug: str | None = Field(None, min_length=2, max_length=60, pattern=SLUG)
    name: str | None = Field(None, min_length=2, max_length=120)
    short_name: str | None = Field(None, max_length=30)
    parent_id: str | None = None
    country_code: str | None = Field(None, max_length=2)
    city: str | None = Field(None, max_length=80)
    status: UnitStatus | None = None
    website_url: str | None = Field(None, max_length=300)
    email: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=40)
    summary: str | None = Field(None, max_length=4000)
    position: int | None = None
    hidden: bool | None = None

    @field_validator("website_url")
    @classmethod
    def _u(cls, v: str | None) -> str | None:
        return None if v is None else _url(v)


class OfficerOut(_Out):
    id: str
    unit_id: str
    name: str
    role: str
    term: str
    email: str
    position: int


class UnitOut(_Out):
    id: str
    slug: str
    name: str
    short_name: str
    level: str
    parent_id: str | None
    country_code: str
    city: str
    status: str
    website_url: str
    email: str
    phone: str
    summary: str
    position: int
    hidden: bool


class UnitDetailOut(UnitOut):
    officers: list[OfficerOut] = []
    parent: UnitOut | None = None
    children: list[UnitOut] = []


class StructureOut(BaseModel):
    """The whole family, top to bottom, for drawing the structure diagram and the chapter map."""

    international: list[UnitOut]
    continental: list[UnitOut]
    national: list[UnitOut]


# ---- Officers ----


class OfficerIn(BaseModel):
    unit_id: str
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(min_length=2, max_length=80)
    term: str = Field("", max_length=40)
    email: str = Field("", max_length=200)
    position: int = 100


class OfficerPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    role: str | None = Field(None, min_length=2, max_length=80)
    term: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=200)
    position: int | None = None


# ---- Events ----


class EventIn(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=SLUG)
    title: str = Field(min_length=2, max_length=160)
    theme: str = Field("", max_length=160)
    scripture: str = Field("", max_length=60)
    starts_on: date
    ends_on: date
    venue: str = Field("", max_length=160)
    location: str = Field("", max_length=160)
    host_unit_id: str | None = None
    summary: str = Field("", max_length=4000)
    recap: str = Field("", max_length=4000)
    register_url: str = Field("", max_length=300)
    hidden: bool = False

    @field_validator("register_url")
    @classmethod
    def _u(cls, v: str) -> str:
        return _url(v)

    @model_validator(mode="after")
    def _dates(self) -> "EventIn":
        if self.ends_on < self.starts_on:
            raise ValueError("The end date must be on or after the start date.")
        return self


class EventPatch(BaseModel):
    slug: str | None = Field(None, min_length=2, max_length=80, pattern=SLUG)
    title: str | None = Field(None, min_length=2, max_length=160)
    theme: str | None = Field(None, max_length=160)
    scripture: str | None = Field(None, max_length=60)
    starts_on: date | None = None
    ends_on: date | None = None
    venue: str | None = Field(None, max_length=160)
    location: str | None = Field(None, max_length=160)
    host_unit_id: str | None = None
    summary: str | None = Field(None, max_length=4000)
    recap: str | None = Field(None, max_length=4000)
    register_url: str | None = Field(None, max_length=300)
    hidden: bool | None = None

    @field_validator("register_url")
    @classmethod
    def _u(cls, v: str | None) -> str | None:
        return None if v is None else _url(v)


class EventOut(_Out):
    id: str
    slug: str
    title: str
    theme: str
    scripture: str
    starts_on: date
    ends_on: date
    venue: str
    location: str
    host_unit_id: str | None
    host: UnitOut | None = None
    summary: str
    recap: str
    register_url: str
    hidden: bool
    # "upcoming", "happening" or "ended", worked out from today's date.
    state: str = "upcoming"


# ---- Contact messages ----


class MessageIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    country: str = Field("", max_length=80)
    topic: Topic = "general"
    body: str = Field(min_length=5, max_length=4000)
    # Hidden form field that people never fill in; bots often do.
    website: str = Field("", max_length=200)


class MessageOut(_Out):
    id: str
    name: str
    email: str
    country: str
    topic: str
    body: str
    created_at: datetime
    handled_at: datetime | None
