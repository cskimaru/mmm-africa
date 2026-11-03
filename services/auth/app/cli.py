"""Administrative commands, run on the server or computer that hosts the site.

    python -m app.cli create-owner --email you@example.com --name "Secretary"
    python -m app.cli reset-password --email you@example.com

The password is read from the OWNER_PASSWORD environment variable, or asked for twice.
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select, update

from mmm_common.db import Database, utcnow

from .config import get_settings
from .models import RefreshToken, User
from .passwords import hash_password


def password_problem(password: str, email: str) -> str | None:
    settings = get_settings()
    if len(password) < settings.min_password_length:
        return f"Password must be at least {settings.min_password_length} characters."
    if email.split("@")[0].lower() in password.lower():
        return "The password shouldn't contain your email address."
    return None


def ask_password() -> str | None:
    if os.environ.get("OWNER_PASSWORD"):
        return os.environ["OWNER_PASSWORD"]
    first = getpass.getpass("Choose a password: ")
    if getpass.getpass("Type it again: ") != first:
        print("The two passwords didn't match. Nothing was changed; run the command again.", file=sys.stderr)
        return None
    return first


async def create_owner(email: str, name: str, password: str) -> int:
    problem = password_problem(password, email)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    settings = get_settings()
    db = Database(settings.database_url)
    async with db.sessionmaker() as s:
        existing = (await s.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if existing:
            existing.roles = ",".join(sorted(set(existing.role_list) | {"owner"}))
            existing.is_active = True
            print(f"{email} already had an account; it is now an owner. The password was NOT changed")
            print("(use: make reset-password email=...).")
        else:
            s.add(User(email=email.lower(), display_name=name, password_hash=hash_password(password), roles="owner"))
            print(f"Owner account created for {email}. Sign in at /officers.")
        await s.commit()
    await db.dispose()
    return 0


async def reset_password(email: str, password: str) -> int:
    problem = password_problem(password, email)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    settings = get_settings()
    db = Database(settings.database_url)
    async with db.sessionmaker() as s:
        user = (await s.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user is None:
            print(f"There is no account for {email}. Check the spelling, or create it with make create-owner.")
            await db.dispose()
            return 1
        user.password_hash = hash_password(password)
        user.failed_logins = 0
        user.locked_until = None
        user.is_active = True
        # Sign the account out everywhere, so only the new password works from now on.
        await s.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
        await s.commit()
        print(f"Password changed for {email}, and any sign-in lock cleared. Sign in at /officers.")
    await db.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-owner")
    c.add_argument("--email", required=True)
    c.add_argument("--name", required=True)
    r = sub.add_parser("reset-password")
    r.add_argument("--email", required=True)
    args = parser.parse_args()
    pw = ask_password()
    if pw is None:
        return 2
    if args.cmd == "create-owner":
        return asyncio.run(create_owner(args.email, args.name, pw))
    return asyncio.run(reset_password(args.email, pw))


if __name__ == "__main__":
    raise SystemExit(main())
