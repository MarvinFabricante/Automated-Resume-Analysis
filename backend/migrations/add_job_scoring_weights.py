"""
Idempotent, reversible migration for per-job scoring weights and weight snapshots.

Adds:
  - job_descriptions.scoring_weights (JSON/TEXT, nullable; NULL = use global default)
  - job_applications.applied_weights (JSON/TEXT, nullable; weight snapshot per score)

Usage:
  python -m migrations.add_job_scoring_weights             # apply upgrade
  python -m migrations.add_job_scoring_weights --downgrade # revert changes
"""
import argparse
import asyncio
from sqlalchemy import text

from app.utils.database import engine


async def _column_exists(conn, table: str, column: str) -> bool:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        res = await conn.execute(text(f"PRAGMA table_info({table})"))
        return column in {row[1] for row in res.fetchall()}
    res = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return res.first() is not None


async def upgrade(conn=None) -> None:
    """Add scoring_weights to job_descriptions and applied_weights to job_applications."""
    async def _apply(c):
        dialect = c.dialect.name
        col_type = "TEXT" if dialect == "sqlite" else "JSON"
        if not await _column_exists(c, "job_descriptions", "scoring_weights"):
            await c.execute(text(f"ALTER TABLE job_descriptions ADD COLUMN scoring_weights {col_type}"))
        if not await _column_exists(c, "job_applications", "applied_weights"):
            await c.execute(text(f"ALTER TABLE job_applications ADD COLUMN applied_weights {col_type}"))

    if conn is not None:
        await _apply(conn)
    else:
        async with engine.begin() as c:
            await _apply(c)


async def downgrade(conn=None) -> None:
    """Remove scoring_weights from job_descriptions and applied_weights from job_applications."""
    async def _revert(c):
        if await _column_exists(c, "job_descriptions", "scoring_weights"):
            await c.execute(text("ALTER TABLE job_descriptions DROP COLUMN scoring_weights"))
        if await _column_exists(c, "job_applications", "applied_weights"):
            await c.execute(text("ALTER TABLE job_applications DROP COLUMN applied_weights"))

    if conn is not None:
        await _revert(conn)
    else:
        async with engine.begin() as c:
            await _revert(c)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate per-job scoring weights columns.")
    parser.add_argument("--downgrade", action="store_true", help="Revert the migration.")
    args = parser.parse_args()

    if args.downgrade:
        asyncio.run(downgrade())
        print("Downgraded: removed job_descriptions.scoring_weights and job_applications.applied_weights.")
    else:
        asyncio.run(upgrade())
        print("Upgraded: ensured job_descriptions.scoring_weights and job_applications.applied_weights.")


if __name__ == "__main__":
    main()
