import asyncio

from sqlalchemy import text

from app.utils.auth import hash_password
from app.utils.database import AsyncSessionLocal


DEMO_USERS = [
    {
        "email": "admin@example.com",
        "password": "password",
        "fullname": "Mariwasa Admin",
        "role": "ADMIN",
    },
    {
        "email": "hr@example.com",
        "password": "password",
        "fullname": "Mariwasa HR",
        "role": "HR",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Operations Manager",
    },
    {
        "email": "candidate@example.com",
        "password": "password",
        "fullname": "Demo Candidate",
        "role": "CANDIDATE",
    },
]


DEMO_JOBS = [
    {
        "job_id": "JOB-2026-001",
        "job_title": "Production Supervisor",
        "department": "Manufacturing",
        "job_type": "FULL_TIME",
        "location": "Sto. Tomas, Batangas",
        "salary_range": "PHP 30,000 - PHP 45,000",
        "description": "Lead production line operations, coordinate shift teams, monitor output quality, and support continuous improvement programs.",
        "skills_requirements": "Production planning, ceramic manufacturing, leadership, ISO standards, quality control, shift management",
        "education_requirements": "Bachelor's degree in Industrial Engineering, Manufacturing Engineering, or related field",
        "experience_requirements": "3+ years of manufacturing or production leadership experience",
        "certifications_requirements": "ISO or Lean Manufacturing certification preferred",
        "is_active": True,
    },
    {
        "job_id": "JOB-2026-002",
        "job_title": "Quality Control Analyst",
        "department": "Quality Assurance",
        "job_type": "FULL_TIME",
        "location": "Sto. Tomas, Batangas",
        "salary_range": "PHP 25,000 - PHP 35,000",
        "description": "Perform product inspections, laboratory tests, and quality documentation for ceramic tile production.",
        "skills_requirements": "Material testing, laboratory analysis, attention to detail, quality documentation, data analysis",
        "education_requirements": "Bachelor's degree in Chemical Engineering, Materials Science, or related field",
        "experience_requirements": "1+ year of quality assurance or laboratory experience",
        "certifications_requirements": "Quality management training preferred",
        "is_active": True,
    },
    {
        "job_id": "JOB-2026-003",
        "job_title": "HR Generalist",
        "department": "Human Resources",
        "job_type": "FULL_TIME",
        "location": "Makati City",
        "salary_range": "PHP 28,000 - PHP 40,000",
        "description": "Support recruitment, employee relations, onboarding, records management, and HR operations.",
        "skills_requirements": "Recruitment, employee relations, onboarding, payroll coordination, communication, HRIS",
        "education_requirements": "Bachelor's degree in Psychology, Human Resources, Business Administration, or related field",
        "experience_requirements": "2+ years of HR operations experience",
        "certifications_requirements": "HR certification preferred",
        "is_active": True,
    },
    {
        "job_id": "JOB-2026-004",
        "job_title": "Maintenance Technician",
        "department": "Engineering",
        "job_type": "FULL_TIME",
        "location": "Sto. Tomas, Batangas",
        "salary_range": "PHP 20,000 - PHP 28,000",
        "description": "Maintain production equipment, troubleshoot mechanical and electrical issues, and perform preventive maintenance.",
        "skills_requirements": "Industrial machinery, electrical troubleshooting, mechanical repair, preventive maintenance, safety compliance",
        "education_requirements": "Vocational diploma or associate degree in Electrical, Mechanical, or Industrial Technology",
        "experience_requirements": "2+ years of maintenance experience in a manufacturing environment",
        "certifications_requirements": "TESDA certification preferred",
        "is_active": True,
    },
]


async def upsert_user(session, user):
    email = user["email"].strip().lower()
    password = hash_password(user["password"])
    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    )
    row = result.fetchone()
    if row:
        user_id = row[0]
        await session.execute(
            text(
                """
                UPDATE users
                SET password = :password,
                    fullname = :fullname,
                    role = :role,
                    is_archived = false
                WHERE id = :id
                """
            ),
            {
                "id": user_id,
                "password": password,
                "fullname": user["fullname"],
                "role": user["role"],
            },
        )
    else:
        result = await session.execute(
            text(
                """
                INSERT INTO users (email, password, fullname, role, is_archived, is_online)
                VALUES (:email, :password, :fullname, :role, false, false)
                RETURNING id
                """
            ),
            {
                "email": email,
                "password": password,
                "fullname": user["fullname"],
                "role": user["role"],
            },
        )
        user_id = result.fetchone()[0]

    if user["role"] == "ADMIN":
        await session.execute(
            text(
                """
                INSERT INTO admins (id, managed_region)
                VALUES (:id, 'Main Headquarters')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": user_id},
        )
    elif user["role"] == "HR":
        await session.execute(
            text(
                """
                INSERT INTO hr_staffs (id, company_name, department, position)
                VALUES (:id, :company_name, :department, :position)
                ON CONFLICT (id) DO UPDATE
                SET company_name = EXCLUDED.company_name,
                    department = EXCLUDED.department,
                    position = EXCLUDED.position
                """
            ),
            {
                "id": user_id,
                "company_name": user["company_name"],
                "department": user["department"],
                "position": user["position"],
            },
        )
    elif user["role"] == "CANDIDATE":
        await session.execute(
            text(
                """
                INSERT INTO candidates (id, resume_url, experience_years)
                VALUES (:id, NULL, 0)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": user_id},
        )

    return user_id


async def upsert_job(session, job):
    await session.execute(
        text(
            """
            INSERT INTO job_descriptions (
                job_id, job_title, department, job_type, location, salary_range,
                description, skills_requirements, education_requirements,
                certifications_requirements, experience_requirements, is_active
            )
            VALUES (
                :job_id, :job_title, :department, CAST(:job_type AS jobtype), :location,
                :salary_range, :description, :skills_requirements, :education_requirements,
                :certifications_requirements, :experience_requirements, :is_active
            )
            ON CONFLICT (job_id) DO UPDATE
            SET job_title = EXCLUDED.job_title,
                department = EXCLUDED.department,
                job_type = EXCLUDED.job_type,
                location = EXCLUDED.location,
                salary_range = EXCLUDED.salary_range,
                description = EXCLUDED.description,
                skills_requirements = EXCLUDED.skills_requirements,
                education_requirements = EXCLUDED.education_requirements,
                certifications_requirements = EXCLUDED.certifications_requirements,
                experience_requirements = EXCLUDED.experience_requirements,
                is_active = EXCLUDED.is_active
            """
        ),
        job,
    )


async def seed_demo_data():
    async with AsyncSessionLocal() as session:
        for user in DEMO_USERS:
            await upsert_user(session, user)
        for job in DEMO_JOBS:
            await upsert_job(session, job)
        await session.commit()

    print("Seeded demo users and jobs.")
    print("Demo logins: admin@example.com / password, hr@example.com / password, candidate@example.com / password")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
