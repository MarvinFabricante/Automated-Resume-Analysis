"""
Baseline domain templates, taxonomy clusters, and historical recruitment data.
Used to train FastText embeddings and bootstrap the ML scoring classifier.
"""
from typing import List, Dict, Any

# Curated skill clusters for contextual FastText training
SKILL_CLUSTERS: Dict[str, List[str]] = {
    "frontend_web": [
        "react", "vue", "angular", "svelte", "typescript", "javascript",
        "html5", "css3", "tailwind", "redux", "nextjs", "webpack", "vite",
        "frontend", "ui", "ux", "responsive_design", "single_page_application"
    ],
    "backend_engineering": [
        "python", "fastapi", "flask", "django", "rest", "api", "microservices",
        "celery", "redis", "postgresql", "mysql", "sql", "backend", "orm",
        "sqlalchemy", "node", "express", "backend_architecture"
    ],
    "devops_cloud": [
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "ci_cd",
        "github_actions", "linux", "nginx", "terraform", "cloud", "devops",
        "monitoring", "prometheus", "grafana"
    ],
    "data_science_ml": [
        "machine_learning", "data_science", "nlp", "scikit_learn", "spacy",
        "pandas", "numpy", "gensim", "fasttext", "word2vec", "feature_engineering",
        "data_analysis", "statistics", "data_pipeline", "etl"
    ],
    "ceramics_manufacturing": [
        "kiln", "firing", "glaze", "slip_casting", "clay", "ceramic_tiles",
        "press_operator", "ball_mill", "thermal_processing", "quality_inspection",
        "manufacturing", "production_planning", "industrial_engineering", "safety",
        "kiln_operation", "machine_handling", "quality_checking", "safety_compliance",
        "lean_manufacturing", "5s", "kaizen", "gmp", "assembly_line"
    ],
    "quality_assurance_qc": [
        "quality_control", "quality_assurance", "product_inspection", "defect_reporting",
        "measuring_tools", "iso_9001", "statistical_process_control", "spc", "calibration",
        "laboratory_inspection", "six_sigma", "defect_inspection", "documentation"
    ],
    "accounting_finance": [
        "sap", "bookkeeping", "excel", "reconciliation", "accounts_payable",
        "accounts_receivable", "financial_reporting", "auditing", "quickbooks",
        "xero", "tax_compliance", "payroll", "billing", "invoicing", "vlookup"
    ],
    "sales_marketing_ecommerce": [
        "sales_experience", "communication", "customer_handling", "product_knowledge",
        "negotiation", "lead_generation", "quotation_preparation", "shopify",
        "ecommerce", "digital_marketing", "seo", "merchandising", "brand_management"
    ],
    "customer_service_bpo": [
        "customer_service", "chat_support", "email_support", "order_processing",
        "kustomer", "zendesk", "freshdesk", "stripe", "virtual_assistance",
        "data_encoding", "multitasking", "problem_solving", "time_management"
    ],
    "logistics_warehouse_delivery": [
        "warehouse", "inventory_management", "forklift_operation", "3pl_coordination",
        "shipping", "delivery", "dispatch", "stock_control", "material_handling",
        "logistics", "supply_chain"
    ],
    "maintenance_engineering": [
        "preventive_maintenance", "troubleshooting", "plc", "electrical_systems",
        "hydraulics", "pneumatics", "mechatronics", "hvac", "welding", "smaw",
        "autocad", "blueprint_reading", "equipment_repair"
    ],
    "mobile_development": [
        "react_native", "flutter", "ios", "android", "swift", "kotlin",
        "mobile_apps", "cross_platform"
    ],
    "management_hr": [
        "recruitment", "talent_acquisition", "hr_analytics", "sourcing",
        "interviewing", "payroll", "employee_relations", "onboarding", "hr_management",
        "hris"
    ],
}

JOB_TITLE_EQUIVALENCES: Dict[str, List[str]] = {
    "frontend_developer": [
        "frontend developer", "frontend engineer", "react developer",
        "vue developer", "ui engineer", "web developer"
    ],
    "backend_developer": [
        "backend developer", "backend engineer", "python developer",
        "api engineer", "software engineer backend", "python engineer"
    ],
    "fullstack_developer": [
        "fullstack developer", "fullstack engineer", "software engineer",
        "web engineer", "full stack developer"
    ],
    "devops_engineer": [
        "devops engineer", "cloud engineer", "site reliability engineer",
        "infrastructure engineer", "platform engineer"
    ],
    "ceramics_technician": [
        "ceramics technician", "kiln operator", "tile production specialist",
        "manufacturing operator", "ceramics process engineer", "production operator",
        "machine operator", "production supervisor"
    ],
    "qa_inspector": [
        "qa inspector", "qc inspector", "quality control analyst",
        "quality assurance inspector", "quality control inspector"
    ],
    "accounting_staff": [
        "accounting assistant", "accounting clerk", "bookkeeper",
        "accounts payable clerk", "finance assistant", "certified public accountant"
    ],
    "sales_officer": [
        "sales officer", "sales associate", "account executive",
        "promodiser", "merchandiser", "e-commerce specialist"
    ],
    "customer_service": [
        "customer service representative", "csr", "call center agent",
        "virtual assistant", "technical support representative", "data encoder"
    ],
    "maintenance_tech": [
        "maintenance technician", "electrical technician", "mechanical technician",
        "plant engineer", "plc technician"
    ],
    "hr_specialist": [
        "hr specialist", "recruiter", "talent acquisition specialist",
        "hr officer", "human resources associate", "hr generalist"
    ],
}

def generate_embedding_corpus() -> List[List[str]]:
    """
    Generate contextual sentence patterns for FastText training.
    Produces high co-occurrence between semantically equivalent skills
    (e.g., React and Vue) while maintaining distinct boundaries across domains.
    """
    corpus: List[List[str]] = []

    # 1. Intra-cluster contextual combinations
    for cluster_name, skills in SKILL_CLUSTERS.items():
        # Pairwise and n-gram combinations
        for i in range(len(skills)):
            for j in range(i + 1, min(i + 5, len(skills))):
                sent = [skills[i], skills[j], cluster_name]
                # Repeat to strengthen association
                for _ in range(6):
                    corpus.append(sent)

        # Full cluster windows
        for _ in range(15):
            corpus.append(list(skills))

    # 2. Tech stack combinations (Frontend frameworks are interchangeable)
    framework_patterns = [
        ["senior", "frontend", "engineer", "react", "vue", "javascript", "typescript", "ui", "web"],
        ["lead", "ui", "developer", "vue", "react", "component", "html5", "css3", "frontend"],
        ["fullstack", "developer", "react", "vue", "fastapi", "python", "postgresql"],
        ["modern", "web", "frontend", "react", "nextjs", "vue", "state_management", "redux"],
        ["frontend", "specialist", "vue", "react", "angular", "responsive_design", "web"],
        ["software", "engineer", "react", "vue", "typescript", "frontend", "spa"]
    ]
    for _ in range(30):
        corpus.extend(framework_patterns)

    # 3. Backend patterns
    backend_patterns = [
        ["backend", "engineer", "python", "fastapi", "flask", "django", "rest", "api"],
        ["senior", "python", "developer", "fastapi", "postgresql", "redis", "docker", "microservices"],
        ["software", "engineer", "backend", "django", "fastapi", "sql", "sqlalchemy"]
    ]
    for _ in range(30):
        corpus.extend(backend_patterns)

    # 4. Ceramics manufacturing patterns
    ceramics_patterns = [
        ["kiln", "operator", "ceramics", "thermal_processing", "firing", "tile_manufacturing"],
        ["ceramics", "production", "technician", "glaze", "clay", "ball_mill", "press_operator"],
        ["quality_inspection", "ceramics_tiles", "manufacturing", "industrial_engineering", "safety"]
    ]
    for _ in range(30):
        corpus.extend(ceramics_patterns)

    # 5. Job title patterns
    for role_cat, titles in JOB_TITLE_EQUIVALENCES.items():
        for t in titles:
            corpus.append(t.split())
            corpus.append([role_cat] + t.split())

    return corpus


def get_baseline_records() -> List[Dict[str, Any]]:
    """
    Returns curated historical applicant evaluation records.
    Contains diverse positive and negative recruitment outcomes with
    skills, titles, experience, and education comparisons.
    """
    return [
        # Positive: Strong React applicant for React/Frontend role
        {
            "resume_skills": ["react", "typescript", "redux", "html5", "css3", "javascript"],
            "job_skills": ["react", "typescript", "redux", "web"],
            "resume_title": "frontend developer",
            "job_title": "frontend engineer",
            "candidate_years": 4.0,
            "required_years": 3.0,
            "candidate_edu": "Bachelor of Science in Computer Science",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Positive: Vue applicant for Frontend role (Semantic overlap via Vue ~ React)
        {
            "resume_skills": ["vue", "javascript", "tailwind", "html5", "css3", "typescript"],
            "job_skills": ["react", "javascript", "frontend", "ui"],
            "resume_title": "ui web developer",
            "job_title": "frontend engineer",
            "candidate_years": 3.5,
            "required_years": 2.0,
            "candidate_edu": "BS Information Technology",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Positive: Strong Python/FastAPI backend developer
        {
            "resume_skills": ["python", "fastapi", "postgresql", "docker", "redis", "rest"],
            "job_skills": ["python", "django", "postgresql", "api"],
            "resume_title": "python backend engineer",
            "job_title": "backend developer",
            "candidate_years": 5.0,
            "required_years": 3.0,
            "candidate_edu": "Master of Science in Software Engineering",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Negative: Kiln operator applying for Frontend Engineer role
        {
            "resume_skills": ["kiln", "firing", "glaze", "thermal_processing", "slip_casting"],
            "job_skills": ["react", "typescript", "frontend", "redux"],
            "resume_title": "kiln operator",
            "job_title": "frontend engineer",
            "candidate_years": 6.0,
            "required_years": 3.0,
            "candidate_edu": "High School Diploma",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 0,
        },
        # Negative: Underqualified junior with 0 years for senior role
        {
            "resume_skills": ["html5", "css3"],
            "job_skills": ["react", "typescript", "redux", "nextjs", "architecture"],
            "resume_title": "intern",
            "job_title": "senior frontend engineer",
            "candidate_years": 0.5,
            "required_years": 5.0,
            "candidate_edu": "Associate Degree",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 0,
        },
        # Positive: Kiln / Ceramics operator applying for Ceramics Technician
        {
            "resume_skills": ["kiln", "firing", "glaze", "press_operator", "quality_inspection"],
            "job_skills": ["kiln", "firing", "ceramics", "safety"],
            "resume_title": "ceramics technician",
            "job_title": "kiln operator",
            "candidate_years": 4.0,
            "required_years": 2.0,
            "candidate_edu": "Vocational Diploma in Ceramic Technology",
            "required_edu": "Vocational / High School",
            "recruiter_action": 1,
        },
        # Negative: Frontend developer applying for Kiln Operator
        {
            "resume_skills": ["react", "javascript", "css3"],
            "job_skills": ["kiln", "thermal_processing", "ceramics", "firing"],
            "resume_title": "frontend developer",
            "job_title": "kiln operator",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "BS Computer Science",
            "required_edu": "Vocational / High School",
            "recruiter_action": 0,
        },
        # Positive: DevOps Engineer
        {
            "resume_skills": ["docker", "kubernetes", "aws", "ci_cd", "linux", "terraform"],
            "job_skills": ["docker", "k8s", "cloud", "aws", "devops"],
            "resume_title": "devops engineer",
            "job_title": "cloud infrastructure engineer",
            "candidate_years": 4.5,
            "required_years": 3.0,
            "candidate_edu": "BS Computer Engineering",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Negative: Candidate lacks required degree and experience for Lead Role
        {
            "resume_skills": ["python", "pandas"],
            "job_skills": ["python", "machine_learning", "nlp", "fastapi", "docker", "leadership"],
            "resume_title": "data analyst",
            "job_title": "lead ml engineer",
            "candidate_years": 1.0,
            "required_years": 6.0,
            "candidate_edu": "High School",
            "required_edu": "Master of Science",
            "recruiter_action": 0,
        },
        # Positive: Fullstack Developer with Vue and Python
        {
            "resume_skills": ["vue", "javascript", "python", "fastapi", "postgresql", "html5"],
            "job_skills": ["react", "python", "api", "sql", "fullstack"],
            "resume_title": "fullstack web developer",
            "job_title": "fullstack engineer",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "BS Information Systems",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Positive: HR Recruiter
        {
            "resume_skills": ["recruitment", "talent_acquisition", "sourcing", "interviewing", "onboarding"],
            "job_skills": ["recruitment", "sourcing", "talent_acquisition", "hr"],
            "resume_title": "talent acquisition specialist",
            "job_title": "hr recruiter",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "BS Psychology",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 1,
        },
        # Negative: HR Specialist applying for Backend Engineer
        {
            "resume_skills": ["recruitment", "payroll", "onboarding", "employee_relations"],
            "job_skills": ["python", "fastapi", "postgresql", "docker"],
            "resume_title": "hr officer",
            "job_title": "backend engineer",
            "candidate_years": 5.0,
            "required_years": 2.0,
            "candidate_edu": "BS Psychology",
            "required_edu": "Bachelor's Degree",
            "recruiter_action": 0,
        },
        # Positive: QA / QC Inspector for Quality Assurance role
        {
            "resume_skills": ["quality_control", "product_inspection", "defect_reporting", "iso_9001", "measuring_tools", "six_sigma"],
            "job_skills": ["quality_control", "product_inspection", "defect_reporting", "documentation", "measuring_tools"],
            "resume_title": "quality assurance inspector",
            "job_title": "qa inspector",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "Bachelor of Science in Industrial Technology",
            "required_edu": "Bachelor's in Engineering, Chemistry or a related field",
            "recruiter_action": 1,
        },
        # Negative: Delivery Rider / CSR applying for QA Inspector
        {
            "resume_skills": ["customer_service", "chat_support", "shopify", "order_processing"],
            "job_skills": ["quality_control", "product_inspection", "defect_reporting", "measuring_tools"],
            "resume_title": "customer service representative",
            "job_title": "qa inspector",
            "candidate_years": 1.0,
            "required_years": 2.0,
            "candidate_edu": "BS Computer Science",
            "required_edu": "Bachelor's in Engineering, Chemistry or a related field",
            "recruiter_action": 0,
        },
        # Positive: Accounting Assistant with SAP, Bookkeeping, Excel
        {
            "resume_skills": ["sap", "bookkeeping", "excel", "reconciliation", "accounts_payable", "quickbooks"],
            "job_skills": ["sap", "bookkeeping", "excel", "reconciliation", "accounts_payable"],
            "resume_title": "accounting clerk",
            "job_title": "accounting assistant",
            "candidate_years": 2.0,
            "required_years": 1.0,
            "candidate_edu": "Bachelor of Science in Accountancy",
            "required_edu": "BS Accountancy",
            "recruiter_action": 1,
        },
        # Negative: Customer Service / Delivery Rider applying for Accounting Assistant
        {
            "resume_skills": ["customer_service", "delivery", "time_management"],
            "job_skills": ["sap", "bookkeeping", "excel", "reconciliation", "accounts_payable"],
            "resume_title": "delivery rider",
            "job_title": "accounting assistant",
            "candidate_years": 1.0,
            "required_years": 1.0,
            "candidate_edu": "BS Computer Science",
            "required_edu": "BS Accountancy",
            "recruiter_action": 0,
        },
        # Positive: Sales Officer with Customer Handling, Negotiation, E-commerce
        {
            "resume_skills": ["sales_experience", "communication", "customer_handling", "product_knowledge", "negotiation"],
            "job_skills": ["sales_experience", "communication", "customer_handling", "product_knowledge", "negotiation"],
            "resume_title": "sales associate",
            "job_title": "sales officer",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "BS Business Administration Major in Marketing Management",
            "required_edu": "Any bachelor's degree",
            "recruiter_action": 1,
        },
        # Positive: Production Operator with Machine Handling, Kiln Operation, 5S
        {
            "resume_skills": ["kiln_operation", "machine_handling", "quality_checking", "safety_compliance", "5s", "kaizen"],
            "job_skills": ["kiln_operation", "machine_handling", "quality_checking", "safety_compliance"],
            "resume_title": "production operator",
            "job_title": "production operator",
            "candidate_years": 4.0,
            "required_years": 3.0,
            "candidate_edu": "Diploma in Industrial Technology - TESDA",
            "required_edu": "Senior high school graduate or vocational course",
            "recruiter_action": 1,
        },
        # Positive: Maintenance Technician with PLC, Electrical Systems, Preventive Maintenance
        {
            "resume_skills": ["preventive_maintenance", "troubleshooting", "plc", "electrical_systems", "hydraulics"],
            "job_skills": ["preventive_maintenance", "troubleshooting", "plc", "electrical_systems"],
            "resume_title": "electrical maintenance technician",
            "job_title": "maintenance technician",
            "candidate_years": 3.0,
            "required_years": 2.0,
            "candidate_edu": "BS Electrical Engineering",
            "required_edu": "Bachelor's or Vocational Diploma in Electrical/Mechanical",
            "recruiter_action": 1,
        },
        # Negative: Office Encoder applying for Industrial Maintenance Technician
        {
            "resume_skills": ["data_encoding", "customer_service", "chat_support"],
            "job_skills": ["preventive_maintenance", "troubleshooting", "plc", "electrical_systems"],
            "resume_title": "data encoder",
            "job_title": "maintenance technician",
            "candidate_years": 1.0,
            "required_years": 2.0,
            "candidate_edu": "Senior High School",
            "required_edu": "Vocational Diploma in Electrical/Mechanical",
            "recruiter_action": 0,
        },
    ]
