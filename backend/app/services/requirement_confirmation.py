"""Requirement coverage, evidence and applicant confirmation shared by all match paths."""
import re
import json
from pathlib import Path
from app.extractors.text_normalization import SKILL_SEPARATOR, normalize_skill_key
from app.services.requirement_rules import is_no_value

# Override/extend through matching_config['related_terms']; related evidence always
# needs confirmation, unlike an exact normalized requirement in the resume.
DEFAULT_RELATED_TERMS = json.loads(
    Path(__file__).with_name("requirement_related_terms.json").read_text(encoding="utf-8")
)


def requirement_items(value):
    values = value if isinstance(value, list) else [value]
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or is_no_value(value):
            continue
        for item in re.split(SKILL_SEPARATOR, value):
            item = item.strip()
            key = normalize_skill_key(item)
            if key and key not in seen and not is_no_value(item):
                seen.add(key)
                result.append(item)
    return result


def evaluate_requirements(resume, job, normalize=normalize_skill_key, related_terms=None):
    related = {normalize(k): v for k, v in DEFAULT_RELATED_TERMS.items()}
    related.update({normalize(k): v for k, v in (related_terms or {}).items()})
    responses = {
        (r.get("field"), normalize(str(r.get("requirement", "")))): r
        for r in resume.get("clarification_responses", []) or [] if isinstance(r, dict)
    }
    raw_evidence = " ".join(str(resume.get(k) or "") for k in
        ("skills", "skills_list", "experience", "relevance", "work_experiences", "raw_text"))
    evidence = normalize(raw_evidence)
    rows = []
    for field, requirement_field, candidate in (
        ("skills", "skills_requirements", resume.get("skills") or resume.get("skills_list")),
        ("certifications", "certifications_requirements", resume.get("certifications")),
        ("experience", "experience_requirements", resume.get("experience") or resume.get("relevance")),
    ):
        candidate_keys = {normalize(v) for v in requirement_items(candidate)}
        for item in requirement_items(getattr(job, requirement_field, None)):
            key = normalize(item)
            response = responses.get((field, key), {})
            answer = response.get("answer")
            row = {"field": field, "requirement": item, "status": "Not confirmed", "source": None}
            if answer in ("yes", "some", "no"):
                row.update(answer=answer, details=response.get("details", ""), years=response.get("years"))
                row["status"] = "Does not meet" if answer == "no" else "Meets requirement"
                row["source"] = "Confirmed by applicant"
            elif key in candidate_keys:
                row.update(status="Meets requirement", source="Resume")
            else:
                hits = [term for term in related.get(key, [])
                        if re.search(r"(?<!\w)" + re.escape(normalize(term)) + r"(?!\w)", evidence)]
                if hits:
                    row.update(status="Possible match", evidence=hits)
            rows.append(row)
    return rows


def apply_confirmations(resume, rows):
    """Feed positive answers through the same scoring functions as resume evidence."""
    result = dict(resume)
    for field, target in (("skills", "skills"), ("certifications", "certifications"), ("experience", "experience")):
        items = requirement_items(result.get(target))
        denied = {normalize_skill_key(r["requirement"]) for r in rows if r["field"] == field and r.get("answer") == "no"}
        items = [item for item in items if normalize_skill_key(item) not in denied]
        for row in rows:
            if row["field"] == field and row.get("answer") in ("yes", "some"):
                items.append(row["requirement"])
                if field == "experience":
                    if row.get("details"):
                        items.append(str(row["details"]))
                    try:
                        years = max(0, float(row.get("years") or 0))
                        result["years_experience"] = max(float(result.get("years_experience") or 0), years)
                    except (ValueError, TypeError):
                        pass
        result[target] = " | ".join(dict.fromkeys(items))
    return result


def confirmation_questions(rows, job):
    job_id = str(getattr(job, "job_id", None) or getattr(job, "id", None) or "job")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", job_id).strip("_").lower()
    questions = []
    for field in ("skills", "certifications", "experience"):
        items = [r for r in rows if r["field"] == field and r["source"] != "Resume"]
        if items:
            questions.append({
                "id": f"clarify_{slug}_{field}", "field": field,
                "job_id": job_id, "job_title": getattr(job, "job_title", ""),
                "question": "Which of these requirements do you have experience with?" if field != "certifications" else "Which of these certifications or licenses do you hold?",
                "type": "requirement_group", "items": items, "required": False,
                "reason": "Confirm each item. Unanswered items remain Not confirmed.",
            })
    return questions
