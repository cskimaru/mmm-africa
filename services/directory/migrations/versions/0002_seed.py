"""seed the MMM family and the 2026 convention

Revision ID: 0002
Revises: 0001
"""

from datetime import UTC, date, datetime

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INTL = "00000000000000000000000000000001"
AFRICA = "00000000000000000000000000000002"
KENYA = "00000000000000000000000000000003"
CONVENTION_2026 = "00000000000000000000000000000101"


def upgrade() -> None:
    now = datetime.now(UTC)
    units = sa.table(
        "units",
        *(sa.column(c) for c in (
            "id", "slug", "name", "short_name", "level", "parent_id", "country_code", "city", "status",
            "website_url", "email", "phone", "summary", "position", "hidden", "created_at", "updated_at",
        )),
    )
    base = {"country_code": "", "city": "", "status": "established", "email": "", "phone": "", "hidden": False,
            "created_at": now, "updated_at": now}
    op.bulk_insert(units, [
        {**base, "id": INTL, "slug": "mmm-international", "name": "Medical Missionary Movement International",
         "short_name": "MMM International", "level": "international", "parent_id": None,
         "website_url": "https://medicalmissionarymovement.org/", "position": 1,
         "summary": "The worldwide umbrella over every Medical Missionary Movement chapter."},
        {**base, "id": AFRICA, "slug": "africa", "name": "MMM African Chapter", "short_name": "MMM Africa",
         "level": "continental", "parent_id": INTL, "website_url": "", "position": 1,
         "summary": "Unites the national MMM chapters across Africa in health ministry and the Gospel commission."},
        {**base, "id": KENYA, "slug": "kenya", "name": "MMM Kenya Chapter", "short_name": "MMMK",
         "level": "national", "parent_id": AFRICA, "country_code": "ke", "city": "Nairobi",
         "website_url": "https://mmmkenya.org", "email": "info@mmmkenya.org", "phone": "+254 727 279 257",
         "position": 10,
         "summary": "Medical outreach camps, discipleship and training, and health evangelism across Kenya. "
                    "Host of the 2026 African Chapter Annual Convention."},
    ])

    events = sa.table(
        "events",
        *(sa.column(c) for c in (
            "id", "slug", "title", "theme", "scripture", "starts_on", "ends_on", "venue", "location",
            "host_unit_id", "summary", "recap", "register_url", "hidden", "created_at", "updated_at",
        )),
    )
    op.bulk_insert(events, [{
        "id": CONVENTION_2026, "slug": "convention-2026",
        "title": "MMM African Chapter Annual Convention 2026",
        "theme": "We Have Seen His Star", "scripture": "Matthew 2:2",
        "starts_on": date(2026, 9, 27), "ends_on": date(2026, 10, 4),
        "venue": "Watamu Adventist Beach Resort", "location": "Watamu, Kenya", "host_unit_id": KENYA,
        "summary": "Delegates from across Africa gathered for a week of worship, fellowship and renewal, "
                   "presented with the Seventh-day Adventist Church and ASI.",
        "recap": "Thank you to every delegate, speaker, volunteer and partner who joined us in Watamu, and to "
                 "the MMM Kenya Chapter for hosting. We look forward to serving together again at the next "
                 "Annual Convention.",
        "register_url": "", "hidden": False, "created_at": now, "updated_at": now,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM events WHERE id = :i").bindparams(i=CONVENTION_2026))
    for i in (KENYA, AFRICA, INTL):
        op.execute(sa.text("DELETE FROM units WHERE id = :i").bindparams(i=i))
