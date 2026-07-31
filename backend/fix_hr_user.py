import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.utils.database import AsyncSessionLocal
from app.utils.auth import hash_password
from app.repositories.auth_repository import AuthRepository
from app.services.google_calendar_service import get_real_google_events

async def fix_hr_user():
    from app.main import backend_application
    await backend_application.startup()
    
    async with AsyncSessionLocal() as db:
        email = "marvinfabricante630@gmail.com"
        password = "password"
        
        # update user
        pw_hash = hash_password(password)
        await db.execute(
            text("UPDATE users SET role = 'HR', password = :pw, is_archived = false WHERE email = :email"), 
            {"pw": pw_hash, "email": email}
        )
        await db.commit()
        print("Updated user to HR.")
        
        existing = await AuthRepository.get_raw_user_by_email(db, email)
        print("Role is now:", existing.role)
        
        # Check credentials
        row = await db.execute(text("SELECT google_credentials FROM users WHERE email = :email"), {"email": email})
        creds = row.fetchone()[0]
        if creds:
            print("Has google credentials! Fetching events...")
            events = await asyncio.to_thread(get_real_google_events, creds)
            if events:
                for e in events:
                    print(e.get('summary'), e.get('start_datetime'))
            else:
                print("No events found or error.")
        else:
            print("No google credentials found for user.")

if __name__ == "__main__":
    asyncio.run(fix_hr_user())
