"""
Generates a clean, one-page, ATS-friendly resume guide/template in DOCX format.
Strictly single-column, standard font, NO tables, NO images, NO text boxes,
and NO headers/footers, using a fictional placeholder name and content.
"""
import io
import docx
from docx.shared import Inches, Pt, RGBColor


def build_ats_friendly_resume_docx() -> bytes:
    """Return raw bytes for a one-page ATS-friendly DOCX resume template."""
    doc = docx.Document()

    # Compact margins so everything fits cleanly on one page
    for section in doc.sections:
        section.top_margin = Inches(0.55)
        section.bottom_margin = Inches(0.55)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    def add_heading(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(text.upper())
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        return p

    def add_line(text: str, bold: bool = False, italic: bool = False, size: float = 10.5, space_after: float = 2):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        return p

    def add_bullet(text: str):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1.5)
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        return p

    # Name & Contact (plain body text on page 1 — NOT in a header or table)
    p_name = doc.add_paragraph()
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(2)
    r_name = p_name.add_run("ALEX RIVERA")
    r_name.bold = True
    r_name.font.name = "Calibri"
    r_name.font.size = Pt(16)
    r_name.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    add_line(
        "Calamba, Laguna  |  0917-000-0123  |  alex.rivera@example.com",
        size=10,
        space_after=4,
    )
    add_line(
        "Sample ATS-Friendly Resume Template — Replace all sample details with your own true information, then delete this line before saving as DOCX or text-based PDF.",
        italic=True,
        size=9,
        space_after=6,
    )

    # Skills
    add_heading("Skills")
    add_line(
        "Customer Service, Order Processing, Microsoft Excel, Shopify, Data Entry, Inventory Tracking, Report Preparation, Time Management",
        size=10,
        space_after=4,
    )

    # Work Experience
    add_heading("Work Experience")

    add_line(
        "Customer Service Representative, June 2023 - Present",
        bold=True,
        size=10.5,
        space_after=1,
    )
    add_line("Sample Retail Services Inc., Santa Rosa, Laguna", italic=True, size=10, space_after=2)
    add_bullet("Answered 50+ customer inquiries daily by phone and email regarding orders, deliveries, and product availability.")
    add_bullet("Updated order records and tracked shipments using Shopify and Microsoft Excel with high accuracy.")
    add_bullet("Coordinated with warehouse and delivery staff to resolve damaged or delayed orders promptly.")

    add_line(
        "Data Entry and Admin Assistant, May 2021 - May 2023",
        bold=True,
        size=10.5,
        space_after=1,
    )
    add_line("Sample Supply Co., Sto. Tomas, Batangas", italic=True, size=10, space_after=2)
    add_bullet("Encoded daily sales, inventory counts, and supplier invoices into Excel spreadsheets.")
    add_bullet("Prepared weekly stock summaries and assisted supervisors with filing and document checks.")

    # Education
    add_heading("Education")
    add_line(
        "Bachelor of Science in Business Administration, 2017 - 2021",
        bold=True,
        size=10.5,
        space_after=1,
    )
    add_line("Sample State College, Laguna", size=10, space_after=4)

    # Certifications
    add_heading("Certifications")
    add_bullet("TESDA National Certificate II (NC II) in Bookkeeping, 2022")
    add_bullet("Workplace Safety and Basic Microsoft Excel Training, 2023")

    # Brief reminder at bottom
    p_tip = doc.add_paragraph()
    p_tip.paragraph_format.space_before = Pt(8)
    p_tip.paragraph_format.space_after = Pt(0)
    r_tip = p_tip.add_run(
        "Quick tips: Keep one column, avoid tables/images/text boxes, list real skills by name, and only include what is true."
    )
    r_tip.italic = True
    r_tip.font.name = "Calibri"
    r_tip.font.size = Pt(9)
    r_tip.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
