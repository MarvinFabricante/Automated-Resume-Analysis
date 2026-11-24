"""
Idempotent, reversible migration for Mariwasa Recruitment lifecycle, privacy,
retention, reactivation, and multi-application rules.

Adds columns:
  - job_descriptions: status, closed_at, archived_at
  - shortlist_rosters: non_shortlisted_action, is_finalized, finalized_at
  - users: is_deactivated, deactivated_at, token_version, is_anonymized,
           anonymized_at, anonymized_token, email_hash
  - job_applications: resolved_at, messaging_closed_at, hold_reason,
                      is_anonymized, anonymized_token, email_hash

Creates tables:
  - account_otps
  - retention_run_logs

Never runs any bulk status changes or data purges on existing records.

Usage:
  python -m migrations.add_recruitment_lifecycle_rules             # apply upgrade
  python -m migrations.add_recruitment_lifecycle_rules --downgrade # revert changes
"""
import argparse
import asyncio
from sqlalchemy import text

from app.utils.database import engine


# (table, column, pg_type_with_default, sqlite_type_with_default)
NEW_COLUMNS = [
    # Job opening lifecycle
    ("job_descriptions", "status", "VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'", "TEXT DEFAULT 'ACTIVE'"),
    ("job_descriptions", "closed_at", "TIMESTAMP", "TIMESTAMP"),
    ("job_descriptions", "archived_at", "TIMESTAMP", "TIMESTAMP"),
    # Shortlist roster non-shortlisted policy
    ("shortlist_rosters", "non_shortlisted_action", "VARCHAR(64) NOT NULL DEFAULT 'keep_under_review'", "TEXT DEFAULT 'keep_under_review'"),
    ("shortlist_rosters", "is_finalized", "BOOLEAN NOT NULL DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
    ("shortlist_rosters", "finalized_at", "TIMESTAMP", "TIMESTAMP"),
    # User deactivation, token invalidation & anonymization
    ("users", "is_deactivated", "BOOLEAN NOT NULL DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
    ("users", "deactivated_at", "TIMESTAMP", "TIMESTAMP"),
    ("users", "token_version", "INTEGER NOT NULL DEFAULT 0", "INTEGER DEFAULT 0"),
    ("users", "is_anonymized", "BOOLEAN NOT NULL DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
    ("users", "anonymized_at", "TIMESTAMP", "TIMESTAMP"),
    ("users", "anonymized_token", "VARCHAR(64)", "TEXT"),
    ("users", "email_hash", "VARCHAR(128)", "TEXT"),
    # Application resolution, messaging closure, hold & anonymization
    ("job_applications", "resolved_at", "TIMESTAMP", "TIMESTAMP"),
    ("job_applications", "messaging_closed_at", "TIMESTAMP", "TIMESTAMP"),
    ("job_applications", "hold_reason", "TEXT", "TEXT"),
    ("job_applications", "is_anonymized", "BOOLEAN NOT NULL DEFAULT FALSE", "BOOLEAN DEFAULT 0"),
    ("job_applications", "anonymized_token", "VARCHAR(64)", "TEXT"),
    ("job_applications", "email_hash", "VARCHAR(128)", "TEXT"),
]

NEW_INDEXES = [
    ("idx_job_descriptions_status", "job_descriptions", "status"),
    ("idx_users_email_hash", "users", "email_hash"),
    ("idx_job_applications_resolved_at", "job_applications", "resolved_at"),
    ("idx_job_applications_is_anonymized", "job_applications", "is_anonymized"),
    ("idx_job_applications_email_hash", "job_applications", "email_hash"),
]


async def _table_exists(conn, table: str) -> bool:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        res = await conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :t"),
            {"t": table},
        )
        return res.first() is not None
    res = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t"
        ),
        {"t": table},
    )
    return res.first() is not None


async def _column_exists(conn, table: str, column: str) -> bool:
    if not await _table_exists(conn, table):
        return False
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
    """Apply schema additions idempotently without modifying existing applicant data."""
    async def _apply(c):
        dialect = c.dialect.name

        for table, column, pg_type, sqlite_type in NEW_COLUMNS:
            if not await _table_exists(c, table):
                continue
            if not await _column_exists(c, table, column):
                col_def = sqlite_type if dialect == "sqlite" else pg_type
                await c.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))

        # Backfill NULL job_descriptions.status from is_active only where status is NULL
        if await _column_exists(c, "job_descriptions", "status"):
            if dialect == "sqlite":
                await c.execute(
                    text(
                        "UPDATE job_descriptions "
                        "SET status = CASE WHEN is_active = 0 THEN 'ARCHIVED' ELSE 'ACTIVE' END "
                        "WHERE status IS NULL OR status = ''"
                    )
                )
            else:
                await c.execute(
                    text(
                        "UPDATE job_descriptions "
                        "SET status = CASE WHEN is_active = FALSE THEN 'ARCHIVED' ELSE 'ACTIVE' END "
                        "WHERE status IS NULL OR status = ''"
                    )
                )

        # Create account_otps table
        if dialect == "sqlite":
            await c.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS account_otps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        code_hash TEXT NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 5,
                        expires_at TIMESTAMP NOT NULL,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            await c.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS retention_run_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dry_run BOOLEAN NOT NULL DEFAULT 1,
                        retention_months INTEGER NOT NULL DEFAULT 12,
                        triggered_by TEXT NOT NULL DEFAULT 'scheduled',
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        candidates_evaluated INTEGER NOT NULL DEFAULT 0,
                        candidates_anonymized INTEGER NOT NULL DEFAULT 0,
                        applications_anonymized INTEGER NOT NULL DEFAULT 0,
                        files_deleted INTEGER NOT NULL DEFAULT 0,
                        skipped_active INTEGER NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'COMPLETED',
                        details TEXT
                    )
                    """
                )
            )
        else:
            await c.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS account_otps (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        purpose VARCHAR(64) NOT NULL,
                        code_hash VARCHAR(128) NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 5,
                        expires_at TIMESTAMP NOT NULL,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
            await c.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS retention_run_logs (
                        id SERIAL PRIMARY KEY,
                        dry_run BOOLEAN NOT NULL DEFAULT TRUE,
                        retention_months INTEGER NOT NULL DEFAULT 12,
                        triggered_by VARCHAR(100) NOT NULL DEFAULT 'scheduled',
                        started_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP,
                        candidates_evaluated INTEGER NOT NULL DEFAULT 0,
                        candidates_anonymized INTEGER NOT NULL DEFAULT 0,
                        applications_anonymized INTEGER NOT NULL DEFAULT 0,
                        files_deleted INTEGER NOT NULL DEFAULT 0,
                        skipped_active INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
                        details JSON
                    )
                    """
                )
            )

        await c.execute(text("CREATE INDEX IF NOT EXISTS idx_account_otps_email ON account_otps (email)"))

        for idx_name, table, col in NEW_INDEXES:
            if await _column_exists(c, table, col):
                await c.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"))

    if conn is not None:
        await _apply(conn)
    else:
        async with engine.begin() as c:
            await _apply(c)


async def downgrade(conn=None) -> None:
    """Revert schema additions safely and idempotently."""
    async def _revert(c):
        dialect = c.dialect.name

        # Drop tables first
        await c.execute(text("DROP TABLE IF EXISTS retention_run_logs"))
        await c.execute(text("DROP TABLE IF EXISTS account_otps"))

        # Drop any indexes on columns we are about to drop (required by SQLite)
        for idx_name, table, col in NEW_INDEXES:
            await c.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
            # Also drop SQLAlchemy auto-named ix_<table>_<col> if created via metadata.create_all
            await c.execute(text(f"DROP INDEX IF EXISTS ix_{table}_{col}"))

        for table, column, _, _ in reversed(NEW_COLUMNS):
            if await _column_exists(c, table, column):
                if dialect == "postgresql":
                    await c.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"))
                else:
                    await c.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))

    if conn is not None:
        await _revert(conn)
    else:
        async with engine.begin() as c:
            await _revert(c)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Mariwasa recruitment lifecycle rules schema.")
    parser.add_argument("--downgrade", action="store_true", help="Revert the migration.")
    args = parser.parse_args()

    if args.downgrade:
        asyncio.run(downgrade())
        print("Downgraded: reverted recruitment lifecycle rules schema additions.")
    else:
        asyncio.run(upgrade())
        print("Upgraded: ensured recruitment lifecycle rules schema additions.")


if __name__ == "__main__":
    main()
