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


_CERT_SEPARATOR = r"[,;|•●◦‣▪►✓\n]+"


def requirement_items(value, split_slash: bool = True):
    values = value if isinstance(value, list) else [value]
    separator = SKILL_SEPARATOR if split_slash else _CERT_SEPARATOR
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or is_no_value(value):
            continue
        for item in re.split(separator, value):
            item = item.strip()
            key = normalize_skill_key(item)
            if key and key not in seen and not is_no_value(item):
                seen.add(key)
                result.append(item)
    return result


_PURE_DURATION_RE = re.compile(
    r"^(?:(?:minimum|min\.?|at\s+least)\s+(?:of\s+)?)?"
    r"\d+(?:\.\d+)?(?:\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?)?\s*\+?\s*"
    r"(?:years?|yrs?|months?|mos?)"
    r"(?:\s+(?:of\s+)?(?:relevant|related|direct|professional|work|industry|hands[- ]on|practical|prior)?\s*(?:work\s+)?(?:experience|exp\.?))?"
    r"(?:\s+(?:preferred|required|minimum))?\.?$",
    re.IGNORECASE,
)


def is_pure_duration_requirement(item: str) -> bool:
    """Return True when an experience requirement states only a tenure/duration (e.g. '3yrs', '2 years')."""
    return bool(item and _PURE_DURATION_RE.match(item.strip()))


def has_explicit_experience_evidence(resume: dict) -> bool:
    """Return True when the resume already provides explicit work history or experience duration."""
    try:
        if float(resume.get("years_experience") or 0) > 0:
            return True
    except (ValueError, TypeError):
        pass
    try:
        if int(resume.get("total_experience_months") or 0) > 0:
            return True
    except (ValueError, TypeError):
        pass
    for we in resume.get("work_experiences") or []:
        if isinstance(we, dict) and (
            int(we.get("duration_months") or 0) > 0
            or str(we.get("job_title") or "").strip()
            or str(we.get("start_date") or "").strip()
        ):
            return True
    exp_text = " ".join(
        str(resume.get(k) or "") for k in ("experience", "relevance", "relevant_experience")
    )
    if re.search(r"\b\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?)\b", exp_text, re.I):
        return True
    if re.search(r"\b(?:19|20)\d{2}\s*[-–—to]+\s*(?:(?:19|20)\d{2}|present|current)\b", exp_text, re.I):
        return True
    return False


def _merge_candidate_items(*values, split_slash: bool = True) -> list[str]:
    merged = []
    seen = set()
    for val in values:
        for item in requirement_items(val, split_slash=split_slash):
            key = normalize_skill_key(item)
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def evaluate_requirements(resume, job, normalize=normalize_skill_key, related_terms=None):
    related = {normalize(k): v for k, v in DEFAULT_RELATED_TERMS.items()}
    related.update({normalize(k): v for k, v in (related_terms or {}).items()})
    responses = {
        (r.get("field"), normalize(str(r.get("requirement", "")))): r
        for r in resume.get("clarification_responses", []) or [] if isinstance(r, dict)
    }
    raw_evidence = " ".join(str(resume.get(k) or "") for k in
        ("skills", "skills_list", "experience", "relevance", "work_experiences", "certifications", "certifications_list", "raw_text"))
    evidence = normalize(raw_evidence)
    has_exp_evidence = has_explicit_experience_evidence(resume)
    work_exp_text = " | ".join(
        " ".join(str(w.get(k) or "") for k in ("job_title", "company_name", "description", "responsibilities"))
        for w in (resume.get("work_experiences") or []) if isinstance(w, dict)
    )
    rows = []
    for field, requirement_field, candidate in (
        ("skills", "skills_requirements", _merge_candidate_items(resume.get("skills"), resume.get("skills_list"))),
        ("certifications", "certifications_requirements", _merge_candidate_items(resume.get("certifications"), resume.get("certifications_list"), resume.get("candidate_certifications"), split_slash=False)),
        ("experience", "experience_requirements", _merge_candidate_items(resume.get("experience"), resume.get("relevance"), work_exp_text)),
    ):
        candidate_keys = {normalize(v) for v in candidate}
        for item in requirement_items(getattr(job, requirement_field, None), split_slash=(field != "certifications")):
            key = normalize(item)
            response = responses.get((field, key), {})
            answer = response.get("answer")
            if field == "experience" and is_pure_duration_requirement(item) and has_exp_evidence and answer not in ("yes", "some", "no"):
                # Pure duration requirements (e.g. "3yrs", "2 years") with explicit resume work history
                # are evaluated directly by duration/relevance matching rather than treated as unasked checklist items.
                continue
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
    for field, target in (("skills", "skills"), ("certifications", "certifications")):
        existing_sources = (
            (result.get("skills"), result.get("skills_list"))
            if field == "skills"
            else (result.get("certifications"), result.get("certifications_list"), result.get("candidate_certifications"))
        )
        items = _merge_candidate_items(*existing_sources)
        denied = {normalize_skill_key(r["requirement"]) for r in rows if r["field"] == field and r.get("answer") == "no"}
        items = [item for item in items if normalize_skill_key(item) not in denied]
        for row in rows:
            if row["field"] == field and row.get("answer") in ("yes", "some"):
                items.append(row["requirement"])
                if field == "certifications" and row.get("details"):
                    items.append(str(row["details"]).strip())
        deduped = list(dict.fromkeys(i for i in items if i))
        result[target] = " | ".join(deduped)
        if field == "skills" and "skills_list" in result:
            result["skills_list"] = deduped

    # Preserve existing work experience entries intact (never split prose on commas into fake entries).
    exp_rows = [r for r in rows if r["field"] == "experience" and r.get("answer") in ("yes", "some")]
    if exp_rows:
        existing_exp = str(result.get("experience") or "").strip()
        exp_entries = [e.strip() for e in re.split(r"[|\n]+", existing_exp) if e.strip()] if existing_exp else []
        for row in exp_rows:
            exp_entries.append(row["requirement"])
            if row.get("details"):
                exp_entries.append(str(row["details"]).strip())
            try:
                years = max(0.0, float(row.get("years") or 0))
                if years > 0:
                    result["years_experience"] = max(float(result.get("years_experience") or 0), years)
            except (ValueError, TypeError):
                pass
        result["experience"] = " | ".join(dict.fromkeys(exp_entries))
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
