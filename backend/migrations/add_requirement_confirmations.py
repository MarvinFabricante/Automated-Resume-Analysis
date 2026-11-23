"""Persist clarification evidence. Run: python -m migrations.add_requirement_confirmations."""
import asyncio
from sqlalchemy import text
from app.utils.database import engine
from migrations.add_job_scoring_weights import _column_exists


async def upgrade(conn=None):
    async def apply(connection):
        for column in ("clarification_responses", "requirement_evaluations"):
            if not await _column_exists(connection, "job_applications", column):
                await connection.execute(text(f"ALTER TABLE job_applications ADD COLUMN {column} JSON"))
    if conn is not None:
        await apply(conn)
    else:
        async with engine.begin() as connection:
            await apply(connection)


if __name__ == "__main__":
    asyncio.run(upgrade())
