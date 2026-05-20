"""
Migration script to add new ATS breakdown columns to job_applications table.
Run this once to add the new columns for detailed analysis storage.
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=True)

NEW_COLUMNS = [
    ("matched_skills", "JSON"),
    ("missing_skills", "JSON"),
    ("relevant_experience", "VARCHAR"),
    ("experience_gaps", "VARCHAR"),
    ("required_degree", "VARCHAR"),
    ("candidate_degree", "VARCHAR"),
    ("recommendations", "JSON"),
]

async def migrate():
    async with engine.begin() as conn:
        for col_name, col_type in NEW_COLUMNS:
            try:
                await conn.execute(text(
                    f"ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                ))
                print(f"  ✓ Added column: {col_name} ({col_type})")
            except Exception as e:
                print(f"  ⚠ Column {col_name} might already exist: {e}")
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
