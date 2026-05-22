import asyncio
from app.utils.database import AsyncSessionLocal
from app.services.auth_service import login_user

async def test():
    async with AsyncSessionLocal() as db:
        try:
            # Let's try to login as 'sam@gmail.com' with 'password'
            # Or better, let's create a new user via auth_service.register_user
            from app.services.auth_service import register_user
            try:
                user = await register_user(db, 'test456@gmail.com', 'password123', 'CANDIDATE', 'Test User')
                print("Registered user:", user.email)
            except Exception as e:
                print("Register error:", e)
            
            try:
                res = await login_user(db, 'test456@gmail.com', 'password123')
                print("Login success:", res)
            except Exception as e:
                print("Login error:", e)
        except Exception as e:
            print("Outer error:", e)

asyncio.run(test())
