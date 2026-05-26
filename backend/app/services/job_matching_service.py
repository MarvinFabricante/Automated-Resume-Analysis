import re
import logging
from difflib import SequenceMatcher
from app.models.job_description import JobDescription

logger = logging.getLogger(__name__)

AI_SCORE_WEIGHT = 0.80
RULE_SCORE_WEIGHT = 1.0 - AI_SCORE_WEIGHT

# Degree hierarchy for education matching
DEGREE_HIERARCHY = {
    "SENIOR HIGH SCHOOL": 1,
    "SHS": 1,
    "DIPLOMA/VOCATIONAL": 2,
    "ASSOCIATE": 3,
    "BACHELOR": 4,
    "MASTER": 5,
    "DOCTORATE": 6,
    "PHD": 6
}

def _normalize_skill(s: str) -> str:
    """Normalize a skill string for comparison."""
    if not s:
        return ""
    s = s.lower().strip()
    # Remove common suffixes/versions to improve matching (e.g., React.js -> react)
    s = re.sub(r'\.js$', '', s)
    s = re.sub(r'[^a-z0-9+#/ ]', '', s)
    return s.strip()


def _tokenize_skills(skills_str: str) -> list[str]:
    """Split a skills string into individual normalized tokens."""
    if not skills_str:
        return []
    
    # Split by pipe, comma, semicolon, or bullet
    raw = re.split(r'[|,;•\-]', skills_str)
    skills = []
    for s in raw:
        cleaned = _normalize_skill(s)
        if cleaned and len(cleaned) > 1:
            skills.append(cleaned)
    return skills


def _fuzzy_match(a: str, b: str, threshold: float = 0.75) -> bool:
    """Check if two skill strings are a fuzzy match."""
    if a == b:
        return True
    # Check if one contains the other
    if a in b or b in a:
        return True
    # Use SequenceMatcher for fuzzy comparison
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= threshold


# ── Experience Relevance Analysis ─────────────────────────────────────────
ROLE_FAMILY_KEYWORDS = {
    "software": ["developer", "engineer", "programmer", "coding", "software", "backend", "frontend", "fullstack", "devops", "sre", "qa", "testing", "automation"],
    "data": ["data", "analyst", "scientist", "machine learning", "ai", "analytics", "business intelligence", "statistics", "etl"],
    "design": ["designer", "ui", "ux", "graphic", "creative", "visual", "figma", "adobe", "illustration"],
    "marketing": ["marketing", "seo", "content", "social media", "digital marketing", "advertising", "brand", "copywriter"],
    "finance": ["accountant", "finance", "auditor", "bookkeeper", "financial", "cpa", "banking", "investment"],
    "hr": ["human resources", "hr", "recruiter", "talent", "hiring", "payroll", "compensation"],
    "sales": ["sales", "account executive", "business development", "relationship manager", "account manager"],
    "operations": ["operations", "logistics", "supply chain", "warehouse", "inventory", "procurement"],
    "healthcare": ["nurse", "doctor", "medical", "healthcare", "clinical", "pharmacy", "patient"],
    "education": ["teacher", "instructor", "professor", "tutor", "education", "training", "curriculum"],
    "service": ["cashier", "service crew", "barista", "waiter", "waitress", "food", "retail", "customer service", "fast food", "restaurant"],
    "admin": ["administrative", "secretary", "clerk", "receptionist", "office", "assistant"],
    "engineering": ["civil engineer", "mechanical engineer", "electrical engineer", "structural", "construction"],
    "legal": ["lawyer", "attorney", "paralegal", "legal", "compliance"],
    "management": ["manager", "director", "supervisor", "team lead", "head of", "vp", "chief"],
}

TRANSFERABLE_SKILLS = {
    "teamwork": ["team", "collaborate", "coordination", "group"],
    "communication": ["communication", "interpersonal", "presentation", "public speaking"],
    "customer service": ["customer", "client", "service", "support", "helpdesk"],
    "leadership": ["leader", "lead", "manage", "supervise", "mentor"],
    "problem solving": ["problem solving", "troubleshoot", "analytical", "critical thinking"],
    "time management": ["time management", "deadline", "prioritize", "multitask"],
    "adaptability": ["adaptable", "flexible", "versatile", "fast-paced"],
    "attention to detail": ["detail", "accuracy", "precise", "quality"],
}


def _detect_role_family(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    best_family, best_count = "", 0
    for family, keywords in ROLE_FAMILY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_family = family
    return best_family


def _identify_transferable_skills(experience_text: str) -> list[str]:
    if not experience_text:
        return []
    text_lower = experience_text.lower()
    return [name for name, indicators in TRANSFERABLE_SKILLS.items() if any(ind in text_lower for ind in indicators)]


def calculate_experience_relevance(resume_experience: str, resume_skills: str, job_title: str, job_description: str) -> dict:
    """
    Evaluate how RELEVANT the candidate's work experience is to the target job.
    Does NOT just count years — checks whether previous roles are related.
    """
    target_family = _detect_role_family(job_title + " " + (job_description or ""))
    resume_text = (resume_experience or "") + " " + (resume_skills or "")
    candidate_family = _detect_role_family(resume_text)
    transferable = _identify_transferable_skills(resume_text)
    job_kw = set(_tokenize_skills(job_title))
    exp_kw = set(_tokenize_skills(resume_experience or ""))
    direct_overlap = job_kw & exp_kw

    if not resume_experience or not resume_experience.strip():
        return {"relevance_level": "Irrelevant", "relevance_score": 0.1, "transferable_skills": transferable, "reason": "No work experience provided to evaluate relevance."}
    if target_family and candidate_family and target_family == candidate_family:
        return {"relevance_level": "Highly Relevant", "relevance_score": 0.9, "transferable_skills": transferable, "reason": f"Previous work experience is directly related to the {job_title} role."}
    if direct_overlap and len(direct_overlap) >= 2:
        return {"relevance_level": "Highly Relevant", "relevance_score": 0.85, "transferable_skills": transferable, "reason": f"Resume shares key terms with the target role: {', '.join(w.title() for w in list(direct_overlap)[:5])}."}
    if target_family and candidate_family and target_family != candidate_family and transferable:
        score = min(0.6, 0.25 + len(transferable) * 0.07)
        return {"relevance_level": "Partially Relevant", "relevance_score": round(score, 2), "transferable_skills": transferable, "reason": f"Different field but demonstrates transferable skills: {', '.join(transferable[:5])}."}
    if transferable:
        return {"relevance_level": "Partially Relevant", "relevance_score": 0.3, "transferable_skills": transferable, "reason": f"Limited relevance but transferable skills identified: {', '.join(transferable[:4])}."}
    return {"relevance_level": "Irrelevant", "relevance_score": 0.1, "transferable_skills": [], "reason": f"Previous work experience has little connection to the {job_title} role."}


def calculate_education_match(resume_education: str, job_description: str, education_req: str = None) -> dict:
    """Compare candidate's education level against job requirements."""
    required_level = _extract_education_requirement(education_req or "") or _extract_education_requirement(job_description)
    candidate_level = _extract_education_requirement(resume_education or "")

    if not required_level:
        score = 1.0 if candidate_level else 0.7
        return {"score": score, "required_education": "Not specified", "candidate_education": candidate_level or "Not specified", "reason": "No specific education requirement found in job description."}
    if not candidate_level:
        return {"score": 0.3, "required_education": required_level, "candidate_education": "Not specified", "reason": f"Job requires {required_level} level education, but none detected in resume."}

    req_rank = DEGREE_HIERARCHY.get(required_level, 0)
    cand_rank = DEGREE_HIERARCHY.get(candidate_level, 0)
    if cand_rank >= req_rank:
        return {"score": 1.0, "required_education": required_level, "candidate_education": candidate_level, "reason": f"Your {candidate_level} degree meets or exceeds the {required_level} requirement."}
    elif cand_rank == req_rank - 1:
        return {"score": 0.7, "required_education": required_level, "candidate_education": candidate_level, "reason": f"Your {candidate_level} degree is close to the required {required_level} level."}
    else:
        score = max(0.2, round(cand_rank / req_rank, 2) if req_rank > 0 else 0.2)
        return {"score": score, "required_education": required_level, "candidate_education": candidate_level, "reason": f"Your {candidate_level} degree does not meet the {required_level} requirement."}


def calculate_skills_match(resume_skills: str, job_skills: str) -> dict:
    """
    Compare resume skills against job requirements.
    Returns match ratio and lists of matched/missing skills.
    """

    resume_tokens = _tokenize_skills(resume_skills)
    job_tokens = _tokenize_skills(job_skills)
    
    if not job_tokens:
        return {"score": 1.0, "matched": [], "missing": []}
    if not resume_tokens:
        return {"score": 0.0, "matched": [], "missing": job_tokens}
    
    matched = []
    missing = []
    
    for job_skill in job_tokens:
        found = False
        for resume_skill in resume_tokens:
            if _fuzzy_match(resume_skill, job_skill):
                matched.append(job_skill)
                found = True
                break
        if not found:
            missing.append(job_skill)
    
    score = len(matched) / len(job_tokens) if job_tokens else 0.0
    return {"score": score, "matched": matched, "missing": missing}


def _extract_years_from_text(text: str) -> int:
    """Extract years of experience mentioned in a job description."""
    if not text:
        return 0
    
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
        r'(?:minimum|at least|min)\s*(?:of\s+)?(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:relevant|professional|work)',
    ]
    
    max_years = 0
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            try:
                max_years = max(max_years, int(m))
            except ValueError:
                continue
    
    return max_years


def calculate_experience_match(resume_years: int, job_description: str, experience_req: str = None) -> dict:
    """
    Compare resume years of experience against job requirements.
    Returns a dict with score and details.
    """
    required_years = 0
    if experience_req:
        # Check if experience_req is a pure number or text with number
        try:
            required_years = int(re.sub(r'[^\d]', '', experience_req))
        except ValueError:
            required_years = _extract_years_from_text(experience_req)
            
    if required_years == 0:
        required_years = _extract_years_from_text(job_description)
        
    resume_years = resume_years or 0
    
    if required_years == 0:
        # No explicit requirement — give full marks if candidate has any experience
        score = 1.0 if resume_years > 0 else 0.5
        reason = "No specific experience requirement found in job description." if resume_years > 0 else "No specific experience requirement, but no experience provided."
        return {"score": score, "required_years": 0, "candidate_years": resume_years, "reason": reason}
    
    if resume_years <= 0:
        return {"score": 0.2, "required_years": required_years, "candidate_years": 0, "reason": f"Required {required_years} years, but no experience was extracted from resume."}
    
    if resume_years >= required_years:
        return {"score": 1.0, "required_years": required_years, "candidate_years": resume_years, "reason": f"Your {resume_years} years of experience meets or exceeds the required {required_years} years."}
    
    # Proportional score
    score = round(resume_years / required_years, 2)
    return {"score": score, "required_years": required_years, "candidate_years": resume_years, "reason": f"You have {resume_years} years of experience, meeting {int(score*100)}% of the {required_years}-year requirement."}


def _extract_education_requirement(text: str) -> str:
    """Extract the education level required from a job description."""
    if not text:
        return ""
    
    text_upper = text.upper()
    
    # Check from highest to lowest
    checks = [
        ("DOCTORATE", [r"PH\.?D", r"DOCTORATE", r"DOCTOR"]),
        ("MASTER", [r"MASTER", r"MBA", r"GRADUATE\s+DEGREE"]),
        ("BACHELOR", [r"BACHELOR", r"BS\b", r"BA\b", r"B\.S\b", r"COLLEGE\s+DEGREE", r"UNDERGRADUATE"]),
        ("ASSOCIATE", [r"ASSOCIATE", r"2.YEAR\s+DEGREE"]),
        ("DIPLOMA/VOCATIONAL", [r"DIPLOMA", r"VOCATIONAL", r"TESDA", r"CERTIFICATE"]),
        ("SENIOR HIGH SCHOOL", [r"SENIOR\s+HIGH", r"SHS", r"HIGH\s+SCHOOL"]),
    ]
    
    for degree_label, patterns in checks:
        for p in patterns:
            if re.search(p, text_upper):
                return degree_label
    
    return ""


def calculate_certifications_match(resume_certs: str, job_description: str, certifications_req: str = None) -> dict:
    """
    Compare resume certifications against job requirements.
    Returns a dict with score and details.
    """
    required_certs = certifications_req or ""
    if not required_certs:
        if re.search(r'\b(certification|certified|certificate)\b', job_description, re.IGNORECASE):
            required_certs = "Relevant Certification"
            
    if not required_certs:
        return {"score": 1.0, "required_certifications": "None", "candidate_certifications": resume_certs or "None", "reason": "No specific certification requirement found."}
        
    if not resume_certs:
        return {"score": 0.3, "required_certifications": required_certs, "candidate_certifications": "None", "reason": f"Job requires {required_certs}, but no certifications were found."}
        
    req_tokens = _tokenize_skills(required_certs)
    if not req_tokens:
        return {"score": 1.0, "required_certifications": "None", "candidate_certifications": resume_certs, "reason": "No specific certification requirement found."}
        
    resume_tokens = _tokenize_skills(resume_certs)
    matched = []
    for req in req_tokens:
        if req in ['certification', 'certified', 'certificate']:
            continue
        for res in resume_tokens:
            if _fuzzy_match(res, req):
                matched.append(req)
                break
                
    if not matched:
        return {"score": 0.5, "required_certifications": required_certs, "candidate_certifications": "Unrelated", "reason": f"Your certifications do not match the required {required_certs}."}
        
    valid_reqs = [t for t in req_tokens if t not in ['certification', 'certified', 'certificate']]
    score = len(matched) / len(valid_reqs) if valid_reqs else 1.0
    score = min(1.0, score + 0.2)
    return {"score": score, "required_certifications": required_certs, "candidate_certifications": ", ".join(matched), "reason": f"Your certifications match {int(score*100)}% of the requirement."}


def _generate_recommendations(skills_result: dict, experience_result: dict, education_result: dict, job_title: str) -> list[str]:
    """
    Generate actionable optimization recommendations based on gap analysis.
    Returns a list of 2-3 bullet-point suggestions.
    """
    recommendations = []

    # Skills gap recommendation
    if skills_result["missing"] and len(skills_result["missing"]) > 0:
        missing_list = ", ".join([s.title() for s in skills_result["missing"][:5]])
        recommendations.append(
            f"Add the following in-demand skills to your resume: {missing_list}. "
            f"Consider taking online courses or certifications to demonstrate proficiency."
        )

    # Experience gap recommendation
    req_years = experience_result.get("required_years", 0)
    cand_years = experience_result.get("candidate_years", 0)
    if req_years > 0 and cand_years < req_years:
        gap = req_years - cand_years
        recommendations.append(
            f"The role requires {req_years} years of experience, but your resume reflects {cand_years}. "
            f"Highlight freelance projects, internships, or open-source contributions to bridge the {gap}-year gap."
        )
    elif cand_years == 0:
        recommendations.append(
            f"Quantify your work experience with specific durations (e.g., 'Jan 2022 – Present') "
            f"so the ATS can accurately calculate your tenure for the {job_title} role."
        )

    # Certifications recommendation
    req_certs = education_result.get("required_certifications", "")
    cand_certs = education_result.get("candidate_certifications", "")
    if req_certs and req_certs != "None" and not cand_certs:
        recommendations.append(
            f"The position requires {req_certs}. Consider pursuing these certifications to improve your candidacy."
        )
    elif not cand_certs or cand_certs == "None":
        recommendations.append(
            "Ensure your certifications section is clear and up-to-date so the ATS can evaluate your qualifications."
        )

    # Generic improvement if we haven't found enough specific gaps
    if len(recommendations) < 2:
        recommendations.append(
            f"Tailor your resume summary to mirror the language used in the {job_title} job description. "
            f"Use exact keywords and phrases to maximize ATS compatibility."
        )

    return recommendations[:3]


def _blend_scores(rule_score: float, ai_score: float, ai_available: bool) -> float:
    """
    Blend rule-based and AI scores.
    When AI is available: Gemini is dominant while rule-based checks stay as a guardrail.
    When AI is not available: 100% rule-based.
    """
    if not ai_available:
        return rule_score
    return round(rule_score * RULE_SCORE_WEIGHT + ai_score * AI_SCORE_WEIGHT, 4)


def _merge_unique(primary: list[str], secondary: list[str]) -> list[str]:
    """Merge skill lists without duplicating the same normalized skill."""
    merged = []
    seen = set()
    for skill in primary + secondary:
        clean = str(skill).strip()
        key = _normalize_skill(clean)
        if clean and key and key not in seen:
            merged.append(clean)
            seen.add(key)
    return merged


def calculate_match_score(resume_data: dict, job, use_ai: bool = False) -> dict:
    """
    Calculate the overall match score between a parsed resume and a job.

    Scoring Strategy:
    ─────────────────
    Rule-based component (weights: Skills 40% + Experience 40% + Education 20%):
      Precision keyword/fuzzy matching for verifiable fields.

    Gemini AI component (when available and requested):
      Semantic understanding of context, transferable skills, and nuance.

    Final blended score = Gemini-dominant when available, or 100% rule-based as fallback.
    """
    # ── Rule-based scoring ────────────────────────────────────────────────────
    resume_skills = resume_data.get("skills", "")
    job_skills = job.skills_requirements or ""
    skills_result = calculate_skills_match(resume_skills, job_skills)

    resume_years = resume_data.get("years_experience", 0) or 0
    job_desc = (job.description or "") + " " + (job.skills_requirements or "")
    experience_result = calculate_experience_match(resume_years, job_desc, getattr(job, 'experience_requirements', None))

    # Experience RELEVANCE analysis (not just years)
    resume_experience = resume_data.get("experience", "")
    relevance_result = calculate_experience_relevance(
        resume_experience, resume_skills, job.job_title, job_desc
    )
    # Combine years score with relevance score (relevance weighs more)
    combined_exp_score = (
        experience_result["score"] * 0.35 +
        relevance_result["relevance_score"] * 0.65
    )

    # Education matching (separate from certifications)
    resume_education = resume_data.get("education", "")
    education_result = calculate_education_match(
        resume_education, job_desc, getattr(job, 'education_requirements', None)
    )

    # Certifications matching
    resume_certs = resume_data.get("certifications", "") or resume_data.get("skills", "")
    certs_result = calculate_certifications_match(resume_certs, job_desc, getattr(job, 'certifications_requirements', None))

    # Projects score placeholder (rule-based: check if portfolio/projects mentioned)
    projects_score = 0.5  # default neutral
    resume_text_lower = (resume_data.get("experience", "") + " " + resume_data.get("skills", "")).lower()
    if any(kw in resume_text_lower for kw in ["project", "portfolio", "github", "gitlab", "open source", "capstone"]):
        projects_score = 0.8

    # ── Weighted rule-based composite ─────────────────────────────────────────
    # Skills 40% + Experience Relevance 30% + Education 15% + Certifications 10% + Projects 5%
    rule_match_pct = (
        skills_result["score"] * 0.40 +
        combined_exp_score * 0.30 +
        education_result["score"] * 0.15 +
        certs_result["score"] * 0.10 +
        projects_score * 0.05
    ) * 100


    # ── Gemini AI scoring ─────────────────────────────────────────────────────
    ai_result = None
    ai_available = False
    
    if use_ai:
        try:
            from app.services.ai_analysis_service import analyze_match_with_fallback
            job_data = {
                "job_title": job.job_title,
                "department": getattr(job, "department", ""),
                "description": job.description or "",
                "skills_requirements": job.skills_requirements or "",
                "experience_requirements": getattr(job, "experience_requirements", ""),
                "certifications_requirements": getattr(job, "certifications_requirements", ""),
            }
            ai_result = analyze_match_with_fallback(resume_data, job_data)
            if ai_result:
                ai_available = True
                model_used = ai_result.get("model_used", "ai")
                logger.info(f"{model_used.capitalize()} AI score for job '{job.job_title}': {ai_result['ai_match_score']}%")
        except Exception as e:
            logger.warning(f"Gemini match analysis skipped: {e}")

    # ── Blend scores ──────────────────────────────────────────────────────────
    if ai_available and ai_result:
        ai_match_pct = ai_result["ai_match_score"]  # already 0-100

        # Blend individual dimension scores too
        blended_skills_score = _blend_scores(
            skills_result["score"] * 100,
            ai_result.get("ai_skills_score", skills_result["score"] * 100),
            ai_available
        )
        blended_exp_score = _blend_scores(
            experience_result["score"] * 100,
            ai_result.get("ai_experience_score", experience_result["score"] * 100),
            ai_available
        )
        blended_edu_score = _blend_scores(
            education_result["score"] * 100,
            ai_result.get("ai_certifications_score", education_result["score"] * 100),
            ai_available
        )

        # Final match: Gemini-dominant score with deterministic rule checks retained.
        final_match_pct = min(100.0, round(rule_match_pct * RULE_SCORE_WEIGHT + ai_match_pct * AI_SCORE_WEIGHT, 1))

        # Merge matched/missing skills: union of both sources
        rule_matched = [s.title() for s in skills_result["matched"]]
        all_matched = _merge_unique(rule_matched, ai_result.get("matched_skills", []))

        rule_missing = [s.title() for s in skills_result["missing"]]
        all_missing = [
            skill for skill in _merge_unique(rule_missing, ai_result.get("missing_skills", []))
            if _normalize_skill(skill) not in {_normalize_skill(matched) for matched in all_matched}
        ]

        # Use AI recommendations if available, otherwise rule-based
        final_recommendations = (
            ai_result.get("recommendations") or
            _generate_recommendations(skills_result, experience_result, education_result, job.job_title)
        )

        ai_summary = ai_result.get("ai_summary", "")
        strengths = ai_result.get("strengths", [])
        weaknesses = ai_result.get("weaknesses", [])
        relevance_level = ai_result.get("relevance_level", "Unknown")
        score_explanation = ai_result.get("score_explanation", "")

    else:
        # Fallback: pure rule-based
        blended_skills_score = round(skills_result["score"] * 100, 1)
        blended_exp_score = round(experience_result["score"] * 100, 1)
        blended_edu_score = round(education_result["score"] * 100, 1)
        final_match_pct = min(100.0, round(rule_match_pct, 1))
        all_matched = [s.title() for s in skills_result["matched"]]
        all_missing = [s.title() for s in skills_result["missing"]]
        final_recommendations = _generate_recommendations(skills_result, experience_result, education_result, job.job_title)
        ai_summary = ""
        strengths = []
        weaknesses = []
        relevance_level = "Unknown"
        score_explanation = ""

    # ── Build reason strings ──────────────────────────────────────────────────
    total_job_skills = len(skills_result["matched"]) + len(skills_result["missing"])
    skills_reason = (
        f"Matched {len(all_matched)} out of {total_job_skills} required skills. "
        f"{'Strong alignment with the technical requirements.' if blended_skills_score >= 70 else 'Several critical skills from the job description are missing from the resume.'}"
    )

    experience_text = resume_data.get("experience", "")
    exp_entries = [e.strip() for e in experience_text.split("|") if e.strip()] if experience_text else []
    relevant_experience = " | ".join(exp_entries[:3]) if exp_entries else "No specific roles extracted."

    return {
        "job_id": job.job_id,
        "job_title": job.job_title,
        "department": job.department,
        "location": job.location,
        "job_type": job.job_type.value if job.job_type else None,
        # ── Scores ──
        "match_percentage": final_match_pct,
        "skills_score": round(blended_skills_score, 1),
        "experience_score": round(blended_exp_score, 1),
        "education_score": round(blended_edu_score, 1),
        "certifications_score": round(blended_edu_score, 1),
        # ── Skills ──
        "matched_skills": all_matched,
        "missing_skills": all_missing,
        # ── Reasons ──
        "skills_reason": skills_reason,
        "experience_reason": experience_result["reason"],
        "education_reason": education_result.get("reason", ""),
        "certifications_reason": education_result["reason"],
        # ── Experience ──
        "relevant_experience": relevant_experience,
        "experience_gaps": f"Required: {experience_result.get('required_years', 0)} yrs | Candidate: {experience_result.get('candidate_years', 0)} yrs",
        # ── Education / Certifications ──
        "required_degree": education_result.get("required_certifications", "None"),
        "candidate_degree": education_result.get("candidate_certifications", "None"),
        "required_certifications": education_result.get("required_certifications", "None"),
        "candidate_certifications": education_result.get("candidate_certifications", "None"),
        # ── AI Insights ──
        "recommendations": final_recommendations,
        "ai_summary": ai_summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "ai_powered": ai_available,
        "relevance_level": relevance_level,
        "score_explanation": score_explanation,
    }


async def match_resume_to_all_jobs(db, resume_data: dict, use_ai: bool = False) -> list[dict]:
    """
    Match parsed resume data against all active jobs in the database.
    Returns a list of match results sorted by match_percentage descending.
    """
    from app.repositories.job_description_repository import JobDescriptionRepository
    
    jobs = await JobDescriptionRepository.get_all_active(db, include_inactive=False)
    
    matches = []
    for job in jobs:
        match_result = calculate_match_score(resume_data, job, use_ai=use_ai)
        matches.append(match_result)
    
    # Sort by match percentage descending
    matches.sort(key=lambda x: x["match_percentage"], reverse=True)
    
    return matches


async def match_resume_to_job(db, resume_data: dict, job_id: str, use_ai: bool = False) -> dict | None:
    """
    Match parsed resume data against a single specific job.
    """
    from app.repositories.job_description_repository import JobDescriptionRepository
    
    job = await JobDescriptionRepository.get_by_job_id(db, job_id)
    
    if not job:
        return None
    
    return calculate_match_score(resume_data, job, use_ai=use_ai)


class JobMatchingService:
    _normalize_skill = staticmethod(_normalize_skill)
    _tokenize_skills = staticmethod(_tokenize_skills)
    _fuzzy_match = staticmethod(_fuzzy_match)
    calculate_skills_match = staticmethod(calculate_skills_match)
    _extract_years_from_text = staticmethod(_extract_years_from_text)
    calculate_experience_match = staticmethod(calculate_experience_match)
    _extract_education_requirement = staticmethod(_extract_education_requirement)
    calculate_certifications_match = staticmethod(calculate_certifications_match)
    _generate_recommendations = staticmethod(_generate_recommendations)
    _blend_scores = staticmethod(_blend_scores)
    _merge_unique = staticmethod(_merge_unique)
    calculate_match_score = staticmethod(calculate_match_score)

    async def match_resume_to_all_jobs(self, db, resume_data: dict, use_ai: bool = False) -> list[dict]:
        return await match_resume_to_all_jobs(db, resume_data, use_ai)

    async def match_resume_to_job(self, db, resume_data: dict, job_id: str, use_ai: bool = False) -> dict | None:
        return await match_resume_to_job(db, resume_data, job_id, use_ai)


job_matching_service = JobMatchingService()
