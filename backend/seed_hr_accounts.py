import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.utils.database import AsyncSessionLocal
from app.utils.auth import hash_password

HR_ACCOUNTS = [
    {
        "email": "fabricantemarvin262@gmail.com",
        "fullname": "Marvin Fabricante",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "Lead Technical Recruiter",
        "bio": "Lead technical recruiter and talent evaluation specialist for Mariwasa Siam Ceramics."
    },
    {
        "email": "ceramicsmariwasasiam@gmail.com",
        "fullname": "Mariwasa Siam Ceramics HR",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Talent Acquisition & HR Operations",
        "position": "HR Operations Manager",
        "bio": "Central HR administration and talent acquisition operations for Mariwasa Siam Ceramics."
    },
    {
        "email": "johnpaul6214@gmail.com",
        "fullname": "John Paul",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Recruitment Specialist",
        "bio": "Technical panelist and recruitment specialist conducting candidate screening and interviews."
    },
    {
        "email": "jaemoscoso13@gmail.com",
        "fullname": "Jae Moscoso",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "Talent Acquisition Officer",
        "bio": "Talent acquisition officer responsible for interview management and candidate evaluation."
    },
    {
        "email": "macapanastyronjames@gmail.com",
        "fullname": "Tyron James Macapanas",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Generalist & Panelist",
        "bio": "HR generalist and technical interview panelist managing candidate assessments."
    }
]

async def seed_hr_accounts():
    async with AsyncSessionLocal() as session:
        # Default password is "password"
        hashed_pw = hash_password("password")

        for acc in HR_ACCOUNTS:
            email = acc["email"].strip().lower()
            fullname = acc["fullname"]
            company = acc["company_name"]
            dept = acc["department"]
            position = acc["position"]
            bio = acc["bio"]

            # Check if user exists in users table
            res = await session.execute(text("SELECT id, role FROM users WHERE email = :email"), {"email": email})
            row = res.fetchone()

            if row:
                user_id = row[0]
                # Update users table
                await session.execute(
                    text("""
                        UPDATE users
                        SET role = 'HR', fullname = :fullname, password = :pw, bio = :bio, is_archived = false
                        WHERE id = :id
                    """),
                    {"fullname": fullname, "pw": hashed_pw, "bio": bio, "id": user_id}
                )
                print(f"[UPDATED] User {email} (ID: {user_id}) as HR")
            else:
                # Insert into users table
                insert_res = await session.execute(
                    text("""
                        INSERT INTO users (email, password, fullname, role, bio, is_archived, is_online)
                        VALUES (:email, :pw, :fullname, 'HR', :bio, false, false)
                        RETURNING id
                    """),
                    {"email": email, "pw": hashed_pw, "fullname": fullname, "bio": bio}
                )
                user_id = insert_res.fetchone()[0]
                print(f"[CREATED] User {email} (ID: {user_id}) as HR")

            # Check if entry exists in hr_staffs
            hr_res = await session.execute(text("SELECT id FROM hr_staffs WHERE id = :id"), {"id": user_id})
            hr_row = hr_res.fetchone()

            if hr_row:
                await session.execute(
                    text("""
                        UPDATE hr_staffs
                        SET company_name = :company, department = :dept, position = :position
                        WHERE id = :id
                    """),
                    {"company": company, "dept": dept, "position": position, "id": user_id}
                )
                print(f"  └─ Updated hr_staffs entry for ID {user_id}")
            else:
                await session.execute(
                    text("""
                        INSERT INTO hr_staffs (id, company_name, department, position)
                        VALUES (:id, :company, :dept, :position)
                    """),
                    {"id": user_id, "company": company, "dept": dept, "position": position}
                )
                print(f"  └─ Created hr_staffs entry for ID {user_id}")

        await session.commit()
        print("\nAll 5 HR accounts have been successfully seeded and verified!")

if __name__ == "__main__":
    asyncio.run(seed_hr_accounts())
