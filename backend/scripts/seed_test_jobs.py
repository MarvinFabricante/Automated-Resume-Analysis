#!/usr/bin/env python3
"""
Seed Script for Mariwasa Recruitment System Test Jobs.

Creates five standardized test jobs (J1-J4 Active, J5 Archived)
and their corresponding application form templates with suggested questions.
Idempotent and safe to run multiple times without creating duplicates.

Usage:
    python backend/scripts/seed_test_jobs.py
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

JOBS_SPEC = [
    {
        "code": "JOB-2026-0001",
        "tag": "J1",
        "title": "Production Operator",
        "department": "Manufacturing/Operations",
        "location": "Sto. Tomas, Batangas",
        "job_type": "FULL_TIME",
        "salary_range": "PHP 16,000 - 22,000 / month",
        "description": (
            "Operates and monitors tile production equipment to meet daily output and quality targets "
            "while following plant safety procedures.\n\n"
            "Key Responsibilities:\n"
            "• Operate kilns and production machines according to work instructions\n"
            "• Monitor temperature, speed and output, and record readings\n"
            "• Inspect tiles for defects and separate rejects\n"
            "• Perform basic machine cleaning and routine checks\n"
            "• Follow safety rules and use protective equipment"
        ),
        "skills_requirements": "kiln operation, machine handling, quality checking, safety compliance, teamwork",
        "experience_requirements": "3 years in manufacturing or production",
        "education_requirements": "Senior high school graduate or vocational course",
        "certifications_requirements": "safety training (OSHA or BOSH)",
        "is_active_initial": True,
        "is_active_final": True,
        "questions": [
            "How many years of manufacturing or production experience do you have?",
            "Have you operated a kiln or similar heavy equipment?",
            "Do you have safety training certificates?"
        ]
    },
    {
        "code": "JOB-2026-0002",
        "tag": "J2",
        "title": "QA Inspector",
        "department": "Manufacturing/Operations",
        "location": "Sto. Tomas, Batangas",
        "job_type": "FULL_TIME",
        "salary_range": "PHP 22,000 - 30,000 / month",
        "description": (
            "Ensures tiles meet company and ISO quality standards by inspecting products, testing samples "
            "and reporting defects.\n\n"
            "Key Responsibilities:\n"
            "• Inspect raw materials and finished tiles against specifications\n"
            "• Run sample tests for size, strength and surface quality\n"
            "• Document inspection results and defect reports\n"
            "• Coordinate with production on corrective actions\n"
            "• Maintain quality records for audits"
        ),
        "skills_requirements": "quality control, product inspection, defect reporting, documentation, measuring tools",
        "experience_requirements": "2 years in quality assurance or inspection",
        "education_requirements": "Bachelor's in Engineering, Chemistry or a related field",
        "certifications_requirements": "ISO 9001",
        "is_active_initial": True,
        "is_active_final": True,
        "questions": [
            "How many years of quality control experience do you have?",
            "Which measuring or testing tools have you used?",
            "Do you have ISO 9001 training or certification?"
        ]
    },
    {
        "code": "JOB-2026-0003",
        "tag": "J3",
        "title": "Accounting Assistant",
        "department": "Finance and Administration",
        "location": "Main Office, Batangas",
        "job_type": "FULL_TIME",
        "salary_range": "PHP 20,000 - 28,000 / month",
        "description": (
            "Supports daily accounting operations by processing transactions, maintaining records and preparing basic financial reports.\n\n"
            "Key Responsibilities:\n"
            "• Encode invoices, payments and journal entries in SAP\n"
            "• Reconcile bank and supplier accounts\n"
            "• Prepare monthly schedules and reports in Excel\n"
            "• File and maintain accounting documents\n"
            "• Assist during audits and month-end closing"
        ),
        "skills_requirements": "SAP, bookkeeping, Excel, reconciliation, accounts payable",
        "experience_requirements": "1 year in accounting or finance support",
        "education_requirements": "BS Accountancy",
        "certifications_requirements": "None required",
        "is_active_initial": True,
        "is_active_final": True,
        "questions": [
            "How would you rate your SAP experience (none, basic, intermediate, advanced)?",
            "How many years have you worked in accounting?",
            "Which accounting tasks have you handled (accounts payable, reconciliation, reporting)?"
        ]
    },
    {
        "code": "JOB-2026-0004",
        "tag": "J4",
        "title": "Sales Officer (CTM Branch)",
        "department": "Sales and Marketing",
        "location": "CTM retail branch",
        "job_type": "FULL_TIME",
        "salary_range": "PHP 22,000 - 32,000 / month + commissions",
        "description": (
            "Sells Mariwasa tile products at a CTM retail branch, builds customer relationships and helps meet branch sales targets.\n\n"
            "Key Responsibilities:\n"
            "• Assist walk-in customers and recommend suitable tile products\n"
            "• Prepare quotations and process sales orders\n"
            "• Maintain product knowledge and display standards\n"
            "• Follow up on leads and repeat customers\n"
            "• Report daily sales and customer feedback"
        ),
        "skills_requirements": "sales experience, communication, customer handling, product knowledge, negotiation",
        "experience_requirements": "2 years in sales or retail",
        "education_requirements": "Any bachelor's degree",
        "certifications_requirements": "None required",
        "is_active_initial": True,
        "is_active_final": True,
        "questions": [
            "How many years of sales or retail experience do you have?",
            "Did you meet or exceed sales targets?",
            "Describe a time you closed a difficult sale."
        ]
    },
    {
        "code": "JOB-2026-0005",
        "tag": "J5",
        "title": "Logistics Coordinator",
        "department": "Logistics",
        "location": "Main Warehouse, Batangas",
        "job_type": "FULL_TIME",
        "salary_range": "PHP 20,000 - 27,000 / month",
        "description": (
            "Coordinates delivery schedules and warehouse movements to ensure timely dispatch of products.\n\n"
            "Key Responsibilities:\n"
            "• Schedule truck dispatch and deliveries\n"
            "• Track shipments and update status records\n"
            "• Coordinate with warehouse and sales teams\n"
            "• Resolve delivery delays and documentation issues"
        ),
        "skills_requirements": "logistics, scheduling, inventory tracking, coordination, Excel",
        "experience_requirements": "2 years",
        "education_requirements": "Any bachelor's degree",
        "certifications_requirements": "None required",
        "is_active_initial": True,
        "is_active_final": False,  # Explicitly set to Archived per specification
        "questions": [
            "How many years of logistics or scheduling experience do you have?",
            "Which tools do you use to track shipments or inventory?"
        ]
    }
]


def seed_jobs_sqlite(db_path: str):
    """Inserts the five test jobs into SQLite database idempotently."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    created_jobs = []

    for spec in JOBS_SPEC:
        code = spec["code"]
        title = spec["title"]

        # Check if job already exists
        existing = cur.execute(
            "SELECT id, is_active FROM job_descriptions WHERE job_id = ? OR job_title = ?",
            (code, title)
        ).fetchone()

        if existing:
            job_id_db, is_act = existing
            # Ensure final active state matches specification (e.g. J5 archived)
            cur.execute("UPDATE job_descriptions SET is_active = ?, job_type = ? WHERE id = ?", (1 if spec["is_active_final"] else 0, spec["job_type"], job_id_db))
            conn.commit()
            status_lbl = "Active" if spec["is_active_final"] else "Archived"
            print(f"  • {spec['tag']} ({code}): '{title}' already exists (ID #{job_id_db}) -> Ensured {status_lbl}")
            created_jobs.append((spec["tag"], job_id_db, code, title, status_lbl))
            continue

        # Step 1: Insert as Active initially (J5 is created Active, then set to Archived)
        cur.execute(
            """
            INSERT INTO job_descriptions (
                job_id, job_title, department, job_type, location,
                salary_range, description, skills_requirements,
                education_requirements, certifications_requirements,
                experience_requirements, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                title,
                spec["department"],
                spec["job_type"],
                spec["location"],
                spec["salary_range"],
                spec["description"],
                spec["skills_requirements"],
                spec["education_requirements"],
                spec["certifications_requirements"],
                spec["experience_requirements"],
                1 if spec["is_active_initial"] else 0
            )
        )
        conn.commit()
        new_id = cur.lastrowid
        print(f"  ✓ Created {spec['tag']} ({code}): '{title}' (ID #{new_id}) [Active]")

        # Step 2: If final status is Inactive/Archived (like J5), update it now
        if not spec["is_active_final"]:
            cur.execute("UPDATE job_descriptions SET is_active = 0 WHERE id = ?", (new_id,))
            conn.commit()
            print(f"    ↳ Transitioned {spec['tag']} to Archived (is_active=False)")

        status_lbl = "Active" if spec["is_active_final"] else "Archived"
        created_jobs.append((spec["tag"], new_id, code, title, status_lbl))

        # Step 3: Create FormTemplate with suggested questions for this job
        template_name = f"{title} Application Questions"
        existing_tpl = cur.execute("SELECT id FROM form_templates WHERE name = ?", (template_name,)).fetchone()
        if not existing_tpl:
            fields_data = [
                {
                    "id": f"q_{i+1}",
                    "label": q,
                    "type": "textarea" if "describe" in q.lower() or "which" in q.lower() else "text",
                    "required": True,
                }
                for i, q in enumerate(spec["questions"])
            ]
            cur.execute(
                """
                INSERT INTO form_templates (name, description, fields, is_default, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_name,
                    f"Job-specific screening and clarification questions for {title}",
                    json.dumps(fields_data),
                    0,
                    1,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                )
            )
            conn.commit()
            print(f"    ↳ Created FormTemplate #{cur.lastrowid} with {len(spec['questions'])} suggested questions.")

    conn.close()
    return created_jobs


def main():
    print("=" * 65)
    print(" SEEDING 5 TEST JOBS (J1-J4 Active, J5 Archived)")
    print("=" * 65)

    main_db = os.path.join(BACKEND_DIR, "automated_resume.db")
    if not os.path.exists(main_db):
        print(f"[ERROR] Database file not found at {main_db}. Run reset first or start backend.")
        sys.exit(1)

    jobs = seed_jobs_sqlite(main_db)

    print("\n" + "=" * 65)
    print(" SEEDING SUMMARY")
    print("=" * 65)
    active_count = sum(1 for j in jobs if j[4] == "Active")
    archived_count = sum(1 for j in jobs if j[4] == "Archived")

    for tag, jid, code, title, status in jobs:
        print(f"  [{tag}] ID #{jid:02d} | Code: {code} | {status:<8} | {title}")

    print("-" * 65)
    print(f"Total Open / Active Positions: {active_count}")
    print(f"Total Archived Positions      : {archived_count}")
    print("=" * 65)


if __name__ == "__main__":
    main()
