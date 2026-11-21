#!/usr/bin/env python3
"""
Unified Idempotent Database & ML Bootstrap Seed Script
for Mariwasa Siam Ceramics Inc. — Automated Resume Analysis System.

Seeds (only creating missing records, safe to run repeatedly):
  1. Default Admin account (admin@mariwasa.com) & HR Staff accounts
  2. Mariwasa Siam Ceramics job descriptions (active open positions)
  3. Default application form templates (form_templates)
  4. Default system configurations (matching weights, thresholds,
     max_active_applications, and Email/SMS notification templates)
  5. ML Engine baseline dataset, feedback DB, and production_model.pkl
  6. Clears relevant Redis caches so changes appear immediately

Usage:
    python scripts/seed_defaults.py
    python scripts/seed_defaults.py --with-test-jobs
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List

# Ensure backend directory is importable regardless of current working directory
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv(os.path.join(os.path.dirname(BACKEND_DIR), ".env"))

from sqlalchemy import func, select, text
from app.utils.database import AsyncSessionLocal, engine, Base
from app.utils.auth import hash_password
from app.models.user import User
from app.models.admin import Admin
from app.models.hr import HR
from app.models.job_description import JobDescription, JobType
from app.models.system_config import SystemConfig, FormTemplate
from app.services.system_config_service import (
    DEFAULT_WEIGHTS,
    DEFAULT_THRESHOLDS,
    DEFAULT_RECRUITMENT_CONFIG,
)
from app.services.message_template_service import (
    TEMPLATE_CONFIG_KEY,
    TEMPLATE_CONFIG_CATEGORY,
    DEFAULT_TEMPLATES,
)


DEFAULT_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@mariwasa.com").strip().lower()
DEFAULT_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME = os.getenv("SEED_ADMIN_NAME", "System Administrator")

HR_ACCOUNTS: List[Dict[str, str]] = [
    {
        "email": "hr.mariwasa@gmail.com",
        "fullname": "Mariwasa HR",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Specialist",
        "password": "password123",
    },
    {
        "email": "sheenahpolicapioh@gmail.com",
        "fullname": "Sheenah Policapio",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Specialist",
        "password": "password123",
    },
    {
        "email": "crparayaoan@gmail.com",
        "fullname": "CR Parayaoan",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Specialist",
        "password": "password123",
    },
    {
        "email": "ceramicsmariwasasiam@gmail.com",
        "fullname": "Mariwasa Siam Ceramics HR",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Manager",
        "password": "password123",
    },
    {
        "email": "fabricantemarvin262@gmail.com",
        "fullname": "Marvin Fabricante",
        "company_name": "Mariwasa Siam Ceramics, Inc.",
        "department": "Human Resources",
        "position": "HR Officer",
        "password": "password123",
    },
]

MARIWASA_JOBS: List[Dict[str, str]] = [
    {
        "job_title": "Production Engineer",
        "department": "Manufacturing",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱40,000",
        "description": "In charge of making sure our ceramic tiles are made well and on time.",
        "skills_requirements": "Process optimization, Lean manufacturing, AutoCAD, Quality Control",
        "education_requirements": "Bachelor's degree in Chemical, Mechanical, or Industrial Engineering",
        "certifications_requirements": "Licensed Engineer preferred",
        "experience_requirements": "2-3 years in manufacturing, preferably in ceramics",
    },
    {
        "job_title": "Quality Assurance Supervisor",
        "department": "Quality Assurance",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱30,000 - ₱45,000",
        "description": "Leads the team that checks our tiles to make sure they are in perfect condition before they go to customers.",
        "skills_requirements": "ISO Standards, Quality Auditing, Root Cause Analysis, Team Leadership",
        "education_requirements": "Bachelor's degree in Engineering or related field",
        "certifications_requirements": "Certified Quality Engineer (CQE) is a plus",
        "experience_requirements": "3-5 years in QA/QC role",
    },
    {
        "job_title": "Maintenance Technician",
        "department": "Engineering and Maintenance",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱18,000 - ₱25,000",
        "description": "Fixes and takes care of factory machines so they keep running smoothly.",
        "skills_requirements": "Troubleshooting, Electrical/Mechanical repair, Preventive Maintenance",
        "education_requirements": "Vocational course in Mechanical/Electrical Technology",
        "certifications_requirements": "NCII Certification",
        "experience_requirements": "1-2 years experience in plant maintenance",
    },
    {
        "job_title": "R&D Chemist",
        "department": "Research and Development",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱35,000",
        "description": "Creates new mixtures for our tiles and tests them to make our products better.",
        "skills_requirements": "Chemical analysis, Material testing, Formulation, Data Analysis",
        "education_requirements": "Bachelor's degree in Chemistry or Chemical Engineering",
        "certifications_requirements": "Licensed Chemist",
        "experience_requirements": "2+ years in R&D, ceramics experience is a huge plus",
    },
    {
        "job_title": "Sales Executive",
        "department": "Sales",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱20,000 - ₱30,000 + Commission",
        "description": "Finds new customers and takes good care of the stores that already sell our products.",
        "skills_requirements": "B2B Sales, Negotiation, Presentation skills, Account Management",
        "education_requirements": "Bachelor's degree in Business Administration or Marketing",
        "certifications_requirements": "None",
        "experience_requirements": "At least 2 years experience in field sales, preferably in construction materials",
    },
    {
        "job_title": "HR Manager",
        "department": "Human Resources",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱60,000 - ₱80,000",
        "description": "Manages hiring, helps employees do their best, and makes sure everyone is happy at work.",
        "skills_requirements": "Labor laws, Strategic HR, Employee Relations, Leadership",
        "education_requirements": "Bachelor's degree in Psychology, HR, or related field. Master's is an advantage.",
        "certifications_requirements": "CHRP is a plus",
        "experience_requirements": "7+ years in HR, with at least 3 years in a managerial role",
    },
    {
        "job_title": "Logistics Coordinator",
        "department": "Supply Chain",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱22,000 - ₱30,000",
        "description": "Organizes the packing and shipping of our tiles to stores and customers across the country.",
        "skills_requirements": "Route planning, Inventory tracking, Communication, ERP Systems",
        "education_requirements": "Bachelor's degree in Supply Chain Management or Business Administration",
        "certifications_requirements": "None",
        "experience_requirements": "2 years in logistics or dispatch operations",
    },
    {
        "job_title": "IT Support Specialist",
        "department": "Information Technology",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱20,000 - ₱28,000",
        "description": "Helps team members with computer problems and keeps our office computers and internet working.",
        "skills_requirements": "Hardware troubleshooting, Networking, Helpdesk support, Windows OS",
        "education_requirements": "Bachelor's degree in IT, Computer Science, or related field",
        "certifications_requirements": "CompTIA A+ or similar",
        "experience_requirements": "1-3 years in IT support",
    },
    {
        "job_title": "Accounting Assistant",
        "department": "Finance",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱18,000 - ₱22,000",
        "description": "Helps with money matters like paying bills, sending invoices, and keeping track of our spending.",
        "skills_requirements": "Bookkeeping, Excel proficiency, Attention to detail, SAP Knowledge",
        "education_requirements": "Bachelor's degree in Accountancy or Financial Management",
        "certifications_requirements": "CPA not required but a plus",
        "experience_requirements": "Fresh graduates to 1 year experience",
    },
    {
        "job_title": "Safety Officer",
        "department": "EHS",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱35,000",
        "description": "Makes sure everyone stays safe in the factory by teaching and checking safety rules.",
        "skills_requirements": "OSH Standards, Hazard Identification, First Aid, Reporting",
        "education_requirements": "Bachelor's degree in any field",
        "certifications_requirements": "BOSH/COSH Training Certificate from DOLE-accredited agency",
        "experience_requirements": "2 years experience as a Safety Officer in a manufacturing setup",
    },
    {
        "job_title": "Marketing Associate",
        "department": "Marketing",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱20,000 - ₱28,000",
        "description": "Helps run our ads, plans events, and posts on our social media pages.",
        "skills_requirements": "Copywriting, Social Media Management, Event Coordination, Creativity",
        "education_requirements": "Bachelor's degree in Marketing, Communications, or related",
        "certifications_requirements": "None",
        "experience_requirements": "1-2 years experience in marketing",
    },
    {
        "job_title": "Procurement Specialist",
        "department": "Supply Chain",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱35,000",
        "description": "Finds and buys the materials we need to make tiles for the best possible price.",
        "skills_requirements": "Negotiation, Vendor Management, Sourcing, Market Analysis",
        "education_requirements": "Bachelor's degree in Business or Supply Chain",
        "certifications_requirements": "None",
        "experience_requirements": "3 years experience in purchasing or procurement",
    },
    {
        "job_title": "Production Supervisor",
        "department": "Manufacturing",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱30,000 - ₱45,000",
        "description": "Guides a team of factory workers to reach our daily goals safely.",
        "skills_requirements": "Team Leadership, Production Planning, Problem Solving, 5S",
        "education_requirements": "Bachelor's degree in Engineering",
        "certifications_requirements": "None",
        "experience_requirements": "3-5 years supervisory experience in a manufacturing plant",
    },
    {
        "job_title": "Graphic Designer",
        "department": "Marketing",
        "job_type": "Contract",
        "location": "Remote",
        "salary_range": "₱20,000 - ₱30,000",
        "description": "Designs nice-looking pictures and materials to help advertise our tiles.",
        "skills_requirements": "Adobe Creative Suite, Layout design, Typography, Creativity",
        "education_requirements": "Bachelor's degree in Fine Arts, Multimedia Arts, or equivalent",
        "certifications_requirements": "None",
        "experience_requirements": "Portfolio demonstrating 2+ years of design work",
    },
    {
        "job_title": "Customer Service Representative",
        "department": "Customer Support",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱18,000 - ₱22,000",
        "description": "Answers questions from customers, helps solve their problems, and takes their orders.",
        "skills_requirements": "Communication, Empathy, Problem Solving, CRM Software",
        "education_requirements": "Bachelor's degree or 2-year college level",
        "certifications_requirements": "None",
        "experience_requirements": "At least 1 year in customer service",
    },
    {
        "job_title": "Forklift Operator",
        "department": "Warehouse",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱15,000 - ₱18,000",
        "description": "Drives a forklift to safely move and stack large piles of tiles around the warehouse.",
        "skills_requirements": "Forklift Operation, Safety Awareness, Spatial Awareness",
        "education_requirements": "High School Graduate",
        "certifications_requirements": "Valid Forklift Certification/License",
        "experience_requirements": "1-2 years experience as a forklift operator",
    },
    {
        "job_title": "Internal Auditor",
        "department": "Audit",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱30,000 - ₱45,000",
        "description": "Checks our company's money records and how we work to make sure everything is correct and find ways to do better.",
        "skills_requirements": "Risk Assessment, Financial Analysis, Report Writing, Attention to detail",
        "education_requirements": "Bachelor's degree in Accountancy",
        "certifications_requirements": "CPA Required. CIA is an advantage.",
        "experience_requirements": "2-4 years experience in internal or external auditing",
    },
    {
        "job_title": "Software Developer",
        "department": "Information Technology",
        "job_type": "Full-Time",
        "location": "Hybrid",
        "salary_range": "₱40,000 - ₱60,000",
        "description": "Builds and fixes computer programs that make everyday work easier for our team.",
        "skills_requirements": "Python, React, SQL, API Development",
        "education_requirements": "Bachelor's degree in Computer Science, IT, or related",
        "certifications_requirements": "None",
        "experience_requirements": "3+ years in full-stack software development",
    },
    {
        "job_title": "Data Analyst",
        "department": "Strategy and Planning",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱35,000 - ₱50,000",
        "description": "Looks at our sales and the market to help company leaders make smart choices.",
        "skills_requirements": "SQL, Python/R, Data Visualization (Tableau/PowerBI), Statistical Analysis",
        "education_requirements": "Bachelor's degree in Statistics, Math, Economics, or Computer Science",
        "certifications_requirements": "None",
        "experience_requirements": "2+ years in data analysis",
    },
    {
        "job_title": "Supply Chain Manager",
        "department": "Supply Chain",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱70,000 - ₱100,000",
        "description": "Leads the process of getting materials, storing our products, and shipping them out smoothly.",
        "skills_requirements": "Strategic Planning, Vendor Negotiation, Logistics Management, Leadership",
        "education_requirements": "Bachelor's degree in Supply Chain, Business, or Engineering",
        "certifications_requirements": "CSCP or similar certification is a plus",
        "experience_requirements": "7+ years in supply chain, with managerial experience",
    },
    {
        "job_title": "Civil Engineer",
        "department": "Facilities",
        "job_type": "Contract",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱30,000 - ₱45,000",
        "description": "Manages building projects for our factory and keeps our buildings in good shape.",
        "skills_requirements": "Project Management, Structural Design, AutoCAD, Cost Estimation",
        "education_requirements": "Bachelor's degree in Civil Engineering",
        "certifications_requirements": "Licensed Civil Engineer",
        "experience_requirements": "3-5 years in construction or plant facilities",
    },
    {
        "job_title": "Corporate Lawyer",
        "department": "Legal",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱60,000 - ₱90,000",
        "description": "Takes care of the company's legal issues, checks contracts, and makes sure we follow the law.",
        "skills_requirements": "Corporate Law, Contract drafting, Negotiation, Legal Research",
        "education_requirements": "Juris Doctor or Bachelor of Laws",
        "certifications_requirements": "Passed the Philippine Bar",
        "experience_requirements": "3-5 years of corporate law practice",
    },
    {
        "job_title": "Environment Officer",
        "department": "EHS",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱35,000",
        "description": "Makes sure our factory follows nature-friendly rules and helps us protect the environment.",
        "skills_requirements": "Environmental Laws (DENR standards), Waste Management, Auditing",
        "education_requirements": "Bachelor's degree in Environmental Science, Chemical Engineering, or related",
        "certifications_requirements": "Pollution Control Officer (PCO) Accreditation",
        "experience_requirements": "2+ years as a PCO or in environmental compliance",
    },
    {
        "job_title": "Financial Planning and Analysis (FP&A) Manager",
        "department": "Finance",
        "job_type": "Full-Time",
        "location": "Metro Manila",
        "salary_range": "₱70,000 - ₱100,000",
        "description": "Plans our budget and guesses future money needs to help the company make good decisions.",
        "skills_requirements": "Financial Modeling, Budgeting, Strategic Thinking, Advanced Excel",
        "education_requirements": "Bachelor's degree in Finance or Accountancy",
        "certifications_requirements": "CPA or CFA is highly preferred",
        "experience_requirements": "5+ years in FP&A, with supervisory experience",
    },
    {
        "job_title": "Talent Acquisition Specialist",
        "department": "Human Resources",
        "job_type": "Full-Time",
        "location": "Hybrid",
        "salary_range": "₱22,000 - ₱30,000",
        "description": "Finds and interviews great people to join our team for different jobs.",
        "skills_requirements": "Sourcing, Interviewing, Negotiation, Applicant Tracking Systems",
        "education_requirements": "Bachelor's degree in Psychology or Human Resources",
        "certifications_requirements": "None",
        "experience_requirements": "2-3 years in recruitment",
    },
    {
        "job_title": "Product Development Manager",
        "department": "Research and Development",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱60,000 - ₱80,000",
        "description": "Leads the creation of new tile designs from a simple idea to the final product.",
        "skills_requirements": "Project Management, Product Life Cycle, Materials Science, Design trends",
        "education_requirements": "Bachelor's degree in Engineering, Design, or related field",
        "certifications_requirements": "None",
        "experience_requirements": "5+ years in product development in manufacturing",
    },
    {
        "job_title": "Warehouse Supervisor",
        "department": "Supply Chain",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱30,000 - ₱45,000",
        "description": "Manages the daily work in the warehouse, keeps track of stock, and guides the team.",
        "skills_requirements": "Inventory Management, Team Leadership, ERP Systems, Logistics",
        "education_requirements": "Bachelor's degree in Business or Supply Chain",
        "certifications_requirements": "None",
        "experience_requirements": "3-5 years supervisory experience in warehousing",
    },
    {
        "job_title": "Training Officer",
        "department": "Human Resources",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱35,000",
        "description": "Creates and teaches classes to help our employees learn new skills.",
        "skills_requirements": "Instructional Design, Presentation Skills, Facilitation, Coaching",
        "education_requirements": "Bachelor's degree in Psychology, Education, or related field",
        "certifications_requirements": "None",
        "experience_requirements": "2-3 years in corporate training or organizational development",
    },
    {
        "job_title": "Industrial Engineer",
        "department": "Continuous Improvement",
        "job_type": "Full-Time",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱25,000 - ₱40,000",
        "description": "Looks closely at how we make things to find ways to save time and money.",
        "skills_requirements": "Time and Motion Study, Six Sigma, Lean Manufacturing, Data Analysis",
        "education_requirements": "Bachelor's degree in Industrial Engineering",
        "certifications_requirements": "Lean Six Sigma Green Belt preferred",
        "experience_requirements": "2+ years in process improvement",
    },
    {
        "job_title": "Machine Operator",
        "department": "Manufacturing",
        "job_type": "Contract",
        "location": "Santo Tomas, Batangas",
        "salary_range": "₱15,000 - ₱18,000",
        "description": "Runs the large machines used to make our tiles.",
        "skills_requirements": "Machine operation, Basic troubleshooting, Adherence to safety protocols",
        "education_requirements": "Vocational course or High School Graduate",
        "certifications_requirements": "None",
        "experience_requirements": "1 year experience in a manufacturing environment",
    },
]

DEFAULT_FORM_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "Standard Mariwasa Application Form",
        "description": "Default candidate screening questions covering availability, expected salary, and plant location.",
        "is_default": True,
        "fields": [
            {
                "field_name": "availability_start",
                "field_type": "text",
                "label": "When are you available to start if selected?",
                "required": True,
                "placeholder": "e.g., Immediately / 30 days notice",
            },
            {
                "field_name": "expected_salary",
                "field_type": "text",
                "label": "Expected Monthly Salary (PHP)",
                "required": False,
                "placeholder": "e.g., PHP 25,000 - 30,000",
            },
            {
                "field_name": "willing_onsite",
                "field_type": "select",
                "label": "Are you willing to work onsite at the assigned plant/office location?",
                "required": True,
                "options": ["Yes", "No", "Open to relocation"],
            },
        ],
    },
    {
        "name": "Manufacturing & Plant Operations Screening",
        "description": "Technical & safety screening template for production, kiln, QA, and maintenance roles.",
        "is_default": False,
        "fields": [
            {
                "field_name": "shift_availability",
                "field_type": "select",
                "label": "Are you available for shifting schedules?",
                "required": True,
                "options": ["Yes", "Day Shift Only"],
            },
            {
                "field_name": "safety_training",
                "field_type": "textarea",
                "label": "List any safety certifications (BOSH, COSH, NCII, Forklift, etc.)",
                "required": False,
                "placeholder": "Enter certificate names and validity if applicable",
            },
        ],
    },
]

_JOB_TYPE_MAP = {
    "Full-Time": JobType.FULL_TIME,
    "FULL_TIME": JobType.FULL_TIME,
    "Part-Time": JobType.PART_TIME,
    "PART_TIME": JobType.PART_TIME,
    "Contract": JobType.CONTRACT,
    "CONTRACT": JobType.CONTRACT,
    "Freelance": JobType.FREELANCE,
    "FREELANCE": JobType.FREELANCE,
    "Internship": JobType.INTERNSHIP,
    "INTERNSHIP": JobType.INTERNSHIP,
}


async def ensure_schema() -> None:
    """Ensure all database tables exist before seeding."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_accounts(session) -> Dict[str, int]:
    """Idempotently seed default Admin and HR accounts."""
    created_admin = 0
    created_hr = 0
    updated_hr = 0

    # 1. Default Admin Account
    res_admin = await session.execute(
        text("SELECT id FROM users WHERE LOWER(email) = :email"),
        {"email": DEFAULT_ADMIN_EMAIL},
    )
    admin_row = res_admin.fetchone()
    if not admin_row:
        admin_obj = Admin(
            email=DEFAULT_ADMIN_EMAIL,
            password=hash_password(DEFAULT_ADMIN_PASSWORD),
            fullname=DEFAULT_ADMIN_NAME,
            role="ADMIN",
            department="Administration",
            position="System Administrator",
            is_archived=False,
            is_online=False,
        )
        session.add(admin_obj)
        await session.flush()
        created_admin += 1
        print(f"  + Created Admin account: {DEFAULT_ADMIN_EMAIL}")
    else:
        admin_uid = admin_row[0]
        chk_adm = await session.execute(
            text("SELECT id FROM admins WHERE id = :id"),
            {"id": admin_uid},
        )
        if not chk_adm.fetchone():
            await session.execute(
                text(
                    "INSERT INTO admins (id, department, position) VALUES (:id, 'Administration', 'System Administrator')"
                ),
                {"id": admin_uid},
            )

    # 2. Default HR Accounts
    for acc in HR_ACCOUNTS:
        email = acc["email"].strip().lower()
        res = await session.execute(
            text("SELECT id FROM users WHERE LOWER(email) = :email"),
            {"email": email},
        )
        row = res.fetchone()
        if not row:
            hr_obj = HR(
                email=email,
                password=hash_password(acc["password"]),
                fullname=acc["fullname"],
                role="HR",
                company_name=acc["company_name"],
                department=acc["department"],
                position=acc["position"],
                is_archived=False,
                is_online=False,
            )
            session.add(hr_obj)
            await session.flush()
            created_hr += 1
            print(f"  + Created HR account: {email}")
        else:
            uid = row[0]
            await session.execute(
                text("UPDATE users SET role = 'HR', is_archived = :is_archived WHERE id = :id"),
                {"id": uid, "is_archived": False},
            )
            hr_chk = await session.execute(
                text("SELECT id FROM hr_staffs WHERE id = :id"),
                {"id": uid},
            )
            if not hr_chk.fetchone():
                await session.execute(
                    text(
                        """
                        INSERT INTO hr_staffs (id, company_name, department, position)
                        VALUES (:id, :company_name, :department, :position)
                        """
                    ),
                    {
                        "id": uid,
                        "company_name": acc["company_name"],
                        "department": acc["department"],
                        "position": acc["position"],
                    },
                )
            else:
                await session.execute(
                    text(
                        """
                        UPDATE hr_staffs
                        SET company_name = :company_name, department = :department, position = :position
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": uid,
                        "company_name": acc["company_name"],
                        "department": acc["department"],
                        "position": acc["position"],
                    },
                )
            updated_hr += 1

    await session.commit()
    return {"created_admin": created_admin, "created_hr": created_hr, "verified_hr": updated_hr}


async def seed_jobs(session) -> Dict[str, int]:
    """Idempotently seed Mariwasa job descriptions without duplicating existing jobs."""
    existing_rows = (
        await session.execute(
            select(JobDescription.job_title, JobDescription.department)
        )
    ).all()
    existing_keys = {
        ((t or "").strip().lower(), (d or "").strip().lower())
        for t, d in existing_rows
    }

    created = 0
    skipped = 0
    for job_data in MARIWASA_JOBS:
        key = (
            job_data["job_title"].strip().lower(),
            job_data["department"].strip().lower(),
        )
        if key in existing_keys:
            skipped += 1
            continue

        job_enum = _JOB_TYPE_MAP.get(job_data["job_type"], JobType.FULL_TIME)
        new_job = JobDescription(
            job_id=str(uuid.uuid4()),
            job_title=job_data["job_title"],
            department=job_data["department"],
            job_type=job_enum,
            location=job_data["location"],
            salary_range=job_data["salary_range"],
            description=job_data["description"],
            skills_requirements=job_data["skills_requirements"],
            education_requirements=job_data["education_requirements"],
            certifications_requirements=job_data["certifications_requirements"],
            experience_requirements=job_data["experience_requirements"],
            is_active=True,
        )
        session.add(new_job)
        existing_keys.add(key)
        created += 1

    await session.commit()
    return {"created_jobs": created, "existing_jobs": skipped}


async def seed_form_templates(session) -> Dict[str, int]:
    """Idempotently seed default application form templates."""
    existing_names = set(
        (await session.execute(select(FormTemplate.name))).scalars().all()
    )
    created = 0
    for tpl in DEFAULT_FORM_TEMPLATES:
        if tpl["name"] in existing_names:
            continue
        session.add(
            FormTemplate(
                name=tpl["name"],
                description=tpl["description"],
                fields=tpl["fields"],
                is_default=tpl["is_default"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        created += 1
    await session.commit()
    return {"created_form_templates": created, "existing_form_templates": len(existing_names)}


async def seed_system_configs(session) -> Dict[str, int]:
    """Idempotently seed default matching, recruitment, and notification template configs."""
    default_notif_overrides = {
        k: {
            "email_subject": v.get("email_subject", ""),
            "email_message": v.get("email_message", ""),
            "sms_message": v.get("sms_message", ""),
        }
        for k, v in DEFAULT_TEMPLATES.items()
    }

    desired_configs = [
        (
            "matching_weights",
            json.dumps(DEFAULT_WEIGHTS),
            "matching",
            "Weights for job matching algorithm components",
        ),
        (
            "matching_thresholds",
            json.dumps(DEFAULT_THRESHOLDS),
            "matching",
            "Thresholds and limits for job matching algorithm",
        ),
        (
            "max_active_applications",
            str(DEFAULT_RECRUITMENT_CONFIG["max_active_applications"]),
            "recruitment",
            "Maximum active applications allowed per candidate",
        ),
        (
            TEMPLATE_CONFIG_KEY,
            json.dumps(default_notif_overrides),
            TEMPLATE_CONFIG_CATEGORY,
            "Customizable Email and SMS notification message templates",
        ),
    ]

    existing_keys = set(
        (await session.execute(select(SystemConfig.key))).scalars().all()
    )
    created = 0
    for key, val, cat, desc in desired_configs:
        if key in existing_keys:
            continue
        session.add(
            SystemConfig(
                key=key,
                value=val,
                category=cat,
                description=desc,
            )
        )
        created += 1
    await session.commit()
    return {"created_configs": created, "existing_configs": len(existing_keys)}


def seed_ml_bootstrap() -> bool:
    """Initialize baseline dataset, feedback.db, and production_model.pkl if missing."""
    data_dir = os.path.join(BACKEND_DIR, "data")
    model_path = os.path.join(data_dir, "production_model.pkl")
    feedback_path = os.path.join(data_dir, "feedback.db")

    if os.path.exists(model_path) and os.path.exists(feedback_path):
        print("  • ML Engine artifacts already present (production_model.pkl & feedback.db)")
        return False

    try:
        from scripts.bootstrap_model import bootstrap

        bootstrap()
        return True
    except Exception as exc:
        print(f"  ! ML bootstrap notice: {exc}")
        return False


async def clear_seed_caches() -> None:
    """Clear Redis caches affected by seeding so frontend reflects updates immediately."""
    try:
        from app.utils.cache import clear_cache_pattern

        for pattern in (
            "jobs:*",
            "user:*",
            "users*",
            "hr:*",
            "admin*",
            "app_stats*",
            "sys_config*",
            "form_templates*",
        ):
            await clear_cache_pattern(pattern)
    except Exception as exc:
        print(f"  • Redis cache clear skipped: {exc}")


async def run_all_seeds(include_ml: bool = True) -> Dict[str, Any]:
    """Run all idempotent database & ML seeds."""
    await ensure_schema()
    async with AsyncSessionLocal() as session:
        acc_res = await seed_accounts(session)
        job_res = await seed_jobs(session)
        tpl_res = await seed_form_templates(session)
        cfg_res = await seed_system_configs(session)

    ml_bootstrapped = seed_ml_bootstrap() if include_ml else False
    await clear_seed_caches()

    summary = {
        **acc_res,
        **job_res,
        **tpl_res,
        **cfg_res,
        "ml_bootstrapped": ml_bootstrapped,
    }
    print(
        f"✓ Seed Summary: +{acc_res['created_admin']} admin, "
        f"+{acc_res['created_hr']} HR ({acc_res['verified_hr']} verified), "
        f"+{job_res['created_jobs']} jobs ({job_res['existing_jobs']} already present), "
        f"+{tpl_res['created_form_templates']} form templates, "
        f"+{cfg_res['created_configs']} system configs, "
        f"ML bootstrapped={ml_bootstrapped}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Idempotently seed Mariwasa jobs, accounts, templates, configs, and ML baseline."
    )
    parser.add_argument(
        "--skip-ml",
        action="store_true",
        help="Skip bootstrapping ML baseline/model files",
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  Mariwasa Recruitment System — Unified Database & ML Seeder")
    print("=" * 64)
    asyncio.run(run_all_seeds(include_ml=not args.skip_ml))


if __name__ == "__main__":
    main()
