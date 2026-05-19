import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def update_job_table():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("Updating job_descriptions table with education and experience requirements fields...")
        
        commands = [
            "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS education_requirements VARCHAR;",
            "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS experience_requirements VARCHAR;"
        ]
        
        for command in commands:
            try:
                await conn.execute(text(command))
                print(f"Executed: {command}")
            except Exception as e:
                print(f"Error: {e}")
                
    await engine.dispose()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(update_job_table())
