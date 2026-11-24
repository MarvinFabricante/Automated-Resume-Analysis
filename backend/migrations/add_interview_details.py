"""Run from backend: python -m migrations.add_interview_details [--downgrade].

Re-runnable; does not modify application statuses or guess historical interview types.
Downgrade removes only the three new fields (location/link already existed).
"""
import argparse
import asyncio
from sqlalchemy import text
from app.utils.database import engine
from migrations.add_job_scoring_weights import _column_exists

COLUMNS = {'interview_type': "VARCHAR DEFAULT 'Not specified'", 'instructions': 'TEXT', 'platform': 'VARCHAR'}


async def upgrade(conn=None):
    async def apply(c):
        for name, definition in COLUMNS.items():
            if not await _column_exists(c, 'interviews', name):
                await c.execute(text(f'ALTER TABLE interviews ADD COLUMN {name} {definition}'))
    if conn is not None:
        await apply(conn)
    else:
        async with engine.begin() as c:
            await apply(c)


async def downgrade(conn=None):
    async def apply(c):
        for name in reversed(COLUMNS):
            if await _column_exists(c, 'interviews', name):
                await c.execute(text(f'ALTER TABLE interviews DROP COLUMN {name}'))
    if conn is not None:
        await apply(conn)
    else:
        async with engine.begin() as c:
            await apply(c)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downgrade', action='store_true')
    asyncio.run(downgrade() if parser.parse_args().downgrade else upgrade())
