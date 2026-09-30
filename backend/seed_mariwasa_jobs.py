import asyncio
import uuid
from sqlalchemy import text
from app.utils.database import AsyncSessionLocal

JOBS = [
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
        "experience_requirements": "2-3 years in manufacturing, preferably in ceramics"
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
        "experience_requirements": "3-5 years in QA/QC role"
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
        "experience_requirements": "1-2 years experience in plant maintenance"
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
        "experience_requirements": "2+ years in R&D, ceramics experience is a huge plus"
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
        "experience_requirements": "At least 2 years experience in field sales, preferably in construction materials"
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
        "experience_requirements": "7+ years in HR, with at least 3 years in a managerial role"
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
        "experience_requirements": "2 years in logistics or dispatch operations"
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
        "experience_requirements": "1-3 years in IT support"
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
        "experience_requirements": "Fresh graduates to 1 year experience"
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
        "experience_requirements": "2 years experience as a Safety Officer in a manufacturing setup"
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
        "experience_requirements": "1-2 years experience in marketing"
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
        "experience_requirements": "3 years experience in purchasing or procurement"
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
        "experience_requirements": "3-5 years supervisory experience in a manufacturing plant"
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
        "experience_requirements": "Portfolio demonstrating 2+ years of design work"
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
        "experience_requirements": "At least 1 year in customer service"
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
        "experience_requirements": "1-2 years experience as a forklift operator"
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
        "experience_requirements": "2-4 years experience in internal or external auditing"
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
        "experience_requirements": "3+ years in full-stack software development"
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
        "experience_requirements": "2+ years in data analysis"
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
        "experience_requirements": "7+ years in supply chain, with managerial experience"
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
        "experience_requirements": "3-5 years in construction or plant facilities"
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
        "experience_requirements": "3-5 years of corporate law practice"
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
        "experience_requirements": "2+ years as a PCO or in environmental compliance"
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
        "experience_requirements": "5+ years in FP&A, with supervisory experience"
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
        "experience_requirements": "2-3 years in recruitment"
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
        "experience_requirements": "5+ years in product development in manufacturing"
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
        "experience_requirements": "3-5 years supervisory experience in warehousing"
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
        "experience_requirements": "2-3 years in corporate training or organizational development"
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
        "experience_requirements": "2+ years in process improvement"
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
        "experience_requirements": "1 year experience in a manufacturing environment"
    }
]

from app.models.job_description import JobDescription, JobType

async def seed_jobs():
    async with AsyncSessionLocal() as session:
        count = 0
        for job_data in JOBS:
            job_id = str(uuid.uuid4())
            
            # Map string to enum
            type_map = {
                "Full-Time": JobType.FULL_TIME,
                "Part-Time": JobType.PART_TIME,
                "Contract": JobType.CONTRACT,
                "Freelance": JobType.FREELANCE,
                "Internship": JobType.INTERNSHIP,
            }
            job_enum = type_map.get(job_data["job_type"], JobType.FULL_TIME)
            
            new_job = JobDescription(
                job_id=job_id,
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
                is_active=True
            )
            session.add(new_job)
            count += 1
            
        await session.commit()
        print(f"Successfully seeded {count} jobs for Mariwasa Siam Ceramics Incorporated.")

if __name__ == "__main__":
    asyncio.run(seed_jobs())
