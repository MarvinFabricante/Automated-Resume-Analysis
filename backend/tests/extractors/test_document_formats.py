import os
import tempfile
import pytest
import docx
import fitz

from app.extractors.file.file_extractor import extract_file_content
from app.extractors.file.txt_extractor import extract_text_from_txt
from app.extractors.file.pdf_extractor import extract_text_from_pdf
from app.extractors.file.docx_extractor import extract_text_from_docx
from app.extractors.resume_processor import process_resume
from app.utils.file_validator import validate_file_content, is_executable_binary



@pytest.fixture
def temp_files():
    created = []

    def _track(path):
        created.append(path)
        return path

    yield _track

    for p in created:
        if os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


def test_txt_extraction_utf8(temp_files):
    """Ensure standard UTF-8 text files are accepted and parsed."""
    content = (
        "JUAN CARLOS SANTOS\n"
        "Email: juan.santos@gmail.com\n"
        "Phone: 09181234567\n"
        "Location: Quezon City, Metro Manila\n\n"
        "SUMMARY\n"
        "Full stack software engineer with 5 years experience in Python and React.\n\n"
        "TECHNICAL SKILLS\n"
        "Python, FastAPI, TypeScript, React, Docker, PostgreSQL\n\n"
        "WORK EXPERIENCE\n"
        "Senior Developer\n"
        "Tech Innovations Inc. | Oct 2021 - Present\n"
        "• Developed high-volume microservices\n\n"
        "EDUCATION\n"
        "University of the Philippines Diliman\n"
        "BS Computer Science\n"
        "2017 - 2021\n"
    )

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
        f.write(content.encode("utf-8"))
        txt_path = temp_files(f.name)

    extracted_text = extract_text_from_txt(txt_path)
    assert "JUAN CARLOS SANTOS" in extracted_text
    assert "juan.santos@gmail.com" in extracted_text

    # End-to-end process_resume
    res = process_resume(txt_path, "txt")
    assert res.get("candidate_name") == "Juan Carlos Santos"
    assert res.get("candidate_email") == "juan.santos@gmail.com"
    assert "0918" in res.get("candidate_phone", "")
    assert len(res.get("skills_list", [])) >= 3
    assert res.get("highest_educational_attainment") == "Tertiary / College"
    assert len(res.get("work_experiences", [])) >= 1


def test_txt_extraction_with_bom(temp_files):
    """Ensure UTF-8 with BOM (common on Windows Notepad) is accepted and parsed without corrupting first word."""
    content = "ROBERTO GOMEZ\nEmail: roberto@gmail.com\nPhone: 09171234567\nSKILLS: Java, Spring Boot"
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
        f.write(content.encode("utf-8-sig"))
        txt_path = temp_files(f.name)

    res = process_resume(txt_path, "txt")
    assert res.get("candidate_name") == "Roberto Gomez"
    assert res.get("candidate_email") == "roberto@gmail.com"


def test_txt_extraction_latin1_encoding(temp_files):
    """Ensure non-UTF8 encodings like Latin-1 / Windows-1252 are automatically decoded."""
    content = "RENÉ DELA VEGA\nEmail: rene@gmail.com\nPhone: 09171234567\nSKILLS: Python, SQL"
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
        f.write(content.encode("iso-8859-1"))
        txt_path = temp_files(f.name)

    extracted_text = extract_text_from_txt(txt_path)
    assert "RENÉ DELA VEGA" in extracted_text
    res = process_resume(txt_path, "txt")
    assert "René" in res.get("candidate_name", "") or "Rene" in res.get("candidate_name", "")


def test_magic_bytes_detection_without_extension(temp_files):
    """Ensure files missing extensions or with uppercase/unknown extensions are auto-detected via magic bytes."""
    # 1. PDF magic bytes
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "MARIA CLARA | maria@gmail.com | 09171234567\nSKILLS: Python, React")
    pdf_bytes = doc.tobytes()
    doc.close()

    with tempfile.NamedTemporaryFile(suffix="", mode="wb", delete=False) as f:
        f.write(pdf_bytes)
        no_ext_path = temp_files(f.name)

    extracted = extract_file_content(no_ext_path, "")
    assert "MARIA CLARA" in extracted
    assert "maria@gmail.com" in extracted

    # 2. DOCX magic bytes
    w_doc = docx.Document()
    w_doc.add_paragraph("CRISOSTOMO IBARRA | ibarra@gmail.com | 09171234567")
    w_doc.add_paragraph("SKILLS: Leadership, Communication, Python")
    with tempfile.NamedTemporaryFile(suffix="", mode="wb", delete=False) as f:
        docx_no_ext = temp_files(f.name)
    w_doc.save(docx_no_ext)

    extracted_docx = extract_file_content(docx_no_ext, "unknown")
    assert "CRISOSTOMO IBARRA" in extracted_docx
    assert "ibarra@gmail.com" in extracted_docx


def test_cross_format_resilience(temp_files):
    """Verify that if a DOCX file is mistakenly uploaded with .txt extension, the extractor recovers."""
    w_doc = docx.Document()
    w_doc.add_paragraph("ANDRES BONIFACIO | andres@gmail.com | 09171234567")
    w_doc.add_paragraph("WORK EXPERIENCE\nKatipunan Leader | 1892 - 1897")
    w_doc.add_paragraph("SKILLS: Strategy, Organization, Public Speaking")

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
        misnamed_path = temp_files(f.name)
    w_doc.save(misnamed_path)

    res = process_resume(misnamed_path, "txt")
    assert res.get("candidate_name") == "Andres Bonifacio"
    assert res.get("candidate_email") == "andres@gmail.com"


def test_tc_res_003_upload_valid_txt_r3(temp_files):
    """
    Test Case: TC-RES-003
    Module: Resume Processing
    Requirement: REQ001
    Scenario: Upload Valid TXT
    Steps: Upload R3
    Expected Result: Accepted and Text Extracted
    """
    r3_resume_content = (
        "JOSE P. RIZAL\n"
        "Ophthalmologist & Lead Software Architect\n"
        "Email: jose.rizal@gmail.com\n"
        "Phone: +63 917 123 4567\n"
        "Address: Calamba, Laguna, Calabarzon\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Dedicated architect and polyglot engineer with extensive leadership experience.\n\n"
        "WORK EXPERIENCE\n"
        "Lead Solutions Architect\n"
        "La Liga Innovations Inc. | Calamba, Laguna\n"
        "January 2019 - Present\n"
        "• Designed scalable cloud microservices using Python, FastAPI, and PostgreSQL.\n"
        "• Managed distributed data stores with Redis and optimized throughput.\n\n"
        "EDUCATION\n"
        "Doctor of Medicine / BS Computer Science\n"
        "University of Santo Tomas\n"
        "Graduated: 2015\n\n"
        "SKILLS & COMPETENCIES\n"
        "Python, FastAPI, JavaScript, TypeScript, React, PostgreSQL, Docker, Git, Redis\n\n"
        "CERTIFICATIONS\n"
        "AWS Certified Solutions Architect\n"
    )

    # 1. Test when saved as R3.txt
    with tempfile.NamedTemporaryFile(suffix="_R3.txt", mode="wb", delete=False) as f:
        f.write(r3_resume_content.encode("utf-8"))
        r3_txt_path = temp_files(f.name)

    extracted_text = extract_file_content(r3_txt_path, "txt")
    assert "JOSE P. RIZAL" in extracted_text
    assert "jose.rizal@gmail.com" in extracted_text

    result_txt = process_resume(r3_txt_path, "txt")
    assert result_txt, "Valid TXT resume R3 must be accepted and parsed"
    assert result_txt.get("candidate_name") == "Jose P. Rizal"
    assert result_txt.get("candidate_email") == "jose.rizal@gmail.com"
    assert "917" in result_txt.get("candidate_phone", "")
    assert len(result_txt.get("skills_list", [])) >= 5
    assert len(result_txt.get("work_experiences", [])) >= 1
    assert len(result_txt.get("education_entries", [])) >= 1
    assert "raw_text" in result_txt and len(result_txt["raw_text"]) > 100

    # 2. Test when file is named just "R3" without extension
    with tempfile.NamedTemporaryFile(suffix="_R3", mode="wb", delete=False) as f:
        f.write(r3_resume_content.encode("utf-8"))
        r3_no_ext_path = temp_files(f.name)

    result_no_ext = process_resume(r3_no_ext_path, "")
    assert result_no_ext, "Valid TXT resume R3 without extension must be accepted and parsed"
    assert result_no_ext.get("candidate_name") == "Jose P. Rizal"
    assert result_no_ext.get("candidate_email") == "jose.rizal@gmail.com"


def test_tc_res_008_disguised_exe_rejected(temp_files):
    """
    Test Case: TC-RES-008
    Module: Resume Processing
    Requirement: REQ002
    Scenario: Rename an .exe to .pdf and upload
    Steps: Rejected by content check, not just extension
    Expected Result: File is rejected prior to processing; no text extracted
    """
    # Standard Windows PE executable header: "MZ" + DOS stub
    exe_payload = (
        b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
        b"\xb8\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00"
        b"This program cannot be run in DOS mode.\r\r\n$"
        + (b"\x00" * 200)
    )

    # 1. Content check on raw bytes with fake .pdf filename
    is_valid, reason = validate_file_content(exe_payload, "malicious_resume.pdf")
    assert not is_valid, "Executable disguised as .pdf must fail content validation"
    assert "rejected by content check" in reason.lower()
    assert "executable" in reason.lower()

    # 2. Content check on raw bytes with fake .docx filename
    is_valid_docx, reason_docx = validate_file_content(exe_payload, "malicious_resume.docx")
    assert not is_valid_docx
    assert "rejected by content check" in reason_docx.lower()

    # 3. Content check on raw bytes with fake .txt filename
    is_valid_txt, reason_txt = validate_file_content(exe_payload, "malicious_resume.txt")
    assert not is_valid_txt
    assert "rejected by content check" in reason_txt.lower()

    # 4. Verify Linux ELF binary disguised as .pdf is also rejected
    elf_payload = b"\x7fELF\x02\x01\x01\x00" + (b"\x00" * 128)
    is_valid_elf, reason_elf = validate_file_content(elf_payload, "trojan.pdf")
    assert not is_valid_elf
    assert "rejected by content check" in reason_elf.lower()

    # 5. Verify file extractor does not fall back to plain-text decoding of an executable
    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False) as f:
        f.write(exe_payload)
        fake_pdf_file = temp_files(f.name)

    extracted_text = extract_file_content(fake_pdf_file, "pdf")
    assert extracted_text == "", "Disguised executable must yield empty text from extractor"

    # 6. Verify resume processor rejects and returns empty dictionary
    parsed_resume = process_resume(fake_pdf_file, "pdf")
    assert parsed_resume == {}, "Disguised executable must return empty parsed result"


def test_tc_res_009_review_before_submit_preview_and_replace(temp_files):
    """
    Test Case: TC-RES-009
    Module: Resume Processing
    Requirement: REQ003
    Scenario: Review before submit
    Steps: After upload, open preview
    Expected Result: Applicant can view and replace the resume before submitting
    """
    # 1. Initial upload: Applicant uploads first resume (R1)
    r1_content = (
        "JUAN DELA CRUZ\n"
        "Email: juan.delacruz@gmail.com\n"
        "Phone: +63 917 123 4567\n"
        "Location: Makati City, Philippines\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Senior Quality Assurance Engineer with 6 years of experience in ceramic manufacturing.\n\n"
        "EXPERIENCE\n"
        "QA Lead | Mariwasa Ceramics | 2020 - Present\n"
        "- Oversee quality inspection processes and ceramic tile standard adherence.\n\n"
        "EDUCATION\n"
        "Bachelor of Science in Materials Engineering | Mapua University\n\n"
        "SKILLS\n"
        "Quality Control, ISO 9001, Six Sigma, Tile Inspection\n"
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(r1_content)
        r1_path = temp_files(f.name)

    # Preview & Extraction verification for R1
    r1_parsed = process_resume(r1_path, "txt")
    assert r1_parsed, "First uploaded resume must be parsed successfully"
    assert r1_parsed.get("candidate_name") == "Juan Dela Cruz"
    assert r1_parsed.get("candidate_email") == "juan.delacruz@gmail.com"
    assert "raw_text" in r1_parsed
    assert "JUAN DELA CRUZ" in r1_parsed["raw_text"]
    assert len(r1_parsed.get("skills", [])) > 0

    # 2. Review before submit: Applicant replaces resume with second resume (R2) before final submission
    r2_content = (
        "MARIA SANTOS\n"
        "Email: maria.santos@gmail.com\n"
        "Phone: +63 928 987 6543\n"
        "Location: Batangas City, Philippines\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Mechanical Design Engineer with 4 years in production automation.\n\n"
        "EXPERIENCE\n"
        "Maintenance Engineer | Batangas Plant | 2021 - Present\n"
        "- Supervised preventative maintenance of hydraulic presses and roller kilns.\n\n"
        "EDUCATION\n"
        "BS Mechanical Engineering | Batangas State University\n\n"
        "SKILLS\n"
        "AutoCAD, SolidWorks, PLC Programming, Predictive Maintenance\n"
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(r2_content)
        r2_path = temp_files(f.name)

    # Preview & Extraction verification for replaced resume R2
    r2_parsed = process_resume(r2_path, "txt")
    assert r2_parsed, "Replaced resume must be parsed successfully"
    assert r2_parsed.get("candidate_name") == "Maria Santos"
    assert r2_parsed.get("candidate_email") == "maria.santos@gmail.com"
    assert "maria.santos@gmail.com" in r2_parsed["raw_text"]
    assert "AutoCAD" in r2_parsed.get("skills", [])
    # Verify old data is replaced
    assert r2_parsed.get("candidate_name") != r1_parsed.get("candidate_name")
    assert r2_parsed.get("candidate_email") != r1_parsed.get("candidate_email")


def test_tc_res_010_text_extraction_all_visible_info(temp_files):
    """
    Test Case: TC-RES-010
    Module: Resume Processing
    Requirement: REQ004
    Scenario: Text Extraction
    Steps: Upload R1
    Expected Result: Extracted text contains all visible resume text without missing important info (e.g. company, degree).
    """
    # 1. Test real-world R1 PDF (contains company & job title combined, plus student status)
    r1_sample_path = "uploads/resumes/1779865932_jampol.pdf" if os.path.exists("uploads/resumes/1779865932_jampol.pdf") else "backend/uploads/resumes/1779865932_jampol.pdf"
    if os.path.exists(r1_sample_path):
        parsed = process_resume(r1_sample_path, "pdf")
        assert parsed.get("candidate_name") == "John Paul T. Basagre"
        assert parsed.get("degree") == "Bachelor of Science in Computer Science"
        assert "STI Colleges" in parsed.get("college", "")
        assert parsed.get("company") == "Food Panda", f"Expected 'Food Panda', got '{parsed.get('company')}'"
        assert parsed.get("job_title") == "Delivery Rider"
        assert "raw_text" in parsed
        assert "Filipinas Avenue, Dulumbayan, Teresa, Rizal" in parsed["raw_text"]
        assert len(parsed.get("work_experiences", [])) >= 1
        assert parsed["work_experiences"][0]["company_name"] == "Food Panda"

    # 2. Test multi-role real-world PDF
    r2_sample_path = "uploads/resumes/1779867190_SebastianCurtisLavarias.pdf" if os.path.exists("uploads/resumes/1779867190_SebastianCurtisLavarias.pdf") else "backend/uploads/resumes/1779867190_SebastianCurtisLavarias.pdf"
    if os.path.exists(r2_sample_path):
        parsed2 = process_resume(r2_sample_path, "pdf")
        assert parsed2.get("candidate_name") == "Sebastian Curtis Lavarias"
        assert parsed2.get("degree") == "Bachelor of Science in Information Technology"
        assert "Universidad De Manila" in parsed2.get("college", "")
        assert parsed2.get("company") == "ChanzIT"
        assert len(parsed2.get("work_experiences", [])) >= 3

    # 3. Test DOCX format with specialized engineering degree and single-line experience
    doc = docx.Document()
    doc.add_heading("ENGR. ALYSSA MARIE REYES", level=0)
    p_contact = doc.add_paragraph("alyssa.reyes@gmail.com | +63 919 555 4321 | Binangonan, Rizal")
    
    doc.add_heading("EDUCATION", level=1)
    doc.add_paragraph("Mapúa University - Intramuros, Manila")
    doc.add_paragraph("BS Materials Science and Engineering")
    doc.add_paragraph("2018 - 2022")
    
    doc.add_heading("WORK EXPERIENCE", level=1)
    doc.add_paragraph("Mariwasa Siam Ceramics Inc.")
    doc.add_paragraph("Materials Quality Engineer")
    doc.add_paragraph("August 2022 - Present")
    doc.add_paragraph("• Performed raw material characterization and ceramic testing.")

    doc.add_heading("SKILLS", level=1)
    doc.add_paragraph("Materials Characterization, Metallurgy, XRD, SEM, Quality Assurance")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc.save(f.name)
        docx_path = temp_files(f.name)

    res_docx = process_resume(docx_path, "docx")
    assert "Alyssa Marie Reyes" in res_docx.get("candidate_name", "")
    assert "Materials" in res_docx.get("degree", ""), f"Degree should capture Materials Engineering, got: {res_docx.get('degree')}"
    assert "Mapúa University" in res_docx.get("college", "") or "Mapua" in res_docx.get("college", "")
    assert "Mariwasa" in res_docx.get("company", ""), f"Company should capture Mariwasa, got: {res_docx.get('company')}"
    assert "Engineer" in res_docx.get("job_title", "")
    assert len(res_docx.get("work_experiences", [])) >= 1
    assert len(res_docx.get("education_details", [])) >= 1

    # 4. Test TXT format with date inline without pipe
    txt_content = (
        "MICHAEL ANGELO TAN\n"
        "Email: michael.tan@yahoo.com\n"
        "Phone: 09201234567\n"
        "Location: Quezon City\n\n"
        "WORK EXPERIENCE\n"
        "Grab Philippines Delivery Rider        June 2023 - Present\n"
        "• Transported packages and food parcels across NCR.\n\n"
        "EDUCATION\n"
        "BS Chemical Engineering\n"
        "University of the Philippines Diliman\n"
        "2019 - 2023\n"
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(txt_content)
        txt_path = temp_files(f.name)

    res_txt = process_resume(txt_path, "txt")
    assert res_txt.get("candidate_name") == "Michael Angelo Tan"
    assert "Chemical Engineering" in res_txt.get("degree", "")
    assert "University of the Philippines" in res_txt.get("college", "")
    assert "Grab" in res_txt.get("company", "")
    assert "Delivery Rider" in res_txt.get("job_title", "")


def test_tc_res_011_normalization_emojis_symbols_accented_letters(temp_files):
    """
    Test Case: TC-RES-011
    Module: Resume Processing
    Requirement: REQ005
    Scenario: Normalization
    Steps: Upload R6
    Expected Result: Extra spaces, symbols and stray characters removed; accented letters kept.
    Actual Result (Fixed): Emojis are removed, extra spaces collapsed, accented letters preserved.
    """
    from app.extractors.file.file_extractor import clean_raw_text, remove_emojis

    # 1. Direct unit test of clean_raw_text with emojis, extra spaces, stray symbols, and accented letters
    raw_sample = (
        "👤   JOSÉ   NIÑO   HERNÁNDEZ   ✨\n\n\n"
        "✉️   jose.nino@gmail.com   |   📞   +63 917 555 1234   |   📍   Parañaque City, Metro Manila\n\n\n\n"
        "PROFESSIONAL SUMMARY\n"
        "🚀   Materials Engineer with 4+ years of quality assurance experience.\n\n"
        "EDUCATION\n"
        "🎓   Mapúa University - Intramuros, Manila\n"
        "BS Materials Science and Engineering\n"
        "2018 - 2022   •   Cum Laude   ⭐\n\n"
        "WORK EXPERIENCE\n"
        "💼   Mariwasa Siam Ceramics Inc.\n"
        "Materials Quality Engineer\n"
        "August 2022 - Present\n"
        "•   Conducted ceramic quality analysis and physical testing.   💻\n"
        "•   Collaborated with production managers and inspectors.   ✔️\n"
    )

    cleaned = clean_raw_text(raw_sample)

    # Verification: All emojis must be stripped
    emoji_chars = ["👤", "✨", "✉", "📞", "📍", "🚀", "🎓", "⭐", "💼", "💻", "✔️"]
    for em in emoji_chars:
        assert em not in cleaned, f"Emoji '{em}' should have been removed from cleaned text"

    # Verification: Accented letters must be preserved
    assert "JOSÉ" in cleaned or "José" in cleaned, "Accented letter 'É' should be preserved"
    assert "NIÑO" in cleaned or "Niño" in cleaned, "Accented letter 'Ñ' should be preserved"
    assert "HERNÁNDEZ" in cleaned or "Hernández" in cleaned, "Accented letter 'Á' should be preserved"
    assert "Parañaque" in cleaned, "Accented letter 'ñ' in Parañaque must be preserved"
    assert "Mapúa" in cleaned, "Accented letter 'ú' in Mapúa must be preserved"

    # Verification: Extra spaces collapsed
    assert "   " not in cleaned, "Multiple consecutive spaces should be collapsed"
    assert "\n\n\n" not in cleaned, "Excessive consecutive newlines should be collapsed"

    # 2. End-to-end processing test via process_resume on R6 representation (TXT)
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(raw_sample)
        r6_txt_path = temp_files(f.name)

    res_r6 = process_resume(r6_txt_path, "txt")
    raw_extracted = res_r6.get("raw_text", "")

    # Ensure raw_text is normalized
    for em in emoji_chars:
        assert em not in raw_extracted, f"Emoji '{em}' should not appear in extracted raw_text"
    assert "Parañaque" in raw_extracted
    assert "Mapúa" in raw_extracted

    # Ensure structured fields are clean of emojis and retain accents
    assert "José" in res_r6.get("candidate_name", "") or "JOSÉ" in res_r6.get("candidate_name", "")
    assert "jose.nino@gmail.com" == res_r6.get("candidate_email")
    assert "+63 917 555 1234" in res_r6.get("candidate_phone", "")
    assert "Parañaque" in res_r6.get("location", "")
    assert "Mapúa" in res_r6.get("college", "") or "Mapua" in res_r6.get("college", "")
    assert "Mariwasa" in res_r6.get("company", "")

    # 3. End-to-end processing test via DOCX format with emojis & accents
    doc_r6 = docx.Document()
    doc_r6.add_heading("👤   DR. RENÉ   PEÑA   CRUZ   🌟", level=0)
    doc_r6.add_paragraph("📧   rene.pena@outlook.com   |   📱   0918-765-4321   |   📌   Las Piñas City")
    doc_r6.add_heading("EDUCATION", level=1)
    doc_r6.add_paragraph("Mapúa University   🎓")
    doc_r6.add_paragraph("BS Computer Engineering")
    doc_r6.add_paragraph("2017 - 2021")
    doc_r6.add_heading("WORK EXPERIENCE", level=1)
    doc_r6.add_paragraph("Accenture Philippines   💼")
    doc_r6.add_paragraph("Software Engineer")
    doc_r6.add_paragraph("August 2021 - Present")
    doc_r6.add_paragraph("•   Engineered backend web APIs.   🚀")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc_r6.save(f.name)
        r6_docx_path = temp_files(f.name)

    res_docx_r6 = process_resume(r6_docx_path, "docx")
    docx_raw = res_docx_r6.get("raw_text", "")

    # Ensure no emojis in DOCX raw_text
    for em in ["👤", "🌟", "📧", "📱", "📌", "🎓", "💼", "🚀"]:
        assert em not in docx_raw, f"Emoji '{em}' should not appear in docx raw_text"
    # Ensure accented letters kept
    assert "René" in res_docx_r6.get("candidate_name", "") or "RENÉ" in res_docx_r6.get("candidate_name", "")
    assert "Peña" in res_docx_r6.get("candidate_name", "") or "PEÑA" in res_docx_r6.get("candidate_name", "")
    assert "Las Piñas" in res_docx_r6.get("location", "")
    assert "Accenture" in res_docx_r6.get("company", "")


@pytest.mark.asyncio
async def test_tc_res_013_missing_section_flagged_incomplete(temp_files):
    """
    Test ID: TC-RES-013
    Module: Resume Processing
    Requirement: REQ006
    Scenario: Missing section
    Steps: Upload R7 (DOCX format missing Work Experience section)
    Expected Result: Parser completes; missing section left empty, flagged as incomplete
    """
    # ── 1. Create R7 Sample as a valid Microsoft Word .docx document ─────────
    # R7 has Personal Info, Education, and Skills, but NO Work Experience section
    doc_r7 = docx.Document()
    doc_r7.add_heading("CARMINA FLORES SANTOS", level=0)
    doc_r7.add_paragraph("carmina.santos@gmail.com | +63 917 888 9999 | Makati City, Metro Manila")
    
    doc_r7.add_heading("OBJECTIVE", level=1)
    doc_r7.add_paragraph("Dedicated recent Accountancy graduate aiming to leverage analytical and financial competencies.")

    doc_r7.add_heading("EDUCATION", level=1)
    doc_r7.add_paragraph("Bachelor of Science in Accountancy")
    doc_r7.add_paragraph("University of Santo Tomas, Manila")
    doc_r7.add_paragraph("2019 - 2023 | Magna Cum Laude")

    doc_r7.add_heading("SKILLS & COMPETENCIES", level=1)
    doc_r7.add_paragraph("• Financial Accounting")
    doc_r7.add_paragraph("• QuickBooks")
    doc_r7.add_paragraph("• SAP Financial Accounting")
    doc_r7.add_paragraph("• Philippine Taxation")
    doc_r7.add_paragraph("• Microsoft Excel Financial Modeling")

    doc_r7.add_heading("CERTIFICATIONS & LICENSES", level=1)
    doc_r7.add_paragraph("Certified Public Accountant (CPA) - PRC Board Passer (Rating: 88.50%)")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc_r7.save(f.name)
        r7_docx_path = temp_files(f.name)

    # ── 2. Run Resume Processing on R7 DOCX ──────────────────────────────────
    res_r7 = process_resume(r7_docx_path, "docx")

    # A. Parser completes successfully (does not crash or return empty dict)
    assert res_r7 is not None, "Parser must complete and return structured resume data"
    assert isinstance(res_r7, dict), "Parser result must be a dictionary"
    assert len(res_r7) > 0, "Parser must not return empty data"

    # B. Missing section (Work Experience) is left cleanly empty
    assert res_r7.get("work_experiences") == [], "work_experiences must be an empty list when section is missing"
    assert res_r7.get("experience_details") == [], "experience_details must be an empty list when section is missing"
    assert res_r7.get("job_title") == "", "job_title must be empty string when experience section is missing"
    assert res_r7.get("candidate_job_title") == "", "candidate_job_title alias must be empty string"
    assert res_r7.get("company") == "", "company must be empty string when experience section is missing"
    assert res_r7.get("candidate_company") == "", "candidate_company alias must be empty string"
    assert res_r7.get("experience") == "", "experience summary must be empty string"
    assert res_r7.get("years_experience") == 0, "years_experience must be 0 when experience section is missing"
    assert res_r7.get("total_experience_months") == 0, "total_experience_months must be 0"
    assert res_r7.get("relevance") == "", "relevance statement must be empty when experience is missing"

    # C. Existing sections (Personal, Education, Skills) are accurately parsed
    assert "Carmina" in res_r7.get("candidate_name", "").title()
    assert res_r7.get("candidate_email") == "carmina.santos@gmail.com"
    assert "9178889999" in res_r7.get("candidate_phone", "").replace("-", "").replace(" ", "")
    assert "Bachelor of Science in Accountancy" in res_r7.get("degree", "")
    assert "Santo Tomas" in res_r7.get("college", "")
    assert len(res_r7.get("skills_list", [])) >= 3
    assert any("Accounting" in s or "QuickBooks" in s for s in res_r7.get("skills_list", []))

    # D. Resume is explicitly flagged as incomplete
    assert res_r7.get("is_incomplete") is True, "Resume must be flagged as incomplete (is_incomplete=True)"
    assert res_r7.get("is_complete") is False, "Resume must have is_complete=False"
    assert res_r7.get("completeness_status") == "Incomplete", "completeness_status must be 'Incomplete'"
    assert "Work Experience" in res_r7.get("missing_sections", []), "missing_sections must include 'Work Experience'"
    assert "work_experiences" in res_r7.get("missing_fields", []), "missing_fields must track empty experience fields"
    assert res_r7.get("completeness_score") == 75.0, "Score should reflect 3 of 4 core sections present (75.0%)"
    assert res_r7.get("completeness_flags", {}).get("work_experience") is False

    # E. Diagnostics report displays completeness assessment
    disp = res_r7.get("formatted_display", "")
    assert "COMPLETENESS ASSESSMENT" in disp
    assert "Flagged Incomplete:  Yes" in disp
    assert "Work Experience" in disp

    # ── 3. Test Resume Missing Education Section ─────────────────────────────
    doc_no_edu = docx.Document()
    doc_no_edu.add_heading("MARKO RODRIGUEZ", level=0)
    doc_no_edu.add_paragraph("marko.rodriguez@gmail.com | 0918-111-2222 | Pasig City")
    doc_no_edu.add_heading("WORK EXPERIENCE", level=1)
    doc_no_edu.add_paragraph("Senior Graphic Designer")
    doc_no_edu.add_paragraph("Creative Studio Inc., Pasig City")
    doc_no_edu.add_paragraph("March 2020 - Present")
    doc_no_edu.add_paragraph("• Created brand identity assets and UI graphics.")
    doc_no_edu.add_heading("SKILLS", level=1)
    doc_no_edu.add_paragraph("Adobe Photoshop, Illustrator, Figma, Typography")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc_no_edu.save(f.name)
        no_edu_docx_path = temp_files(f.name)

    res_no_edu = process_resume(no_edu_docx_path, "docx")
    assert res_no_edu.get("is_incomplete") is True
    assert "Education" in res_no_edu.get("missing_sections", [])
    assert res_no_edu.get("education_entries") == []
    assert res_no_edu.get("degree") == ""
    assert res_no_edu.get("institution") == ""
    assert res_no_edu.get("college") == ""
    assert res_no_edu.get("company") == "Creative Studio Inc."

    # ── 4. Test Resume Missing Skills Section ─────────────────────────────────
    doc_no_skills = docx.Document()
    doc_no_skills.add_heading("DIANA REYES", level=0)
    doc_no_skills.add_paragraph("diana.reyes@gmail.com | 0919-333-4444 | Quezon City")
    doc_no_skills.add_heading("EDUCATION", level=1)
    doc_no_skills.add_paragraph("BS Civil Engineering")
    doc_no_skills.add_paragraph("Polytechnic University of the Philippines")
    doc_no_skills.add_paragraph("2018 - 2022")
    doc_no_skills.add_heading("WORK EXPERIENCE", level=1)
    doc_no_skills.add_paragraph("Site Engineer")
    doc_no_skills.add_paragraph("Megawide Construction")
    doc_no_skills.add_paragraph("June 2022 - Present")
    doc_no_skills.add_paragraph("• Supervised rebar placement and concrete pouring.")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc_no_skills.save(f.name)
        no_skills_docx_path = temp_files(f.name)

    res_no_skills = process_resume(no_skills_docx_path, "docx")
    assert res_no_skills.get("is_incomplete") is True
    assert "Skills" in res_no_skills.get("missing_sections", [])
    assert res_no_skills.get("skills_list") == []
    assert res_no_skills.get("skills") == ""

    # ── 5. Test Complete Resume (All 4 Core Sections Present) ────────────────
    doc_complete = docx.Document()
    doc_complete.add_heading("EDUARDO BAUTISTA", level=0)
    doc_complete.add_paragraph("eduardo.bautista@gmail.com | 0917-555-6666 | Taguig City")
    doc_complete.add_heading("EDUCATION", level=1)
    doc_complete.add_paragraph("BS Computer Engineering")
    doc_complete.add_paragraph("Mapua University, 2018-2022")
    doc_complete.add_heading("WORK EXPERIENCE", level=1)
    doc_complete.add_paragraph("Full Stack Developer")
    doc_complete.add_paragraph("Accenture Philippines, 2022-Present")
    doc_complete.add_paragraph("• Built web applications.")
    doc_complete.add_heading("SKILLS", level=1)
    doc_complete.add_paragraph("Python, React, PostgreSQL, Docker, Git")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc_complete.save(f.name)
        complete_docx_path = temp_files(f.name)

    res_complete = process_resume(complete_docx_path, "docx")
    assert res_complete.get("is_incomplete") is False, "Complete resume must have is_incomplete=False"
    assert res_complete.get("is_complete") is True, "Complete resume must have is_complete=True"
    assert res_complete.get("completeness_status") == "Complete"
    assert res_complete.get("missing_sections") == []
    assert res_complete.get("completeness_score") == 100.0


def test_tc_res_014_no_data_loss_across_formats(temp_files):
    """
    Test Case: TC-RES-014
    Module: Resume Processing
    Requirement: REQ051
    Scenario: No data loss across formats
    Steps: Upload same content as DOCX, PDF, TXT
    Expected Result: Extracted fields identical across three (including candidate_company, degree, role, name, email).
    """
    resume_text = (
        "EDUARDO SANTOS\n"
        "Email: eduardo.santos@gmail.com\n"
        "Phone: +63 918 765 4321\n"
        "Address: Pasig City, Metro Manila\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Experienced Senior Full Stack Developer specializing in Python, React, and cloud architectures.\n\n"
        "WORK EXPERIENCE\n"
        "Senior Full Stack Developer\n"
        "Tech Mahindra\n"
        "August 2021 - Present\n"
        "• Designed and developed resilient microservices using FastAPI and PostgreSQL.\n"
        "• Optimized distributed data pipelines and Redis caching layers.\n\n"
        "EDUCATION\n"
        "BS Computer Engineering\n"
        "Mapúa University\n"
        "2015 - 2019\n\n"
        "SKILLS & COMPETENCIES\n"
        "Python, FastAPI, TypeScript, React, PostgreSQL, Docker, Redis, Git, Linux\n"
    )

    # 1. Plain text format (.txt)
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(resume_text)
        txt_path = temp_files(f.name)
    res_txt = process_resume(txt_path, "txt")

    # 2. PDF format (.pdf)
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 50), resume_text)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_doc.save(f.name)
        pdf_path = temp_files(f.name)
    res_pdf = process_resume(pdf_path, "pdf")

    # 3. DOCX format (.docx) with paragraphs
    w_doc = docx.Document()
    for line in resume_text.split("\n"):
        w_doc.add_paragraph(line)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        w_doc.save(f.name)
        docx_path = temp_files(f.name)
    res_docx = process_resume(docx_path, "docx")

    # 4. Verify identical extraction across all three formats
    fields_to_compare = [
        "candidate_name",
        "candidate_email",
        "candidate_company",
        "candidate_job_title",
        "candidate_degree",
        "is_incomplete",
        "completeness_status"
    ]

    for field in fields_to_compare:
        val_txt = res_txt.get(field)
        val_pdf = res_pdf.get(field)
        val_docx = res_docx.get(field)
        assert val_txt == val_pdf == val_docx, (
            f"Discrepancy across formats for field '{field}': "
            f"TXT='{val_txt}', PDF='{val_pdf}', DOCX='{val_docx}'"
        )

    # Specifically verify company was captured identically
    assert res_docx.get("candidate_company") == "Tech Mahindra"
    assert res_pdf.get("candidate_company") == "Tech Mahindra"
    assert res_txt.get("candidate_company") == "Tech Mahindra"

    # Specifically verify job title was captured identically
    assert res_docx.get("candidate_job_title") == "Full Stack Developer"
    assert res_pdf.get("candidate_job_title") == "Full Stack Developer"
    assert res_txt.get("candidate_job_title") == "Full Stack Developer"

    # 5. Test DOCX table layout (Dates in Col 0, Position & Company in Col 1, Duties in Col 2)
    w_table_doc = docx.Document()
    w_table_doc.add_heading("EDUARDO SANTOS", level=0)
    w_table_doc.add_paragraph("eduardo.santos@gmail.com | 09187654321 | Pasig City")
    w_table_doc.add_heading("WORK EXPERIENCE", level=1)

    tbl = w_table_doc.add_table(rows=2, cols=3)
    tbl.cell(0, 0).text = "Dates"
    tbl.cell(0, 1).text = "Role & Company"
    tbl.cell(0, 2).text = "Responsibilities"
    tbl.cell(1, 0).text = "2021 - Present"
    tbl.cell(1, 1).text = "Senior Full Stack Developer\nTech Mahindra"
    tbl.cell(1, 2).text = "Designed and developed microservices in Python"

    w_table_doc.add_heading("EDUCATION", level=1)
    w_table_doc.add_paragraph("BS Computer Engineering\nMapúa University\n2015 - 2019")
    w_table_doc.add_heading("SKILLS", level=1)
    w_table_doc.add_paragraph("Python, FastAPI, Redis, Docker, SQL")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        w_table_doc.save(f.name)
        docx_table_path = temp_files(f.name)
    res_table_docx = process_resume(docx_table_path, "docx")
    assert res_table_docx.get("candidate_company") == "Tech Mahindra", (
        f"Table DOCX must capture company 'Tech Mahindra', got '{res_table_docx.get('candidate_company')}'"
    )
    assert res_table_docx.get("candidate_job_title") == "Full Stack Developer"

    # 6. Test TXT file with UTF-16 encoding
    utf16_content = resume_text.encode("utf-16")
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f:
        f.write(utf16_content)
        txt_utf16_path = temp_files(f.name)
    res_utf16 = process_resume(txt_utf16_path, "txt")
    assert res_utf16.get("candidate_name") == "Eduardo Santos"
    assert res_utf16.get("candidate_company") == "Tech Mahindra"






