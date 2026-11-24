"""
Idempotent, reversible migration for two-way HR-initiated application chat threads.

Adds:
  - application_threads table (one thread per application_id)
  - message_reports table (applicant report-a-message)
  - archived_threads table (per-user thread archiving)
  - messages.thread_id, attachment_url, attachment_name, attachment_type,
    attachment_size, is_reported, email_digest_sent_at

Usage:
  python -m migrations.add_two_way_chat_threads
  python -m migrations.add_two_way_chat_threads --downgrade
"""
import argparse
import asyncio
from sqlalchemy import text
from app.utils.database import engine
from migrations.add_job_scoring_weights import _column_exists


MESSAGE_COLUMNS = {
    "thread_id": "INTEGER",
    "attachment_url": "VARCHAR",
    "attachment_name": "VARCHAR",
    "attachment_type": "VARCHAR",
    "attachment_size": "INTEGER",
    "is_reported": "BOOLEAN DEFAULT FALSE",
    "email_digest_sent_at": "TIMESTAMP",
}


async def upgrade(conn=None) -> None:
    async def _apply(c):
        dialect = c.dialect.name
        if dialect == "sqlite":
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS application_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL UNIQUE REFERENCES job_applications(id) ON DELETE CASCADE,
                    candidate_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    started_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_message_at TIMESTAMP,
                    last_message_preview VARCHAR(300)
                )
            """))
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS message_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    thread_id INTEGER REFERENCES application_threads(id) ON DELETE CASCADE,
                    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'OPEN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS archived_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    thread_id INTEGER NOT NULL REFERENCES application_threads(id) ON DELETE CASCADE,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_user_thread_archive UNIQUE (user_id, thread_id)
                )
            """))
        else:
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS application_threads (
                    id SERIAL PRIMARY KEY,
                    application_id INTEGER NOT NULL UNIQUE REFERENCES job_applications(id) ON DELETE CASCADE,
                    candidate_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    started_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_message_at TIMESTAMP WITH TIME ZONE,
                    last_message_preview VARCHAR(300)
                )
            """))
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS message_reports (
                    id SERIAL PRIMARY KEY,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    thread_id INTEGER REFERENCES application_threads(id) ON DELETE CASCADE,
                    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'OPEN',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await c.execute(text("""
                CREATE TABLE IF NOT EXISTS archived_threads (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    thread_id INTEGER NOT NULL REFERENCES application_threads(id) ON DELETE CASCADE,
                    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_user_thread_archive UNIQUE (user_id, thread_id)
                )
            """))

        for col_name, col_def in MESSAGE_COLUMNS.items():
            if not await _column_exists(c, "messages", col_name):
                if dialect == "sqlite":
                    sqlite_def = (
                        "TEXT" if ("VARCHAR" in col_def or "TIMESTAMP" in col_def)
                        else ("INTEGER" if "INTEGER" in col_def else col_def)
                    )
                    await c.execute(text(f"ALTER TABLE messages ADD COLUMN {col_name} {sqlite_def}"))
                else:
                    pg_def = "TIMESTAMP WITH TIME ZONE" if col_def == "TIMESTAMP" else col_def
                    await c.execute(text(f"ALTER TABLE messages ADD COLUMN IF NOT EXISTS {col_name} {pg_def}"))

        for idx_ddl in [
            "CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages (thread_id)",
            "CREATE INDEX IF NOT EXISTS idx_application_threads_candidate_id ON application_threads (candidate_id)",
            "CREATE INDEX IF NOT EXISTS idx_application_threads_last_message_at ON application_threads (last_message_at)",
            "CREATE INDEX IF NOT EXISTS idx_message_reports_message_id ON message_reports (message_id)",
        ]:
            try:
                await c.execute(text(idx_ddl))
            except Exception:
                pass

    if conn is not None:
        await _apply(conn)
    else:
        async with engine.begin() as c:
            await _apply(c)


async def downgrade(conn=None) -> None:
    async def _revert(c):
        for col_name in reversed(list(MESSAGE_COLUMNS.keys())):
            if await _column_exists(c, "messages", col_name):
                await c.execute(text(f"ALTER TABLE messages DROP COLUMN {col_name}"))
        await c.execute(text("DROP TABLE IF EXISTS archived_threads"))
        await c.execute(text("DROP TABLE IF EXISTS message_reports"))
        await c.execute(text("DROP TABLE IF EXISTS application_threads"))

    if conn is not None:
        await _revert(conn)
    else:
        async with engine.begin() as c:
            await _revert(c)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downgrade", action="store_true")
    asyncio.run(downgrade() if parser.parse_args().downgrade else upgrade())
