import asyncio
from app.utils.database import AsyncSessionLocal
from app.schemas.candidate_schema import CandidateCreate
from app.services.candidate_service import create_candidate_profile
from app.services.auth_service import login_user

async def test():
    async with AsyncSessionLocal() as db:
        try:
            cand = CandidateCreate(
                fullname='Test Cand',
                email='cand1@example.com',
                password='candpassword'
            )
            created = await create_candidate_profile(db, cand)
            print("Candidate created:", created.email)
            
            # Now try to login
            res = await login_user(db, 'cand1@example.com', 'candpassword')
            print("Candidate login success:", res)
        except Exception as e:
            print("Error:", e)

asyncio.run(test())
