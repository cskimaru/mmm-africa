"""The MMM family structure, its leaders, shared events, contact messages and website content.

Three levels: international (MMM International), continental (the MMM African Chapter, this site) and
national (e.g. MMM Kenya Chapter, MMMK). This service stores no financial data.
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


class Setting(Base):
    """One piece of editable website text or a site option, by key (e.g. "home.hero_title").

    The web service holds the default for every key; a row here replaces that default.
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Page(IdMixin, TimestampMixin, Base):
    """A page the officers write themselves, e.g. News, Programmes or Give."""

    __tablename__ = "pages"

    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    in_menu: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=100)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
