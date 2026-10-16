"""
Comprehensive Unit Tests for Philippine Certifications, Licenses & Eligibility Extractor
========================================================================================
Validates:
1. Multi-item line splitting preserving composite course names
2. Header post-nominal title extraction (RCE, RMP, RN, LPT, CPA, etc.)
3. Layer 1: Gazetteer exact matching and canonicalization
4. Layer 2: Dynamic regex catchers (TESDA NC/COC, PRC board exam, CSC, bootcamps)
5. Layer 3: Bullet-level fallback inside dedicated sections
6. Layer 4: Metadata enrichment (issuing org, issue date, status, license numbers, ratings)
7. Full 4-profile end-to-end multi-credential extraction
8. JSON Schema and category summary validation
"""

import pytest
from app.extractors.content.certifications_extractor import (
    PhilippineCertificationsExtractor,
    get_certifications_extractor,
    extract_structured_certifications,
    extract_certifications,
    split_compound_cert_line,
    is_header_line,
)


@pytest.fixture
def extractor():
    return get_certifications_extractor()


# ─── 1. Multi-Item Line Splitter Tests ─────────────────────────────────────────

def test_split_compound_cert_line_tesda_composite():
    line = "TESDA Food and Beverage Services NC II & Bread and Pastry Production NC II (Issued: June 2022)"
    items = split_compound_cert_line(line)
    assert len(items) == 2
    assert "Food and Beverage Services NC II" in items[0]
    assert "Bread and Pastry Production NC II" in items[1]


def test_split_compound_cert_line_pipe_delimiter():
    line = "Civil Engineering Board Exam Passer | RCE License No. 0154321 | BOSH SO2 Certified"
    items = split_compound_cert_line(line)
    assert len(items) == 3
    assert items[0] == "Civil Engineering Board Exam Passer"
    assert items[1] == "RCE License No. 0154321"
    assert items[2] == "BOSH SO2 Certified"


def test_preserve_unified_organization_slash():
    # Cloud Native Computing Foundation / Linux Foundation should not split into two certificates
    line = "Certified Kubernetes Administrator (CKA) - Cloud Native Computing Foundation / Linux Foundation"
    items = split_compound_cert_line(line)
    assert len(items) == 1
    assert "Linux Foundation" in items[0]


def test_preserve_intra_word_hyphens():
    line = "Conflict De-escalation & Complaint Handling Masterclass - BPO Academy"
    items = split_compound_cert_line(line)
    assert len(items) == 1
    assert "Conflict De-escalation" in items[0]


# ─── 2. Header Post-Nominals Tests ─────────────────────────────────────────────

def test_header_post_nominal_extraction(extractor):
    resume = """
Engr. Juan Dela Cruz, RCE, RMP
Makati City | jdelacruz@example.com

SUMMARY
Experienced Civil Engineer.
"""
    result = extractor.extract(resume)
    canonicals = [c["canonical_name"] for c in result["certifications"]]
    assert "PRC Registered Civil Engineer" in canonicals
    assert "PRC Registered Master Plumber" in canonicals

    rce = next(c for c in result["certifications"] if c["canonical_name"] == "PRC Registered Civil Engineer")
    assert rce["source_section"] == "Header"
    assert rce["category"] == "PRC / Government License"
    assert "RCE" in rce["credential_id_or_details"]


def test_nursing_and_teaching_post_nominals(extractor):
    resume = """
Maria Santos, RN, LPT
Manila, Philippines | maria@example.com
"""
    result = extractor.extract(resume)
    canonicals = [c["canonical_name"] for c in result["certifications"]]
    assert "PRC Registered Nurse" in canonicals
    assert "PRC Licensed Professional Teacher" in canonicals


# ─── 3. Dynamic Regex Catchers (Layer 2) ───────────────────────────────────────

def test_dynamic_tesda_catcher(extractor):
    resume = """
CERTIFICATIONS
- Shielded Metal Arc Welding NC I (Issued: 2021)
- Organic Agriculture Production NC II
- Heavy Equipment Operation (Hydraulic Excavator) NC II
- Certificate of Competency in Cookery
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] >= 3
    for c in result["certifications"]:
        assert c["category"] == "TESDA National Certificate"
        assert c["issuing_organization"] == "TESDA"


def test_dynamic_prc_board_exam_catcher(extractor):
    resume = """
LICENSES & ELIGIBILITY
- Chemical Engineering Board Exam Passer (Rating: 84.50%, PRC License No. 009876)
- Geodetic Engineer Licensure Examination Passer
"""
    result = extractor.extract(resume)
    canonicals = [c["canonical_name"] for c in result["certifications"]]
    assert any("Chemical" in name for name in canonicals)
    assert any("Geodetic" in name for name in canonicals)
    chem = next(c for c in result["certifications"] if "Chemical" in c["canonical_name"])
    assert chem["category"] == "PRC / Government License"
    assert "PRC License No. 009876" in chem["credential_id_or_details"]
    assert "Rating: 84.50%" in chem["credential_id_or_details"]


def test_dynamic_civil_service_catcher(extractor):
    resume = """
GOVERNMENT ELIGIBILITY
- Career Service Professional Eligibility (Civil Service Commission, Passed March 2021)
- Career Service Sub-Professional Examination Passer
- Barangay Official Eligibility
- NAPOLCOM Promotional Examination Passer
"""
    result = extractor.extract(resume)
    canonicals = [c["canonical_name"] for c in result["certifications"]]
    assert any("Civil Service Professional" in name for name in canonicals)
    assert any("Civil Service Sub-Professional" in name for name in canonicals)
    assert any("Barangay Official" in name for name in canonicals)
    assert any("NAPOLCOM" in name for name in canonicals)


def test_dynamic_bootcamp_catcher(extractor):
    resume = """
TRAININGS AND SEMINARS
- Certificate of Completion in Full Stack Web Development - Ground Gurus (120 Hours, 2023)
- Certificate of Participation in Reactive Microservices with Spring Boot - PCI Innovations
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 2
    c1 = next(c for c in result["certifications"] if "Full Stack Web Development" in c["canonical_name"])
    assert c1["issuing_organization"] == "Ground Gurus"
    assert c1["issue_date"] == "2023"
    assert "120 Hours" in c1["credential_id_or_details"]

    c2 = next(c for c in result["certifications"] if "Reactive Microservices" in c["canonical_name"])
    assert c2["issuing_organization"] == "PCI Innovations"


# ─── 4. Bullet-Level Fallback (Layer 3) ────────────────────────────────────────

def test_bullet_level_fallback_extraction(extractor):
    resume = """
SEMINARS & TRAININGS ATTENDED
- Effective Business Writing and Executive Correspondence Workshop (16 Hours, 2023)
- Conflict De-escalation & Complaint Handling Masterclass - BPO Academy
- Records Management and 201 File Maintenance Training - National Archives of the Philippines
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 3
    canonicals = [c["canonical_name"] for c in result["certifications"]]
    assert "Effective Business Writing and Executive Correspondence Workshop" in canonicals
    assert "Conflict De-escalation & Complaint Handling Masterclass" in canonicals
    assert "Records Management and 201 File Maintenance Training" in canonicals

    c_conf = next(c for c in result["certifications"] if "Conflict" in c["canonical_name"])
    assert c_conf["issuing_organization"] == "BPO Academy"
    assert c_conf["extraction_method"] == "Section_Bullet_Parse"


# ─── 5. Metadata Enrichment Tests (Layer 4) ───────────────────────────────────

def test_metadata_dates_and_license_numbers(extractor):
    resume = """
CERTIFICATIONS
- Housekeeping NC II - TESDA Rizal Provincial Training Center (Cert No. 22040102001, Issued: 2021)
- LTO Professional Driver's License (Restriction 1, 2, 3 / DL Code A, B) - Valid until 2028
- AWS Certified Solutions Architect - Associate (Validation: AWS-SAA-908123, Valid until Nov 2026)
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 3

    hk = next(c for c in result["certifications"] if "Housekeeping" in c["canonical_name"])
    assert hk["issue_date"] == "2021"
    assert "Cert No. 22040102001" in hk["credential_id_or_details"]

    lto = next(c for c in result["certifications"] if "Driver" in c["canonical_name"])
    assert lto["expiration_or_status"] == "Valid until 2028"
    assert "Restriction 1, 2, 3 / DL Code A, B" in lto["credential_id_or_details"]

    aws = next(c for c in result["certifications"] if "AWS" in c["canonical_name"])
    assert aws["expiration_or_status"] == "Valid until 2026-11"
    assert "Validation: AWS-SAA-908123" in aws["credential_id_or_details"]


# ─── 6. End-to-End Tests Across 4 Workforces ───────────────────────────────────

def test_profile_1_blue_collar_tesda(extractor):
    resume = """
ALEXANDER BAUTISTA
Calamba City, Laguna | 09171234567 | alex.bautista@gmail.com

CERTIFICATIONS & LICENSES
- TESDA Food and Beverage Services NC II & Bread and Pastry Production NC II (Issued: June 2022)
- Housekeeping NC II - TESDA Rizal Provincial Training Center (Cert No. 22040102001, Issued: 2021)
- LTO Professional Driver's License (Restriction 1, 2, 3 / DL Code A, B) - Valid until 2028
- Standard First Aid and Basic Life Support (BLS) - Philippine Red Cross (24 Hours, 2023)
- PNP-SOSIA Security Guard License (License No. SG-8891234, Active)
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 6
    summary = result["summary_by_category"]
    assert summary["tesda_national_certificates"] == 3
    assert summary["prc_and_government_licenses"] == 2
    assert summary["safety_and_compliance_certs"] == 1


def test_profile_2_civil_engineering_safety(extractor):
    resume = """
Engr. Juanito Dela Cruz, RCE, RMP
Makati City, Metro Manila | 09171234567 | jdelacruz.ce@gmail.com

LICENSES AND ELIGIBILITY
- PRC Registered Civil Engineer (Civil Engineering Board Exam Passer, Rating: 85.60%, PRC License No. 0154321)
- PRC Registered Master Plumber (Master Plumber Licensure Examination Passer, Reg. No. 008921)
- Basic Occupational Safety and Health for SO2 (BOSH SO2) - DOLE-BWC Accredited (40 Hours, 2023)
- Construction Occupational Safety and Health (COSH Certified, Safety Officer 2)
- ISO 9001:2015 Quality Management System Internal Auditor - TUV Rheinland
- Autodesk Certified Professional: AutoCAD for Civil Engineering
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] >= 6
    summary = result["summary_by_category"]
    assert summary["prc_and_government_licenses"] == 2
    assert summary["safety_and_compliance_certs"] >= 3


def test_profile_3_bpo_admin_government(extractor):
    resume = """
CLARISSE MENDOZA
Quezon City, Metro Manila | 09181234567 | clarisse.mendoza@gmail.com

ELIGIBILITY & PROFESSIONAL CERTIFICATIONS
- Career Service Professional Eligibility (Civil Service Commission, Rating: 86.42%, Passed March 2021)
- Honor Graduate Eligibility (PD 907) - Civil Service Commission
- Microsoft Office Specialist: Excel Associate (MOS Excel 2019 Certified) - Certiport
- Lean Six Sigma Yellow Belt Certification (SSYB) - Six Sigma PH (2022)
- Certified Customer Service Professional (CCSP)

SEMINARS & TRAININGS ATTENDED
- Effective Business Writing and Executive Correspondence Workshop (16 Hours, 2023)
- Conflict De-escalation & Complaint Handling Masterclass - BPO Academy
- Records Management and 201 File Maintenance Training - National Archives of the Philippines
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 8
    summary = result["summary_by_category"]
    assert summary["prc_and_government_licenses"] == 2
    assert summary["it_and_professional_certs"] == 3
    assert summary["seminars_and_training_certificates"] == 3


def test_profile_4_software_developer_cloud(extractor):
    resume = """
ALEXANDER REYES
Taguig City, Metro Manila | alex.reyes@gmail.com

CERTIFICATIONS & CREDENTIALS
- AWS Certified Solutions Architect - Associate (Validation: AWS-SAA-908123, Valid until Nov 2026)
- Certified Kubernetes Administrator (CKA) - Cloud Native Computing Foundation / Linux Foundation
- Cisco Certified Network Associate (CCNA 200-301) - Cisco Systems (Active)
- HashiCorp Certified: Terraform Associate (003)

TRAININGS & BOOTCAMPS
- Certificate of Completion in Java Web Development Bootcamp - Ground Gurus (120 Hours, 2023)
- Certificate of Participation in Reactive Microservices with Spring Boot - PCI Innovations
- Sololearn Python Intermediate Certification (Certificate ID: SL-778899)
- FreeCodeCamp Responsive Web Design Certification
"""
    result = extractor.extract(resume)
    assert result["total_certifications_count"] == 8
    summary = result["summary_by_category"]
    assert summary["it_and_professional_certs"] == 5
    assert summary["seminars_and_training_certificates"] == 3


def test_backward_compatible_string_output():
    text = "Civil Engineering Board Exam Passer | BOSH SO2 Certified"
    str_out = extract_certifications(text)
    assert isinstance(str_out, str)
    assert "PRC Registered Civil Engineer" in str_out
