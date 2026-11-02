import os
import tempfile
import pytest
import docx
from docx.oxml import parse_xml

from app.extractors.file.docx_extractor import (
    extract_text_from_docx,
    extract_image_from_docx,
)
from app.extractors.resume_processor import process_resume


@pytest.fixture
def temp_docx():
    """Helper fixture to create and clean up temporary docx files."""
    created_files = []

    def _create(doc: docx.Document) -> str:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            tmp_path = f.name
        doc.save(tmp_path)
        created_files.append(tmp_path)
        return tmp_path

    yield _create

    for p in created_files:
        if os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


def test_docx_basic_paragraphs(temp_docx):
    """Test standard paragraphs and headers extraction."""
    doc = docx.Document()
    doc.add_paragraph("MARIA SANTOS")
    doc.add_paragraph("Full Stack Software Engineer")
    doc.add_paragraph("TECHNICAL SKILLS")
    doc.add_paragraph("Python, FastAPI, TypeScript, React, PostgreSQL")

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "MARIA SANTOS" in text
    assert "Full Stack Software Engineer" in text
    assert "TECHNICAL SKILLS" in text
    assert "FastAPI" in text


def test_docx_document_order_preserved(temp_docx):
    """Ensure paragraphs and tables maintain their natural reading order."""
    doc = docx.Document()
    doc.add_paragraph("SECTION 1: SUMMARY")
    doc.add_paragraph("Summary content")

    tbl1 = doc.add_table(rows=1, cols=2)
    tbl1.cell(0, 0).text = "Table 1 Col 1"
    tbl1.cell(0, 1).text = "Table 1 Col 2"

    doc.add_paragraph("SECTION 2: WORK EXPERIENCE")
    doc.add_paragraph("Experience content")

    tbl2 = doc.add_table(rows=1, cols=2)
    tbl2.cell(0, 0).text = "Table 2 Col 1"
    tbl2.cell(0, 1).text = "Table 2 Col 2"

    doc.add_paragraph("SECTION 3: EDUCATION")

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    pos_s1 = text.find("SECTION 1: SUMMARY")
    pos_t1 = text.find("Table 1 Col 1")
    pos_s2 = text.find("SECTION 2: WORK EXPERIENCE")
    pos_t2 = text.find("Table 2 Col 1")
    pos_s3 = text.find("SECTION 3: EDUCATION")

    assert pos_s1 < pos_t1 < pos_s2 < pos_t2 < pos_s3


def test_docx_two_column_resume_layout(temp_docx):
    """Ensure multi-column resume layout tables extract columns vertically without corrupted merged lines."""
    doc = docx.Document()
    tbl = doc.add_table(rows=1, cols=2)

    # Column 1 (Left sidebar)
    tbl.cell(0, 0).text = (
        "CONTACT DETAILS\n"
        "Email: candidate@gmail.com\n"
        "Phone: 09171234567\n\n"
        "SKILLS\n"
        "Python, React, Docker, AWS"
    )

    # Column 2 (Right main column)
    tbl.cell(0, 1).text = (
        "WORK EXPERIENCE\n"
        "Senior Web Developer\n"
        "Acme Technologies | Oct 2021 - Present\n"
        "• Developed high-throughput REST APIs"
    )

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    # Both headers should be isolated lines and not concatenated with ' | '
    assert "Docker, AWS | WORK EXPERIENCE" not in text
    assert "WORK EXPERIENCE" in text
    assert "SKILLS" in text
    assert "Senior Web Developer" in text
    assert "candidate@gmail.com" in text


def test_docx_merged_table_cells_deduplication(temp_docx):
    """Ensure horizontally merged table cells (e.g. section titles spanning all columns) are not duplicated."""
    doc = docx.Document()
    tbl = doc.add_table(rows=2, cols=3)

    # Merge row 0 across all 3 columns
    c0 = tbl.cell(0, 0)
    c2 = tbl.cell(0, 2)
    merged = c0.merge(c2)
    merged.text = "WORK EXPERIENCE"

    # Row 1: normal columns
    tbl.cell(1, 0).text = "Software Engineer"
    tbl.cell(1, 1).text = "Google"
    tbl.cell(1, 2).text = "2020 - 2023"

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    # "WORK EXPERIENCE" should appear once, not duplicated
    assert "WORK EXPERIENCE | WORK EXPERIENCE" not in text
    assert "WORK EXPERIENCE" in text
    assert "Software Engineer | Google | 2020 - 2023" in text


def test_docx_first_page_header_contact_info(temp_docx):
    """Verify first_page_header is captured when different_first_page_header_footer is enabled."""
    doc = docx.Document()
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    section.first_page_header.paragraphs[0].text = "JUAN DELA CRUZ | juan.delacruz@gmail.com | 09171234567"

    doc.add_paragraph("PROFESSIONAL SUMMARY")
    doc.add_paragraph("Results-driven Software Engineer with 4 years of experience.")

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "JUAN DELA CRUZ" in text
    assert "juan.delacruz@gmail.com" in text
    assert "09171234567" in text
    # Should appear before the body text
    assert text.find("JUAN DELA CRUZ") < text.find("PROFESSIONAL SUMMARY")


def test_docx_content_controls_sdt(temp_docx):
    """Verify Structured Document Tags (<w:sdt>) used in Microsoft Word templates are extracted."""
    doc = docx.Document()
    xml_sdt = """<w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:sdtContent>
            <w:p><w:r><w:t>ANA MARIE REYES</w:t></w:r></w:p>
            <w:p><w:r><w:t>Email: ana.reyes@gmail.com</w:t></w:r></w:p>
        </w:sdtContent>
    </w:sdt>"""
    doc._element.body.append(parse_xml(xml_sdt))
    doc.add_paragraph("WORK EXPERIENCE")
    doc.add_paragraph("QA Engineer at Global Solutions")

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "ANA MARIE REYES" in text
    assert "ana.reyes@gmail.com" in text
    assert "QA Engineer at Global Solutions" in text


def test_docx_textboxes_extraction(temp_docx):
    """Verify textboxes anchored inside paragraphs (DrawingML) are extracted."""
    doc = docx.Document()
    xml_txbx = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
        <w:r>
            <w:drawing>
                <wp:anchor>
                    <wps:wsp>
                        <wps:txbx>
                            <w:txbxContent>
                                <w:p><w:r><w:t>JOSE RIZAL MERCADO</w:t></w:r></w:p>
                                <w:p><w:r><w:t>jose.rizal@gmail.com</w:t></w:r></w:p>
                            </w:txbxContent>
                        </wps:txbx>
                    </wps:wsp>
                </wp:anchor>
            </w:drawing>
        </w:r>
    </w:p>"""
    doc._element.body.append(parse_xml(xml_txbx))
    doc.add_paragraph("OBJECTIVE")
    doc.add_paragraph("To contribute as a Lead Software Architect.")

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "JOSE RIZAL MERCADO" in text
    assert "jose.rizal@gmail.com" in text
    assert "OBJECTIVE" in text


def test_docx_bullet_formatting(temp_docx):
    """Verify bullet list items (w:numPr) receive a bullet prefix (•)."""
    doc = docx.Document()
    doc.add_paragraph("WORK EXPERIENCE")
    doc.add_paragraph("Software Engineer")

    xml_bullet = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:pPr>
            <w:numPr>
                <w:ilvl w:val="0"/>
                <w:numId w:val="1"/>
            </w:numPr>
        </w:pPr>
        <w:r><w:t>Architected scalable microservices handling 10k RPS</w:t></w:r>
    </w:p>"""
    doc._element.body.append(parse_xml(xml_bullet))

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "• Architected scalable microservices handling 10k RPS" in text


def test_docx_hyperlinks_extraction(temp_docx):
    """Verify hyperlinks (mailto:, tel:, LinkedIn) are captured."""
    doc = docx.Document()
    doc.add_paragraph("Contact Me")

    # Add a mock relationship
    part = doc.part
    rel_id = part.relate_to("mailto:dev@company.com", docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    part.relate_to("https://www.linkedin.com/in/sample-dev", docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    path = temp_docx(doc)
    text = extract_text_from_docx(path)

    assert "Email Link: dev@company.com" in text
    assert "Profile Link: https://www.linkedin.com/in/sample-dev" in text


def test_docx_end_to_end_resume_processing(temp_docx):
    """End-to-end test verifying full process_resume accuracy on a multi-column DOCX resume."""
    doc = docx.Document()
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    section.first_page_header.paragraphs[0].text = "MARK ANTHONY BAUTISTA | mark.bautista@gmail.com | 09281234567"

    # Objective
    doc.add_paragraph("SUMMARY")
    doc.add_paragraph("Passionate Full Stack Developer with 3 years of enterprise development experience.")

    # 2-column layout table (Left: Skills & Education, Right: Experience)
    tbl = doc.add_table(rows=1, cols=2)
    tbl.cell(0, 0).text = (
        "SKILLS\n"
        "Python, Django, React, TypeScript, Docker, PostgreSQL\n\n"
        "EDUCATION\n"
        "Polytechnic University of the Philippines\n"
        "Bachelor of Science in Information Technology\n"
        "2020 - 2024"
    )
    tbl.cell(0, 1).text = (
        "WORK EXPERIENCE\n"
        "Full Stack Developer\n"
        "Innovatech Solutions | Quezon City, Metro Manila\n"
        "Jan 2022 - Present\n"
        "• Built real-time analytics dashboard with React and Django\n"
        "• Optimized PostgreSQL database queries by 40%"
    )

    path = temp_docx(doc)
    res = process_resume(path, "docx")

    assert res.get("candidate_name") == "Mark Anthony Bautista"
    assert res.get("candidate_email") == "mark.bautista@gmail.com"
    assert "0928" in res.get("candidate_phone", "")
    assert len(res.get("skills_list", [])) >= 4
    assert any("Python" in s for s in res.get("skills_list", []))
    assert any("React" in s for s in res.get("skills_list", []))

    # Experience entries
    exp_entries = res.get("work_experiences", [])
    assert len(exp_entries) >= 1
    exp0 = exp_entries[0]
    assert "Developer" in exp0.get("job_title", "")
    assert "Innovatech" in exp0.get("company_name", "")

    # Education entries
    assert res.get("highest_educational_attainment") == "Tertiary / College"
    assert "Information Technology" in res.get("degree", "")


def test_docx_image_extraction(temp_docx):
    """Verify profile picture extraction from DOCX."""
    import fitz

    # Create a small valid test PNG using fitz
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 180, 180), 0)
    pix.set_rect(fitz.IRect(0, 0, 180, 180), (120, 160, 200))
    png_bytes = pix.tobytes("png")

    doc = docx.Document()
    doc.add_paragraph("Candidate Resume")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_f:
        img_f.write(png_bytes)
        img_f_path = img_f.name

    doc.add_picture(img_f_path, width=docx.shared.Inches(1.5))
    os.unlink(img_f_path)

    path = temp_docx(doc)
    extracted_img = extract_image_from_docx(path)

    assert extracted_img is not None
    # Either a local path or a Supabase public URL
    assert "img" in extracted_img

