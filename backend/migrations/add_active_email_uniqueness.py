"""Reversible normalized active-email index; does not modify account data.

Run: python -m migrations.add_active_email_uniqueness [--downgrade]
Existing exact-email uniqueness remains: recovery anonymizes before replacement.
Upgrade fails safely if legacy active rows collide; resolve those explicitly.
"""
import argparse
import asyncio
from sqlalchemy import text
from app.utils.database import engine


async def upgrade(connection):
    await connection.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_active_normalized_email
        ON users (LOWER(TRIM(email)))
        WHERE is_deactivated IS NOT TRUE AND is_anonymized IS NOT TRUE
    """))


async def downgrade(connection):
    await connection.execute(text("DROP INDEX IF EXISTS uq_users_active_normalized_email"))


async def main(reverse=False):
    async with engine.begin() as connection:
        await (downgrade(connection) if reverse else upgrade(connection))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downgrade", action="store_true")
    asyncio.run(main(parser.parse_args().downgrade))
