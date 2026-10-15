"""
Philippine & Global Certifications, Licenses & Eligibility Knowledge Base
========================================================================
Exhaustive localized taxonomy covering:
1. PRC Board Licenses & Post-Nominal Professional Credentials (RCE, RME, REE, RMP, RN, CPA, LPT)
2. Civil Service Commission (CSC) Eligibilities & Government Badges (CSE-Prof, PD 907, BOE, SME)
3. Other Regulatory Bodies (LTO Driver's Licenses, PNP-SOSIA Security Licenses, MARINA/STCW, NAPOLCOM)
4. TESDA National Certificates (NC I to NC IV) and Certificates of Competency (COC)
5. Safety, Health, Environment & Quality Standards (DOLE BOSH/COSH SO1-SO4, HIRAC, Red Cross BLS, ISO, HACCP)
6. Vendor & Global IT Certifications (AWS, Azure, GCP, CKA, Cisco, Oracle, CompTIA, Scrum, PMI)
7. Online Bootcamps & Training Providers (Coursera, Udemy, Sololearn, Ground Gurus, FreeCodeCamp, DICT)
"""

import os
import re
import json
import csv
from typing import Dict, Any, List, Optional, Set, Tuple


# ─── 1. Exhaustive Taxonomy Dictionary ────────────────────────────────────────
# Format: canonical_name -> { "category": str, "default_issuer": str, "aliases": list[str] }

PHILIPPINE_CERTIFICATIONS_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # ══════════════════════════════════════════════════════════════════════════
    # 1. PRC & PHILIPPINE GOVERNMENT LICENSES
    # ══════════════════════════════════════════════════════════════════════════
    "PRC Registered Civil Engineer": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Civil Engineer", "Licensed Civil Engineer",
            "Civil Engineering Board Exam Passer", "Civil Engineer Licensure Examination Passer",
            "Civil Engineering Licensure Exam", "Civil Engineering Board Exam", "RCE"
        ]
    },
    "PRC Registered Mechanical Engineer": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Mechanical Engineer", "Licensed Mechanical Engineer",
            "Mechanical Engineering Board Exam Passer", "Mechanical Engineer Licensure Exam Passer", "RME"
        ]
    },
    "PRC Registered Electrical Engineer": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Electrical Engineer", "Licensed Electrical Engineer",
            "Electrical Engineering Board Exam Passer", "Electrical Engineer Licensure Exam Passer", "REE"
        ]
    },
    "PRC Registered Master Plumber": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Master Plumber", "Licensed Master Plumber",
            "Master Plumber Licensure Examination Passer", "Master Plumber Board Exam Passer", "RMP"
        ]
    },
    "PRC Registered Master Electrician": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Master Electrician", "Licensed Master Electrician",
            "Master Electrician Licensure Exam Passer"
        ]
    },
    "PRC Registered Electronics Engineer": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Electronics Engineer", "Licensed Electronics Engineer",
            "Electronics Engineering Board Exam Passer", "Electronics Engineer Licensure Exam Passer", "ECE", "PECE"
        ]
    },
    "PRC Registered Nurse": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Nurse", "Licensed Nurse", "Nursing Board Exam Passer",
            "Nurse Licensure Examination Passer", "NLE Passer", "RN"
        ]
    },
    "PRC Certified Public Accountant": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Certified Public Accountant", "Certified Public Accountant (CPA)",
            "Accountancy Board Exam Passer", "CPA Licensure Examination Passer", "CPA"
        ]
    },
    "PRC Licensed Professional Teacher": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Licensed Professional Teacher", "Registered Professional Teacher",
            "Licensure Examination for Teachers Passer", "LET Passer", "LPT"
        ]
    },
    "PRC Registered Architect": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Architect", "Licensed Architect",
            "Architecture Board Exam Passer", "Architect Licensure Examination Passer", "ALE Passer", "RA"
        ]
    },
    "PRC Registered Pharmacist": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Pharmacist", "Licensed Pharmacist",
            "Pharmacy Board Exam Passer", "Pharmacist Licensure Exam Passer", "RPh"
        ]
    },
    "PRC Registered Medical Technologist": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Medical Technologist", "Licensed Medical Technologist",
            "Medical Technology Board Exam Passer", "Medical Technologist Licensure Exam Passer", "RMT"
        ]
    },
    "PRC Registered Chemist": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Chemist", "Licensed Chemist",
            "Chemist Licensure Examination Passer", "Chemistry Board Exam Passer", "RCh"
        ]
    },
    "PRC Registered Radiologic Technologist": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Radiologic Technologist", "Licensed Radiologic Technologist",
            "Radiologic Technology Board Exam Passer", "RRT"
        ]
    },
    "PRC Registered Criminologist": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Registered Criminologist", "Licensed Criminologist",
            "Criminology Board Exam Passer", "Criminologist Licensure Exam Passer", "RCrim"
        ]
    },
    "PRC Customs Broker Licensure Exam Passer": {
        "category": "PRC / Government License",
        "default_issuer": "PRC",
        "aliases": [
            "Customs Broker Licensure Exam", "Licensed Customs Broker",
            "Customs Broker Board Exam Passer", "CBLE"
        ]
    },
    "Civil Service Professional Eligibility": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": [
            "Career Service Professional Eligibility", "Civil Service Professional Eligibility",
            "Civil Service Professional", "CSC Professional Eligibility",
            "CSC Professional", "CSE-Prof", "CSE Professional", "Civil Service Exam Professional"
        ]
    },
    "Civil Service Sub-Professional Eligibility": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": [
            "Career Service Sub-Professional Eligibility", "Civil Service Sub-Professional Eligibility",
            "Civil Service Sub-Professional", "CSC Sub-Professional Eligibility",
            "CSC Sub-Professional", "CSE-SubProf", "CSE Sub-Professional", "Civil Service Exam Sub-Professional"
        ]
    },
    "Honor Graduate Eligibility (PD 907)": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": [
            "Honor Graduate Eligibility", "Honor Graduate Eligibility (PD 907)",
            "PD 907 Eligibility", "Presidential Decree 907 Eligibility", "PD 907"
        ]
    },
    "Barangay Official Eligibility (BOE)": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": ["Barangay Official Eligibility", "BOE Eligibility", "BOE"]
    },
    "Sanggunian Member Eligibility (SME)": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": ["Sanggunian Member Eligibility", "SME Eligibility"]
    },
    "Scientific and Technological Specialist Eligibility": {
        "category": "PRC / Government License",
        "default_issuer": "Civil Service Commission",
        "aliases": ["Scientific and Technological Specialist Eligibility", "STSE"]
    },
    "LTO Professional Driver's License": {
        "category": "PRC / Government License",
        "default_issuer": "LTO",
        "aliases": [
            "Professional Driver's License", "LTO Professional Driver's License",
            "LTO Driver's License", "Pro Driver's License", "Philippine Driver's License",
            "LTO Pro License", "Professional Driver's License (LTO)"
        ]
    },
    "LTO Non-Professional Driver's License": {
        "category": "PRC / Government License",
        "default_issuer": "LTO",
        "aliases": [
            "Non-Professional Driver's License", "LTO Non-Professional Driver's License",
            "Non-Pro Driver's License", "LTO Non-Pro License"
        ]
    },
    "PNP-SOSIA Security Guard License": {
        "category": "PRC / Government License",
        "default_issuer": "PNP-SOSIA",
        "aliases": [
            "Security Guard License", "SOSIA License", "Licensed Security Guard",
            "PNP-SOSIA Security Guard License", "PNP SOSIA License", "SOSIA Security Guard License",
            "Licensed Security Guard (SOSIA)"
        ]
    },
    "PNP-SOSIA Security Officer License": {
        "category": "PRC / Government License",
        "default_issuer": "PNP-SOSIA",
        "aliases": [
            "Security Officer License", "Licensed Security Officer",
            "PNP-SOSIA Security Officer License", "SOSIA Security Officer License"
        ]
    },
    "NAPOLCOM PNP Entrance Examination Passer": {
        "category": "PRC / Government License",
        "default_issuer": "NAPOLCOM",
        "aliases": [
            "NAPOLCOM PNP Entrance Examination", "NAPOLCOM Entrance Examination",
            "NAPOLCOM Passer", "NAPOLCOM PNP Entrance", "NAPOLCOM Eligibility"
        ]
    },
    "Penology Officer Examination (POE)": {
        "category": "PRC / Government License",
        "default_issuer": "CSC / BJMP",
        "aliases": [
            "Penology Officer Examination", "POE Passer", "BJMP Eligibility",
            "Penology Officer Exam"
        ]
    },
    "Fire Officer Examination (FOE)": {
        "category": "PRC / Government License",
        "default_issuer": "CSC / BFP",
        "aliases": [
            "Fire Officer Examination", "FOE Passer", "BFP Eligibility",
            "Fire Officer Exam"
        ]
    },
    "MARINA Standards of Training, Certification and Watchkeeping (STCW)": {
        "category": "PRC / Government License",
        "default_issuer": "MARINA",
        "aliases": [
            "STCW Certificate", "MARINA STCW", "STCW '95",
            "Standards of Training, Certification and Watchkeeping"
        ]
    },
    "Seafarer's Identification and Record Book (SIRB)": {
        "category": "PRC / Government License",
        "default_issuer": "MARINA",
        "aliases": [
            "SIRB", "Seaman's Book", "Seafarer's Book",
            "Seafarer's Identification and Record Book"
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 2. TESDA NATIONAL CERTIFICATES
    # ══════════════════════════════════════════════════════════════════════════
    "Food and Beverage Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Food and Beverage Services NC II", "FBS NC II", "TESDA FBS NC II",
            "Food & Beverage Services NC II", "Food and Beverage Services NC 2"
        ]
    },
    "Bread and Pastry Production NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Bread and Pastry Production NC II", "BPP NC II", "TESDA BPP NC II",
            "Bread & Pastry Production NC II", "Bread and Pastry Production NC 2"
        ]
    },
    "Commercial Cooking NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Commercial Cooking NC II", "Cookery NC II", "TESDA Cookery NC II",
            "Commercial Cooking NC 2", "Cookery NC 2"
        ]
    },
    "Bartending NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Bartending NC II", "TESDA Bartending NC II", "Bartending NC 2"]
    },
    "Housekeeping NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Housekeeping NC II", "TESDA Housekeeping NC II", "Housekeeping NC 2"]
    },
    "Front Office Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Front Office Services NC II", "TESDA Front Office NC II", "Front Office NC II"]
    },
    "Barista NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Barista NC II", "TESDA Barista NC II", "Barista NC 2"]
    },
    "Shielded Metal Arc Welding (SMAW) NC I": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Shielded Metal Arc Welding NC I", "SMAW NC I", "SMAW NC 1"]
    },
    "Shielded Metal Arc Welding (SMAW) NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Shielded Metal Arc Welding NC II", "SMAW NC II", "TESDA SMAW NC II",
            "SMAW NCII", "Shielded Metal Arc Welding (SMAW) NC II", "SMAW NC 2"
        ]
    },
    "Shielded Metal Arc Welding (SMAW) NC III": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Shielded Metal Arc Welding NC III", "SMAW NC III", "SMAW NC 3"]
    },
    "Gas Tungsten Arc Welding (GTAW / TIG) NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["GTAW NC II", "TIG Welding NC II", "GTAW NC 2", "TIG NC II"]
    },
    "Gas Metal Arc Welding (GMAW / MIG) NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["GMAW NC II", "MIG Welding NC II", "GMAW NC 2", "MIG NC II"]
    },
    "Electrical Installation and Maintenance NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Electrical Installation and Maintenance NC II", "EIM NC II",
            "TESDA EIM NC II", "Electrical Installation & Maintenance NC II", "EIM NC 2"
        ]
    },
    "Electrical Installation and Maintenance NC III": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Electrical Installation and Maintenance NC III", "EIM NC III", "EIM NC 3"]
    },
    "Electronic Products Assembly and Servicing NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Electronic Products Assembly and Servicing NC II", "EPAS NC II",
            "TESDA EPAS NC II", "EPAS NC 2"
        ]
    },
    "Computer Systems Servicing (CSS) NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Computer Systems Servicing NC II", "CSS NC II", "TESDA CSS NC II",
            "Computer Systems Servicing (CSS) NC II", "Computer Hardware Servicing NC II", "CHS NC II", "CSS NC 2"
        ]
    },
    "Automotive Servicing NC I": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Automotive Servicing NC I", "Automotive Servicing NC 1"]
    },
    "Automotive Servicing NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Automotive Servicing NC II", "TESDA Automotive Servicing NC II", "Automotive Servicing NC 2"]
    },
    "Heavy Equipment Operation (Forklift) NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Heavy Equipment Operation (Forklift) NC II", "Forklift Operation NC II",
            "HEO Forklift NC II", "Forklift NC II"
        ]
    },
    "Plumbing NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Plumbing NC II", "TESDA Plumbing NC II", "Plumbing NC 2"]
    },
    "Carpentry NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Carpentry NC II", "TESDA Carpentry NC II", "Carpentry NC 2"]
    },
    "Masonry NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Masonry NC II", "TESDA Masonry NC II", "Masonry NC 2"]
    },
    "Tile Setting NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Tile Setting NC II", "TESDA Tile Setting NC II", "Tile Setting NC 2"]
    },
    "RAC (PACU/CRE) Servicing NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "RAC Servicing NC II", "Aircon Servicing NC II",
            "Refrigeration and Air Conditioning Servicing NC II", "RAC NC II"
        ]
    },
    "Caregiving NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Caregiving NC II", "TESDA Caregiving NC II", "Caregiving NC 2"]
    },
    "Health Care Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Health Care Services NC II", "TESDA HCS NC II", "HCS NC II"]
    },
    "Pharmacy Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Pharmacy Services NC II", "TESDA Pharmacy Services NC II"]
    },
    "Emergency Medical Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Emergency Medical Services NC II", "EMS NC II", "TESDA EMS NC II"]
    },
    "Driving NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Driving NC II", "TESDA Driving NC II", "Driving NC 2"]
    },
    "Bookkeeping NC III": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": ["Bookkeeping NC III", "TESDA Bookkeeping NC III", "Bookkeeping NC 3"]
    },
    "Visual Graphic Design NC III": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Visual Graphic Design NC III", "VGD NC III", "TESDA VGD NC III",
            "Visual Graphic Design NC 3"
        ]
    },
    "Contact Center Services NC II": {
        "category": "TESDA National Certificate",
        "default_issuer": "TESDA",
        "aliases": [
            "Contact Center Services NC II", "TESDA Contact Center NC II",
            "CCS NC II", "Call Center NC II"
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 3. SAFETY & COMPLIANCE CERTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    "Basic Occupational Safety and Health (BOSH)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": [
            "Basic Occupational Safety and Health", "BOSH", "BOSH Certified",
            "DOLE BOSH", "BOSH Training"
        ]
    },
    "Basic Occupational Safety and Health for SO2 (BOSH SO2)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": [
            "BOSH SO2", "BOSH SO2 Certified", "Basic Occupational Safety and Health for SO2",
            "Safety Officer 2 (BOSH SO2)", "Safety Officer 2 (BOSH)", "BOSH for Safety Officer 2"
        ]
    },
    "Construction Occupational Safety and Health (COSH)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": [
            "Construction Occupational Safety and Health", "COSH", "COSH Certified",
            "DOLE COSH", "COSH Training", "Construction Safety Officer"
        ]
    },
    "Safety Officer 1 (SO1)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["Safety Officer 1", "SO1 Certified", "Safety Officer SO1", "SO1"]
    },
    "Safety Officer 2 (SO2)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["Safety Officer 2", "SO2 Certified", "Safety Officer SO2", "SO2"]
    },
    "Safety Officer 3 (SO3)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["Safety Officer 3", "SO3 Certified", "Safety Officer SO3", "SO3"]
    },
    "Safety Officer 4 (SO4)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["Safety Officer 4", "SO4 Certified", "Safety Officer SO4", "SO4"]
    },
    "Loss Control Management (LCM)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["Loss Control Management", "LCM Training", "DOLE LCM"]
    },
    "Hazard Identification, Risk Assessment and Determining Control (HIRAC)": {
        "category": "Safety & Compliance",
        "default_issuer": "DOLE-OSHC",
        "aliases": ["HIRAC", "HIRAC Training", "Hazard Identification, Risk Assessment and Determining Control"]
    },
    "Standard First Aid and Basic Life Support (BLS)": {
        "category": "Safety & Compliance",
        "default_issuer": "Philippine Red Cross",
        "aliases": [
            "Standard First Aid and Basic Life Support", "Standard First Aid and BLS",
            "First Aid and BLS", "Basic Life Support and First Aid",
            "Philippine Red Cross Standard First Aid", "Standard First Aid",
            "Basic Life Support (BLS)", "BLS and First Aid", "First Aid and CPR"
        ]
    },
    "Hazard Analysis Critical Control Point (HACCP)": {
        "category": "Safety & Compliance",
        "default_issuer": "Food Safety Authority",
        "aliases": [
            "Hazard Analysis Critical Control Point", "HACCP", "HACCP Certified",
            "HACCP Certification"
        ]
    },
    "ServSafe Food Protection Manager Certification": {
        "category": "Safety & Compliance",
        "default_issuer": "ServSafe / National Restaurant Association",
        "aliases": [
            "ServSafe", "ServSafe Certified", "ServSafe Food Protection Manager",
            "ServSafe Food Protection Manager Certification"
        ]
    },
    "ISO 9001:2015 Internal Auditor": {
        "category": "Safety & Compliance",
        "default_issuer": "ISO Registrar",
        "aliases": [
            "ISO 9001:2015 Internal Auditor", "ISO 9001 Internal Auditor",
            "ISO 9001 Lead Auditor", "ISO 9001:2015 Quality Management System Internal Auditor"
        ]
    },
    "ISO 14001 Environmental Management Internal Auditor": {
        "category": "Safety & Compliance",
        "default_issuer": "ISO Registrar",
        "aliases": ["ISO 14001 Internal Auditor", "ISO 14001", "ISO 14001 Lead Auditor"]
    },
    "ISO 45001 Occupational Health and Safety Internal Auditor": {
        "category": "Safety & Compliance",
        "default_issuer": "ISO Registrar",
        "aliases": ["ISO 45001 Internal Auditor", "ISO 45001", "ISO 45001 Lead Auditor"]
    },
    "Lean Six Sigma Yellow Belt": {
        "category": "IT & Professional Certification",
        "default_issuer": "Six Sigma PH",
        "aliases": [
            "Lean Six Sigma Yellow Belt", "Six Sigma Yellow Belt", "SSYB", "LSSYB",
            "Lean Six Sigma Yellow Belt Certification"
        ]
    },
    "Lean Six Sigma Green Belt": {
        "category": "IT & Professional Certification",
        "default_issuer": "Six Sigma PH",
        "aliases": [
            "Lean Six Sigma Green Belt", "Six Sigma Green Belt", "SSGB", "LSSGB",
            "Lean Six Sigma Green Belt Certification"
        ]
    },
    "Lean Six Sigma Black Belt": {
        "category": "IT & Professional Certification",
        "default_issuer": "Six Sigma PH",
        "aliases": [
            "Lean Six Sigma Black Belt", "Six Sigma Black Belt", "SSBB", "LSSBB",
            "Lean Six Sigma Black Belt Certification"
        ]
    },

    # ══════════════════════════════════════════════════════════════════════════
    # 4. IT & PROFESSIONAL CERTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    "AWS Certified Solutions Architect - Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": [
            "AWS Certified Solutions Architect - Associate", "AWS Solutions Architect Associate",
            "AWS SAA-C03", "AWS Certified Solutions Architect Associate"
        ]
    },
    "AWS Certified Solutions Architect - Professional": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": ["AWS Certified Solutions Architect - Professional", "AWS SAP-C02"]
    },
    "AWS Certified Cloud Practitioner": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": [
            "AWS Certified Cloud Practitioner", "AWS Cloud Practitioner",
            "AWS CLF-C01", "AWS CLF-C02"
        ]
    },
    "AWS Certified Developer - Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": ["AWS Certified Developer - Associate", "AWS Developer Associate", "AWS DVA-C02"]
    },
    "AWS Certified SysOps Administrator - Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": ["AWS Certified SysOps Administrator", "AWS SysOps Associate", "AWS SOA-C02"]
    },
    "AWS Certified DevOps Engineer - Professional": {
        "category": "IT & Professional Certification",
        "default_issuer": "AWS",
        "aliases": ["AWS Certified DevOps Engineer", "AWS DevOps Professional", "AWS DOP-C02"]
    },
    "Microsoft Certified: Azure Fundamentals (AZ-900)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Microsoft",
        "aliases": [
            "Microsoft Certified: Azure Fundamentals", "Azure Fundamentals",
            "AZ-900", "AZ 900"
        ]
    },
    "Microsoft Certified: Azure Administrator Associate (AZ-104)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Microsoft",
        "aliases": [
            "Microsoft Certified: Azure Administrator Associate", "Azure Administrator Associate",
            "AZ-104", "AZ 104"
        ]
    },
    "Microsoft Certified: Azure Solutions Architect Expert (AZ-305)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Microsoft",
        "aliases": [
            "Microsoft Certified: Azure Solutions Architect Expert", "Azure Solutions Architect",
            "AZ-305", "AZ 305"
        ]
    },
    "Google Cloud Certified Professional Cloud Architect": {
        "category": "IT & Professional Certification",
        "default_issuer": "Google Cloud",
        "aliases": [
            "Google Cloud Certified Professional Cloud Architect", "GCP Professional Cloud Architect",
            "Google Professional Cloud Architect"
        ]
    },
    "Google Cloud Certified Associate Cloud Engineer": {
        "category": "IT & Professional Certification",
        "default_issuer": "Google Cloud",
        "aliases": [
            "Google Cloud Certified Associate Cloud Engineer", "GCP Associate Cloud Engineer",
            "Google Associate Cloud Engineer"
        ]
    },
    "Certified Kubernetes Administrator (CKA)": {
        "category": "IT & Professional Certification",
        "default_issuer": "CNCF / Linux Foundation",
        "aliases": ["Certified Kubernetes Administrator", "CKA", "CKA Certified"]
    },
    "Certified Kubernetes Application Developer (CKAD)": {
        "category": "IT & Professional Certification",
        "default_issuer": "CNCF / Linux Foundation",
        "aliases": ["Certified Kubernetes Application Developer", "CKAD"]
    },
    "Certified Kubernetes Security Specialist (CKS)": {
        "category": "IT & Professional Certification",
        "default_issuer": "CNCF / Linux Foundation",
        "aliases": ["Certified Kubernetes Security Specialist", "CKS"]
    },
    "HashiCorp Certified: Terraform Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "HashiCorp",
        "aliases": [
            "HashiCorp Certified: Terraform Associate", "Terraform Associate",
            "HashiCorp Certified Terraform Associate", "HashiCorp Terraform"
        ]
    },
    "Docker Certified Associate (DCA)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Docker / Mirantis",
        "aliases": ["Docker Certified Associate", "DCA"]
    },
    "Oracle Certified Professional: Java SE Programmer (OCPJP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Oracle",
        "aliases": [
            "Oracle Certified Professional: Java SE Programmer", "OCPJP",
            "Oracle Certified Professional Java", "OCP Java"
        ]
    },
    "Oracle Certified Associate: Java Programmer (OCAJP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Oracle",
        "aliases": ["Oracle Certified Associate: Java Programmer", "OCAJP", "OCA Java"]
    },
    "Certified ScrumMaster (CSM)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Scrum Alliance",
        "aliases": ["Certified ScrumMaster", "Certified Scrum Master", "CSM"]
    },
    "Professional Scrum Master (PSM I)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Scrum.org",
        "aliases": ["Professional Scrum Master", "PSM I", "PSM 1", "PSM"]
    },
    "Certified Scrum Product Owner (CSPO)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Scrum Alliance",
        "aliases": ["Certified Scrum Product Owner", "CSPO"]
    },
    "Project Management Professional (PMP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "PMI",
        "aliases": ["Project Management Professional", "PMP", "PMP Certified"]
    },
    "PRINCE2 Foundation / Practitioner": {
        "category": "IT & Professional Certification",
        "default_issuer": "AXELOS / PeopleCert",
        "aliases": ["PRINCE2", "PRINCE2 Foundation", "PRINCE2 Practitioner"]
    },
    "ITIL 4 Foundation": {
        "category": "IT & Professional Certification",
        "default_issuer": "AXELOS / PeopleCert",
        "aliases": ["ITIL 4 Foundation", "ITIL v4", "ITIL Foundation", "ITIL"]
    },
    "Cisco Certified Network Associate (CCNA)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Cisco",
        "aliases": [
            "Cisco Certified Network Associate", "CCNA", "CCNA 200-301",
            "CCNA Routing and Switching", "CCNA Certified"
        ]
    },
    "Cisco Certified Network Professional (CCNP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Cisco",
        "aliases": ["Cisco Certified Network Professional", "CCNP", "CCNP Enterprise"]
    },
    "CompTIA A+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA A+", "CompTIA APlus", "A+ Certified"]
    },
    "CompTIA Network+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA Network+", "CompTIA NetworkPlus", "Network+ Certified"]
    },
    "CompTIA Security+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA Security+", "CompTIA SecurityPlus", "Security+ Certified"]
    },
    "CompTIA CySA+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA CySA+", "CompTIA Cybersecurity Analyst", "CySA+"]
    },
    "CompTIA PenTest+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA PenTest+", "PenTest+"]
    },
    "CompTIA Linux+": {
        "category": "IT & Professional Certification",
        "default_issuer": "CompTIA",
        "aliases": ["CompTIA Linux+", "Linux+"]
    },
    "Certified Information Systems Security Professional (CISSP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "(ISC)²",
        "aliases": ["Certified Information Systems Security Professional", "CISSP"]
    },
    "Certified Information Security Manager (CISM)": {
        "category": "IT & Professional Certification",
        "default_issuer": "ISACA",
        "aliases": ["Certified Information Security Manager", "CISM"]
    },
    "Certified Ethical Hacker (CEH)": {
        "category": "IT & Professional Certification",
        "default_issuer": "EC-Council",
        "aliases": ["Certified Ethical Hacker", "CEH", "CEH v12"]
    },
    "Offensive Security Certified Professional (OSCP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "OffSec",
        "aliases": ["Offensive Security Certified Professional", "OSCP"]
    },
    "Google Data Analytics Professional Certificate": {
        "category": "IT & Professional Certification",
        "default_issuer": "Google",
        "aliases": ["Google Data Analytics Professional Certificate", "Google Data Analytics Certificate"]
    },
    "Microsoft Certified: Power BI Data Analyst Associate (PL-300)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Microsoft",
        "aliases": [
            "Microsoft Certified: Power BI Data Analyst Associate", "Power BI Data Analyst Associate",
            "PL-300", "PL 300"
        ]
    },
    "Databricks Certified Data Engineer Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "Databricks",
        "aliases": ["Databricks Certified Data Engineer Associate", "Databricks Certified Data Engineer"]
    },
    "SnowPro Core Certified": {
        "category": "IT & Professional Certification",
        "default_issuer": "Snowflake",
        "aliases": ["SnowPro Core Certified", "SnowPro Core", "Snowflake SnowPro"]
    },
    "Microsoft Office Specialist: Excel Associate": {
        "category": "IT & Professional Certification",
        "default_issuer": "Microsoft / Certiport",
        "aliases": [
            "Microsoft Office Specialist: Excel Associate", "MOS Excel Associate",
            "Microsoft Office Specialist Excel", "MOS Excel 2019 Certified", "MOS Excel"
        ]
    },
    "Salesforce Certified Administrator": {
        "category": "IT & Professional Certification",
        "default_issuer": "Salesforce",
        "aliases": ["Salesforce Certified Administrator", "Salesforce Administrator"]
    },
    "Salesforce Certified Platform Developer I": {
        "category": "IT & Professional Certification",
        "default_issuer": "Salesforce",
        "aliases": ["Salesforce Certified Platform Developer I", "Salesforce Platform Developer I", "Salesforce PD1"]
    },
    "Autodesk Certified Professional: AutoCAD": {
        "category": "IT & Professional Certification",
        "default_issuer": "Autodesk",
        "aliases": [
            "Autodesk Certified Professional: AutoCAD", "AutoCAD Certified Professional",
            "Autodesk Certified AutoCAD", "AutoCAD Certified", "Autodesk Certified Professional: AutoCAD for Civil Engineering"
        ]
    },
    "Autodesk Certified Professional: Revit": {
        "category": "IT & Professional Certification",
        "default_issuer": "Autodesk",
        "aliases": ["Autodesk Certified Professional: Revit", "Revit Certified Professional", "Autodesk Certified Revit"]
    },
    "Certified Customer Service Professional (CCSP)": {
        "category": "IT & Professional Certification",
        "default_issuer": "Customer Service Institute",
        "aliases": ["Certified Customer Service Professional", "CCSP"]
    },
}


# ─── 2. Supporting Ontologies & Configuration ─────────────────────────────────

_KNOWN_ORGANIZATIONS = {
    "PRC": "PRC",
    "PROFESSIONAL REGULATION COMMISSION": "PRC",
    "TESDA": "TESDA",
    "CSC": "Civil Service Commission",
    "CIVIL SERVICE COMMISSION": "Civil Service Commission",
    "DOLE": "DOLE-OSHC",
    "OSHC": "DOLE-OSHC",
    "BWC": "DOLE-BWC",
    "DOLE-BWC": "DOLE-BWC",
    "DOLE-OSHC": "DOLE-OSHC",
    "LTO": "LTO",
    "LAND TRANSPORTATION OFFICE": "LTO",
    "PNP": "PNP-SOSIA",
    "SOSIA": "PNP-SOSIA",
    "PNP-SOSIA": "PNP-SOSIA",
    "MARINA": "MARINA",
    "PHILIPPINE RED CROSS": "Philippine Red Cross",
    "RED CROSS": "Philippine Red Cross",
    "AWS": "AWS",
    "AMAZON WEB SERVICES": "AWS",
    "MICROSOFT": "Microsoft",
    "CERTIPORT": "Certiport",
    "GOOGLE": "Google",
    "GOOGLE CLOUD": "Google Cloud",
    "CISCO": "Cisco",
    "CISCO SYSTEMS": "Cisco",
    "CISCO NETWORKING ACADEMY": "Cisco Networking Academy",
    "ORACLE": "Oracle",
    "COMPTIA": "CompTIA",
    "HASHICORP": "HashiCorp",
    "DOCKER": "Docker",
    "SCRUM.ORG": "Scrum.org",
    "SCRUM ALLIANCE": "Scrum Alliance",
    "PMI": "PMI",
    "PROJECT MANAGEMENT INSTITUTE": "PMI",
    "SOLOLEARN": "Sololearn",
    "GROUND GURUS": "Ground Gurus",
    "COURSERA": "Coursera",
    "UDEMY": "Udemy",
    "FREECODECAMP": "FreeCodeCamp",
    "DATACAMP": "DataCamp",
    "HUBSPOT": "HubSpot",
    "DICT": "DICT",
    "PCI INNOVATIONS": "PCI Innovations",
    "TUV RHEINLAND": "TUV Rheinland",
    "LINUX FOUNDATION": "Linux Foundation",
    "CNCF": "CNCF",
    "CLOUD NATIVE COMPUTING FOUNDATION": "CNCF",
    "NATIONAL ARCHIVES OF THE PHILIPPINES": "National Archives of the Philippines",
    "BPO ACADEMY": "BPO Academy",
    "SIX SIGMA PH": "Six Sigma PH",
    "AUTODESK": "Autodesk",
}

_POST_NOMINAL_MAP = {
    "RCE": "PRC Registered Civil Engineer",
    "RME": "PRC Registered Mechanical Engineer",
    "REE": "PRC Registered Electrical Engineer",
    "RMP": "PRC Registered Master Plumber",
    "RN": "PRC Registered Nurse",
    "LPT": "PRC Licensed Professional Teacher",
    "CPA": "PRC Certified Public Accountant",
    "ECE": "PRC Registered Electronics Engineer",
    "PECE": "PRC Registered Electronics Engineer",
    "RA": "PRC Registered Architect",
    "RCH": "PRC Registered Chemist",
    "RMT": "PRC Registered Medical Technologist",
    "RRT": "PRC Registered Radiologic Technologist",
    "RCRIM": "PRC Registered Criminologist",
}

_PROTECTED_PHRASES = [
    "Food and Beverage Services",
    "Bread and Pastry Production",
    "Heating, Ventilation, and Air Conditioning",
    "Standard First Aid and Basic Life Support",
    "Basic Life Support and First Aid",
    "First Aid and Basic Life Support",
    "First Aid and CPR",
    "Electrical Installation and Maintenance",
    "Electronic Products Assembly and Servicing",
    "Refrigeration and Air Conditioning",
    "Standards of Training, Certification and Watchkeeping",
    "Hazard Identification, Risk Assessment and Determining Control",
    "Conflict De-escalation & Complaint Handling",
    "Effective Business Writing and Executive Correspondence",
    "Records Management and 201 File Maintenance",
    "Cloud Native Computing Foundation",
]

_SECTION_HEADERS = {
    "Certifications": re.compile(
        r'^(?:certifications?|certificates?|credentials?|accreditations?|'
        r'professional\s+certifications?|certifications?\s*(?:&|and)\s*credentials?|'
        r'certifications?\s*(?:&|and)\s*licenses?)\b',
        re.IGNORECASE
    ),
    "Eligibility": re.compile(
        r'^(?:licenses?\s*(?:&|and)\s*certifications?|licenses?\s*(?:&|and)\s*eligibility|'
        r'eligibility(?:\s*&\s*licenses?)?|eligibility\s*&\s*professional\s*certifications?|'
        r'board\s+exams?|government\s+eligibility|licenses?|licensures?)\b',
        re.IGNORECASE
    ),
    "Seminars & Trainings": re.compile(
        r'^(?:seminars?\s*(?:&|and)\s*trainings?(?:\s+attended)?|trainings?\s*(?:&|and)\s*seminars?|'
        r'trainings?\s*attended|seminars?\s*attended|trainings?\s*(?:&|and)\s*workshops?|'
        r'workshops?\s*(?:&|and)\s*seminars?|bootcamps?|trainings?\s*(?:&|and)\s*bootcamps?|'
        r'trainings?|professional\s+development)\b',
        re.IGNORECASE
    ),
    "Education": re.compile(
        r'^(?:education|educational\s+background|educational\s+attainment|'
        r'academic\s+background)\b',
        re.IGNORECASE
    ),
    "Skills": re.compile(
        r'^(?:technical\s+skills?|skills?\s*(?:&|and)\s*abilities|core\s+competencies|'
        r'skills?|competencies)\b',
        re.IGNORECASE
    ),
    "Work Experience": re.compile(
        r'^(?:work\s+experience|professional\s+experience|employment\s+history|'
        r'experience)\b',
        re.IGNORECASE
    ),
}

_CREDENTIAL_MARKERS = [
    r'\bNC\s*(?:I|II|III|IV)\b',
    r'\bCOC(?:\s*\d+)?\b',
    r'\bCertified\b',
    r'\bLicense\b',
    r'\bPasser\b',
    r'\bEligibility\b',
    r'\bCertificate\b',
    r'\bAssociate\b',
    r'\bProfessional\b',
    r'\bAuditor\b',
    r'\bBelt\b',
    r'\bSpecialist\b',
    r'\bDriver\'?s?\s*License\b',
]


# ─── 3. External Dataset Ingestion Hook ───────────────────────────────────────

def load_external_certification_datasets(
    tesda_json_path: Optional[str] = None,
    custom_certs_csv: Optional[str] = None
) -> int:
    """
    Ingests external qualification datasets at runtime and adds them to taxonomy.
    """
    count = 0
    if tesda_json_path and os.path.exists(tesda_json_path):
        try:
            with open(tesda_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    title = item.get("qualification_title", "").strip()
                    if title and title not in PHILIPPINE_CERTIFICATIONS_TAXONOMY:
                        PHILIPPINE_CERTIFICATIONS_TAXONOMY[title] = {
                            "category": "TESDA National Certificate",
                            "default_issuer": "TESDA",
                            "aliases": [title, item.get("acronym", "").strip()]
                        }
                        count += 1
        except Exception:
            pass

    if custom_certs_csv and os.path.exists(custom_certs_csv):
        try:
            with open(custom_certs_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("name", "").strip()
                    cat = row.get("category", "IT & Professional Certification").strip()
                    iss = row.get("issuer", "Professional Organization").strip()
                    if name and name not in PHILIPPINE_CERTIFICATIONS_TAXONOMY:
                        alts = [a.strip() for a in row.get("aliases", "").split("|") if a.strip()]
                        PHILIPPINE_CERTIFICATIONS_TAXONOMY[name] = {
                            "category": cat,
                            "default_issuer": iss,
                            "aliases": [name] + alts
                        }
                        count += 1
        except Exception:
            pass

    return count
