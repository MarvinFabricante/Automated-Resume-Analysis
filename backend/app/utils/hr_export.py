import csv
import io
from datetime import datetime
from typing import Any, Dict, List

import fitz  # PyMuPDF


def _csv_safe(value: Any) -> str:
    """Serialize cell value safely for CSV readers and spreadsheets."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", " ").replace("\n", " ").strip()
    if text and text[0] in ("=", "+", "@") and not text.startswith(("+", "-")):
        return f"'{text}"
    return text


def _pdf_safe_text(value: Any) -> str:
    """Ensure text renders cleanly with built-in PyMuPDF Helvetica Latin-1 font."""
    if value is None:
        return ""
    return str(value).replace("\r\n", " ").replace("\n", " ").encode("latin-1", "replace").decode("latin-1")


def generate_hr_csv_bytes(export_data: Dict[str, Any]) -> bytes:
    """
    Generate a UTF-8 (with BOM) CSV containing HR Dashboard analytics
    (summary counts, applicants per position, average score, skills distribution)
    and individual applicant records.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")

    summary = export_data.get("summary") or {}
    positions = export_data.get("position_distribution") or []
    skills_dist = export_data.get("skills_distribution") or []
    applicants = export_data.get("applicants") or []

    writer.writerow(["MARIWASA ARAS - HR DASHBOARD RECRUITMENT & ANALYTICS REPORT"])
    writer.writerow(["Generated At", export_data.get("generated_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")])
    writer.writerow([])

    writer.writerow(["DASHBOARD ANALYTICS SUMMARY"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Applications", summary.get("total_applications", len(applicants))])
    writer.writerow(["Active Positions", summary.get("active_positions", 0)])
    writer.writerow(["Overall Average Score", f"{summary.get('average_score', 0)}%"])
    writer.writerow(["Pending Review", summary.get("pending", 0)])
    writer.writerow(["Screened / Reviewed", summary.get("reviewed", 0)])
    writer.writerow(["Accepted", summary.get("accepted", 0)])
    writer.writerow(["Rejected / Archived", summary.get("rejected", 0)])
    writer.writerow([])

    writer.writerow(["APPLICANTS PER POSITION"])
    writer.writerow(["Position", "Applicants", "Share", "Average Score"])
    for pos in positions:
        writer.writerow([
            _csv_safe(pos.get("label", "Unspecified")),
            pos.get("value", 0),
            pos.get("percentage", "0%"),
            f"{pos.get('avg_score', 0)}%",
        ])
    writer.writerow([])

    writer.writerow(["SKILLS DISTRIBUTION"])
    writer.writerow(["Skill", "Applicants", "Share"])
    for skill in skills_dist:
        writer.writerow([
            _csv_safe(skill.get("label", "")),
            skill.get("value", 0),
            skill.get("percentage", "0%"),
        ])
    writer.writerow([])

    writer.writerow(["APPLICANT DATA"])
    writer.writerow([
        "ID",
        "Candidate Name",
        "Email",
        "Preferred Role",
        "Department",
        "Status",
        "Match Score",
        "Skills Score",
        "Experience Score",
        "Education Score",
        "Skills",
        "Application Date",
        "Location",
    ])
    for app in applicants:
        writer.writerow([
            app.get("id", ""),
            _csv_safe(app.get("candidate_name", "")),
            _csv_safe(app.get("candidate_email", "")),
            _csv_safe(app.get("preferred_role", "")),
            _csv_safe(app.get("department", "General")),
            _csv_safe(app.get("status", "PENDING")),
            f"{app.get('match_score', 0)}%",
            f"{app.get('skills_score', 0)}%",
            f"{app.get('experience_score', 0)}%",
            f"{app.get('education_score', 0)}%",
            _csv_safe(app.get("skills_text", "")),
            _csv_safe(app.get("applied_date", "N/A")),
            _csv_safe(app.get("location", "N/A")),
        ])

    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def generate_hr_pdf_bytes(export_data: Dict[str, Any]) -> bytes:
    """
    Generate a clean multi-page A4 PDF report containing HR Dashboard analytics
    and applicant records using PyMuPDF (fitz).
    """
    doc = fitz.open()
    page_w, page_h = 595, 842
    margin_x = 36
    max_y = page_h - 44

    summary = export_data.get("summary") or {}
    positions: List[Dict[str, Any]] = export_data.get("position_distribution") or []
    skills_dist: List[Dict[str, Any]] = export_data.get("skills_distribution") or []
    applicants: List[Dict[str, Any]] = export_data.get("applicants") or []
    generated_at = export_data.get("generated_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    state: Dict[str, Any] = {"page": None, "y": 40}

    def new_page() -> None:
        page = doc.new_page(width=page_w, height=page_h)
        state["page"] = page
        # Brand accent bar & title
        page.draw_rect(fitz.Rect(0, 0, page_w, 54), color=(0.839, 0.0, 0.255), fill=(0.839, 0.0, 0.255))
        page.insert_text((margin_x, 26), "MARIWASA ARAS - HR Dashboard Analytics & Applicant Report", fontsize=13, fontname="helv", color=(1, 1, 1))
        page.insert_text((margin_x, 42), f"Generated: {_pdf_safe_text(generated_at)}   |   Page {len(doc)}", fontsize=8.5, fontname="helv", color=(1, 0.9, 0.93))
        state["y"] = 74

    def ensure_space(needed_height: float) -> None:
        if state["page"] is None or (state["y"] + needed_height) > max_y:
            new_page()

    def write_section_header(title: str) -> None:
        ensure_space(28)
        y = state["y"]
        state["page"].draw_rect(fitz.Rect(margin_x, y - 11, page_w - margin_x, y + 6), color=(0.96, 0.97, 0.98), fill=(0.96, 0.97, 0.98))
        state["page"].insert_text((margin_x + 6, y + 1), _pdf_safe_text(title), fontsize=10.5, fontname="helv", color=(0.839, 0.0, 0.255))
        state["y"] += 18

    def write_line(text: str, fontsize: float = 9.0, color=(0.15, 0.18, 0.24), x_offset: float = 0) -> None:
        ensure_space(fontsize + 6)
        state["page"].insert_text(
            (margin_x + x_offset, state["y"]),
            _pdf_safe_text(text),
            fontsize=fontsize,
            fontname="helv",
            color=color,
        )
        state["y"] += fontsize + 5

    new_page()

    # Section 1: Summary KPIs
    write_section_header("1. Dashboard Analytics Summary")
    write_line(
        f"Total Applications: {summary.get('total_applications', len(applicants))}   |   "
        f"Active Positions: {summary.get('active_positions', 0)}   |   "
        f"Average Score: {summary.get('average_score', 0)}%",
        fontsize=9.5,
    )
    write_line(
        f"Pending: {summary.get('pending', 0)}   |   "
        f"Screened/Reviewed: {summary.get('reviewed', 0)}   |   "
        f"Accepted: {summary.get('accepted', 0)}   |   "
        f"Rejected/Archived: {summary.get('rejected', 0)}",
        fontsize=9.0,
        color=(0.3, 0.35, 0.42),
    )
    state["y"] += 6

    # Section 2: Applicants per Position
    write_section_header("2. Applicants per Position")
    if not positions:
        write_line("No position applications recorded.", color=(0.45, 0.5, 0.56))
    else:
        for pos in positions:
            write_line(
                f"- {pos.get('label', 'Unspecified')}: {pos.get('value', 0)} applicant(s) "
                f"({pos.get('percentage', '0%')} | Avg Score: {pos.get('avg_score', 0)}%)"
            )
    state["y"] += 6

    # Section 3: Skills Distribution
    write_section_header("3. Skills Distribution")
    if not skills_dist:
        write_line("No extracted skills recorded.", color=(0.45, 0.5, 0.56))
    else:
        for skill in skills_dist[:30]:
            write_line(
                f"- {skill.get('label', '')}: {skill.get('value', 0)} applicant(s) ({skill.get('percentage', '0%')})"
            )
        if len(skills_dist) > 30:
            write_line(f"... and {len(skills_dist) - 30} more skills (see CSV export for full tail)", color=(0.45, 0.5, 0.56))
    state["y"] += 6

    # Section 4: Applicant Records Table
    write_section_header(f"4. Applicant Data ({len(applicants)} Records)")
    write_line("ID | Name | Role | Status | Score | Date", fontsize=8.5, color=(0.35, 0.4, 0.48))
    if not applicants:
        write_line("No applicants recorded.", color=(0.45, 0.5, 0.56))
    else:
        for app in applicants:
            row_line = (
                f"#{app.get('id', '')} | {app.get('candidate_name', '')[:26]} | "
                f"{str(app.get('preferred_role', ''))[:26]} | {app.get('status', 'PENDING')} | "
                f"{app.get('match_score', 0)}% | {app.get('applied_date', 'N/A')}"
            )
            write_line(row_line, fontsize=8.5)
            skills_preview = str(app.get("skills_text", "") or "").strip()
            if skills_preview:
                write_line(f"   Skills: {skills_preview[:95]}", fontsize=7.5, color=(0.42, 0.47, 0.55))

    return doc.tobytes()
