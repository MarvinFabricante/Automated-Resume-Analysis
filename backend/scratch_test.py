import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine('postgresql+asyncpg://postgres:passwordnamin@localhost:5432/automated_resume_db')
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text('SELECT id, email, password, role FROM users LIMIT 10;'))
            for row in res:
                print(row)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
