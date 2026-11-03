"""The MMM family structure, its leaders, shared events and contact messages.

The structure follows the Seventh-day Adventist pattern:

    international  ~ General Conference   (MMM International)
    continental    ~ Division             (MMM African Chapter: this site)
    national       ~ Union / Conference   (e.g. MMM Kenya Chapter, MMMK)

Each unit keeps its own leadership and its own finances. This service stores
no financial data at all: only who the units are, who leads them, and the
activities they share.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mmm_common.db import Base, IdMixin, TimestampMixin, utcnow

LEVELS = ("international", "continental", "national")
UNIT_STATUSES = ("established", "forming")
TOPICS = ("general", "start_chapter", "partner", "volunteer")


class Unit(IdMixin, TimestampMixin, Base):
    __tablename__ = "units"

    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(30), default="")
    level: Mapped[str] = mapped_column(String(20), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="established")
    website_url: Mapped[str] = mapped_column(String(300), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=100)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class Officer(IdMixin, TimestampMixin, Base):
    __tablename__ = "officers"

    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80))
    term: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    position: Mapped[int] = mapped_column(Integer, default=100)


class Event(IdMixin, TimestampMixin, Base):
    __tablename__ = "events"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    theme: Mapped[str] = mapped_column(String(160), default="")
    scripture: Mapped[str] = mapped_column(String(60), default="")
    starts_on: Mapped[date] = mapped_column(Date, index=True)
    ends_on: Mapped[date] = mapped_column(Date)
    venue: Mapped[str] = mapped_column(String(160), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    host_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    # Shown after the event ends, e.g. a thank-you to attendees.
    recap: Mapped[str] = mapped_column(Text, default="")
    # Registration usually lives on the host chapter's own site.
    register_url: Mapped[str] = mapped_column(String(300), default="")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(IdMixin, Base):
    __tablename__ = "messages"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(80), default="")
    topic: Mapped[str] = mapped_column(String(20), default="general")
    body: Mapped[str] = mapped_column(Text)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handled_by: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_log"

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(64), default="")
