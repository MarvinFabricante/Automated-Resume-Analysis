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
    "software": ["developer", "engineer", "programmer", "coding", "software", "backend", "frontend", "fullstack", "devops", "sre", "qa", "testing", "automation", "api", "microservices", "ci/cd", "git", "agile", "scrum", "it support", "technical support", "systems", "deployment", "infrastructure", "it"],
    "data": ["data", "analyst", "scientist", "machine learning", "ai", "analytics", "business intelligence", "statistics", "etl", "big data", "data pipeline", "deep learning"],
    "design": ["designer", "ui", "ux", "graphic", "creative", "visual", "figma", "adobe", "illustration", "wireframe", "prototype"],
    "marketing": ["marketing", "seo", "content", "social media", "digital marketing", "advertising", "brand", "copywriter", "campaign"],
    "finance": ["accountant", "finance", "auditor", "bookkeeper", "financial", "cpa", "banking", "investment", "tax", "budget"],
    "hr": ["human resources", "hr", "recruiter", "talent", "hiring", "payroll", "compensation", "onboarding"],
    "sales": ["sales", "account executive", "business development", "relationship manager", "account manager", "revenue"],
    "operations": ["operations", "logistics", "supply chain", "warehouse", "inventory", "procurement", "shipping"],
    "healthcare": ["nurse", "doctor", "medical", "healthcare", "clinical", "pharmacy", "patient", "diagnosis"],
    "education": ["teacher", "instructor", "professor", "tutor", "education", "training", "curriculum", "academic"],
    "service": ["cashier", "service crew", "barista", "waiter", "waitress", "food", "retail", "customer service", "fast food", "restaurant", "counter", "crew member", "food service"],
    "admin": ["administrative", "secretary", "clerk", "receptionist", "office", "assistant", "filing", "clerical"],
    "engineering": ["civil engineer", "mechanical engineer", "electrical engineer", "structural", "construction", "cad", "blueprint"],
    "legal": ["lawyer", "attorney", "paralegal", "legal", "compliance", "litigation"],
    "management": ["manager", "director", "supervisor", "team lead", "head of", "vp", "chief"],
    "manufacturing": ["factory", "assembly", "production", "manufacturing", "quality control", "machine operator", "factory worker", "laborer"],
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

# Maximum score transferable skills alone can contribute (out of 10)
_TRANSFERABLE_ONLY_CAP = 2


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


def _detect_all_role_families(text: str) -> dict[str, int]:
    """Return a dict mapping each role family to the number of keyword hits."""
    if not text:
        return {}
    text_lower = text.lower()
    result = {}
    for family, keywords in ROLE_FAMILY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            result[family] = count
    return result


def _identify_transferable_skills(experience_text: str) -> list[str]:
    if not experience_text:
        return []
    text_lower = experience_text.lower()
    return [name for name, indicators in TRANSFERABLE_SKILLS.items() if any(ind in text_lower for ind in indicators)]


def _compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Use spaCy document vectors to compute a semantic similarity score between
    two text fragments. Returns 0.0 if NLP is unavailable, the model has no
    real word vectors (e.g. en_core_web_sm), or vectors are empty.

    NOTE: en_core_web_sm does NOT ship with word vectors; its .similarity()
    uses context-sensitive tensors that give misleadingly high scores for
    unrelated text.  We detect this and return 0.0 to avoid score inflation.
    """
    try:
        from app.extractors.nlp.nlp_engine import get_doc, get_nlp
        import warnings

        # Check if the loaded model actually has word vectors
        nlp = get_nlp()
        model_name = nlp.meta.get("name", "")
        # Small models (e.g. en_core_web_sm) don't have real word vectors
        if model_name.endswith("sm"):
            return 0.0

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc_a = get_doc(text_a)
            doc_b = get_doc(text_b)
            if doc_a.vector_norm == 0 or doc_b.vector_norm == 0:
                return 0.0
            sim = doc_a.similarity(doc_b)
            return max(0.0, min(1.0, sim))
    except Exception:
        return 0.0


def _count_job_keyword_hits(entry_text: str, job_keywords: set[str]) -> tuple[int, list[str]]:
    """
    Count how many job-requirement keywords appear in an experience entry.
    Returns (count, list_of_matched_keywords).
    """
    entry_lower = entry_text.lower()
    matched = [kw for kw in job_keywords if kw in entry_lower and len(kw) > 2]
    return len(matched), matched


def _validate_verb_objects_against_job(verbs_objs: list[tuple[str, str]], job_text_lower: str) -> list[tuple[str, str]]:
    """
    Filter verb-object pairs to only those whose object terms appear in the
    job description/requirements. This prevents crediting unrelated actions.
    """
    relevant = []
    for verb, obj in verbs_objs:
        obj_tokens = [t.strip().lower() for t in obj.split() if len(t.strip()) > 2]
        if any(tok in job_text_lower for tok in obj_tokens):
            relevant.append((verb, obj))
    return relevant


def calculate_experience_relevance(resume_experience: str, resume_skills: str, job_title: str, job_description: str) -> dict:
    """
    Evaluate how RELEVANT the candidate's work experience is to the target job.

    STRICT SCORING POLICY:
    ─────────────────────
    • Irrelevant experience contributes ZERO to the experience score.
    • Only relevant entries count toward the denominator/maximum score.
    • Transferable skills alone are capped at a small contribution.
    • Semantic similarity (spaCy vectors) gates borderline decisions.
    • Each entry receives a transparent explanation of why it was scored.

    Uses a hybrid approach (NLP, spaCy semantic similarity, keyword matching,
    rule-based validation) to analyze each entry individually.
    """
    try:
        from app.extractors.nlp.nlp_engine import get_doc, get_verb_object_pairs
        nlp_available = True
    except ImportError:
        nlp_available = False

    job_text = job_title + " " + (job_description or "")
    job_text_lower = job_text.lower()
    target_family = _detect_role_family(job_text)
    target_families = _detect_all_role_families(job_text)
    job_kw = set(_tokenize_skills(job_text))

    exp_entries = [e.strip() for e in (resume_experience or "").split("|") if e.strip()]
    if not exp_entries:
        return {
            "relevance_level": "Irrelevant",
            "relevance_score": 0.0,
            "transferable_skills": [],
            "reason": "No work experience provided to evaluate relevance.",
            "detailed_breakdown": "No work experience provided.",
            "relevant_count": 0,
            "irrelevant_count": 0,
            "total_entries": 0,
        }

    relevant_scores = []     # Scores from Highly Relevant / Partially Relevant entries only
    all_transferable = set()
    breakdown_texts = []
    relevant_count = 0
    irrelevant_count = 0

    for i, entry in enumerate(exp_entries):
        candidate_family = _detect_role_family(entry)
        candidate_families = _detect_all_role_families(entry)
        entry_kw = set(_tokenize_skills(entry))
        direct_overlap = job_kw & entry_kw
        transferable = _identify_transferable_skills(entry)
        all_transferable.update(transferable)

        # Semantic similarity between the experience entry and the job description
        semantic_sim = _compute_semantic_similarity(entry, job_text) if nlp_available else 0.0

        # Job keyword hits inside the entry
        kw_hit_count, kw_hits = _count_job_keyword_hits(entry, job_kw)

        # NLP verb-object pair extraction & validation
        verbs_objs = []
        relevant_verbs_objs = []
        if nlp_available:
            entry_doc = get_doc(entry)
            verbs_objs = get_verb_object_pairs(entry_doc)
            relevant_verbs_objs = _validate_verb_objects_against_job(verbs_objs, job_text_lower)

        # ── Multi-signal relevance classification ─────────────────────────
        score_contrib = 0
        relevance = "Irrelevant"
        reasons = []

        # Check if there is family overlap (including secondary families)
        family_match = (target_family and candidate_family and target_family == candidate_family)
        secondary_family_overlap = bool(set(target_families.keys()) & set(candidate_families.keys())) if not family_match else False

        if family_match:
            # ── Highly Relevant: same domain ──
            relevance = "Highly Relevant"
            score_contrib = 8
            reasons.append(
                f"✅ Domain alignment: Role is in the '{candidate_family.title()}' family, "
                f"directly matching the target job '{target_family.title()}'."
            )
            # Bonus for strong keyword or semantic overlap
            if len(direct_overlap) >= 3 or semantic_sim >= 0.6:
                score_contrib = min(10, score_contrib + 1)
                reasons.append(f"✅ Additional technical alignment detected (keyword overlap: {len(direct_overlap)}, semantic similarity: {semantic_sim:.0%}).")

        elif len(direct_overlap) >= 3 or (len(direct_overlap) >= 2 and semantic_sim >= 0.5):
            # ── Highly Relevant: strong technical/keyword overlap even if family differs ──
            relevance = "Highly Relevant"
            score_contrib = 7
            overlap_sample = ', '.join(list(direct_overlap)[:4])
            reasons.append(
                f"✅ Strong technical alignment: {len(direct_overlap)} overlapping keywords/technologies "
                f"({overlap_sample}), semantic similarity: {semantic_sim:.0%}."
            )

        elif secondary_family_overlap and (len(direct_overlap) >= 1 or semantic_sim >= 0.45):
            # ── Partially Relevant: related domain with some evidence ──
            overlap_families = set(target_families.keys()) & set(candidate_families.keys())
            relevance = "Partially Relevant"
            score_contrib = 4
            reasons.append(
                f"⚠️ Related domain overlap in: {', '.join(f.title() for f in overlap_families)}. "
                f"Keyword overlap: {len(direct_overlap)}, semantic similarity: {semantic_sim:.0%}."
            )

        elif semantic_sim >= 0.55 and kw_hit_count >= 2:
            # ── Partially Relevant: semantic similarity with keyword evidence ──
            relevance = "Partially Relevant"
            score_contrib = 4
            reasons.append(
                f"⚠️ Moderate semantic similarity ({semantic_sim:.0%}) with "
                f"{kw_hit_count} job keyword hits ({', '.join(kw_hits[:3])})."
            )

        elif len(relevant_verbs_objs) >= 2:
            # ── Partially Relevant: matched responsibilities via NLP ──
            relevance = "Partially Relevant"
            score_contrib = 3
            vo_text = ", ".join([f"{v} {o}" for v, o in relevant_verbs_objs[:3]])
            reasons.append(
                f"⚠️ Matched job-relevant responsibilities via NLP analysis: {vo_text}."
            )

        elif transferable and (semantic_sim >= 0.35 or len(direct_overlap) >= 1):
            # ── Minimally Relevant: only transferable skills with weak signal ──
            relevance = "Partially Relevant"
            score_contrib = min(_TRANSFERABLE_ONLY_CAP, len(transferable))
            reasons.append(
                f"⚠️ Limited relevance. Transferable skills detected but no direct "
                f"technical or domain alignment. Score capped at {_TRANSFERABLE_ONLY_CAP}/10."
            )

        else:
            # ── Irrelevant: no meaningful signal ──
            relevance = "Irrelevant"
            score_contrib = 0  # STRICT: zero contribution
            if candidate_family:
                reasons.append(
                    f"❌ Experience is in the '{candidate_family.title()}' domain, "
                    f"which is not related to the target '{target_family.title() if target_family else 'Unknown'}' domain."
                )
            else:
                reasons.append("❌ No recognizable professional domain detected in this entry.")
            reasons.append(
                "❌ No technical tools, relevant technologies, or domain-specific "
                "responsibilities were found that align with the target position."
            )
            if transferable:
                reasons.append(
                    f"ℹ️ Transferable skills noted ({', '.join(transferable)}), but they are "
                    f"insufficient on their own to generate a score for this specific role."
                )

        # ── Add supplementary detail ─────────────────────────────────────
        if transferable and relevance != "Irrelevant":
            reasons.append(f"ℹ️ Transferable skills: {', '.join(transferable)}.")

        if relevant_verbs_objs and relevance != "Irrelevant":
            vo_text = ", ".join([f"{v} {o}" for v, o in relevant_verbs_objs[:3]])
            reasons.append(f"ℹ️ Job-relevant responsibilities (NLP): {vo_text}.")
        elif verbs_objs and not relevant_verbs_objs and relevance != "Irrelevant":
            reasons.append("ℹ️ Responsibilities were detected but none align with the target job requirements.")

        if semantic_sim > 0:
            reasons.append(f"ℹ️ Semantic similarity to job description: {semantic_sim:.0%}.")

        # ── Track scores ─────────────────────────────────────────────────
        if relevance in ("Highly Relevant", "Partially Relevant"):
            relevant_scores.append(score_contrib)
            relevant_count += 1
        else:
            irrelevant_count += 1

        breakdown_texts.append(
            f"{i+1}. {entry}\n"
            f"   Relevance Level: {relevance}\n"
            f"   Score Contribution: +{score_contrib}/10"
            f"{' (NOT counted — irrelevant)' if relevance == 'Irrelevant' else ''}\n"
            f"   Reason:\n   - " + "\n   - ".join(reasons) + "\n"
        )

    # ── Final score: only relevant entries count ─────────────────────────
    if relevant_scores:
        # Score is average of relevant entries, normalized to [0, 1]
        avg_relevant = sum(relevant_scores) / len(relevant_scores)
        final_score = min(1.0, avg_relevant / 10.0)
    else:
        # No relevant experience at all
        final_score = 0.0

    # ── Determine overall level ─────────────────────────────────────────
    if final_score >= 0.65:
        overall_level = "Highly Relevant"
    elif final_score >= 0.30:
        overall_level = "Partially Relevant"
    else:
        overall_level = "Irrelevant"

    # ── Summary line ────────────────────────────────────────────────────
    summary_parts = [
        f"Evaluated {len(exp_entries)} experience(s) using Hybrid NLP + Semantic analysis.",
        f"Relevant: {relevant_count} | Irrelevant: {irrelevant_count}.",
    ]
    if irrelevant_count > 0 and relevant_count == 0:
        summary_parts.append(
            "None of the candidate's work experience is relevant to the target position. "
            "Experience score reflects zero qualifying entries."
        )
    elif irrelevant_count > 0:
        summary_parts.append(
            f"{irrelevant_count} experience(s) were excluded from scoring because they are "
            f"not relevant to the target job."
        )

    return {
        "relevance_level": overall_level,
        "relevance_score": round(final_score, 2),
        "transferable_skills": list(all_transferable),
        "reason": " ".join(summary_parts),
        "detailed_breakdown": (
            "Work Experience Breakdown (Strict Relevance Evaluation):\n"
            f"Target Position: {job_title}\n"
            f"Target Domain: {target_family.title() if target_family else 'General'}\n"
            f"Relevant Entries: {relevant_count}/{len(exp_entries)} | "
            f"Irrelevant (excluded): {irrelevant_count}/{len(exp_entries)}\n"
            f"Relevance Score: {final_score:.0%}\n\n"
            + "\n".join(breakdown_texts)
        ),
        "relevant_count": relevant_count,
        "irrelevant_count": irrelevant_count,
        "total_entries": len(exp_entries),
    }


def _find_education_context(text: str) -> str:
    """Extract sentences from job description that likely contain education requirements."""
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    ed_sentences = []
    level_pattern = r'\b(bachelor|master|doctorate|ph\.?d|degree|university|college|graduated)\b'
    for s in sentences:
        if re.search(level_pattern, s, re.IGNORECASE):
            ed_sentences.append(s)
    return " ".join(ed_sentences)


def _extract_core_subject(text: str) -> str:
    """Extract the core field of study by removing generic degree terms."""
    if not text:
        return ""
    level_pattern = r'\b(bachelor\'?s?|master\'?s?|doctorate|ph\.?d|associate\'?s?|diploma|degree|of|in|the|at|bs|ba|ms|ma|bsc|msc|b\.s\.?|m\.s\.?|b\.a\.?|m\.a\.?|undergraduate|graduate|postgraduate|majoring|major)\b'
    text = re.sub(level_pattern, ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'[^\w\s]', ' ', text)
    words = [w for w in text.lower().split() if len(w) > 2]
    return " ".join(words)


def calculate_education_match(resume_education: str, job_description: str, education_req: str = None) -> dict:
    """
    Compare candidate's education against job requirements with STRICT matching.
    Only assigns percentage scores if the degree field is exactly or highly relevant.
    """
    req_text = education_req if education_req else _find_education_context(job_description)
    cand_text = resume_education or ""
    
    required_level = _extract_education_requirement(req_text)
    candidate_level = _extract_education_requirement(cand_text)

    if not required_level and not req_text.strip():
        score = 1.0 if candidate_level else 0.7
        return {
            "score": score, 
            "required_education": "Not specified", 
            "candidate_education": candidate_level or "Not specified", 
            "reason": "No specific education requirement found in job description."
        }

    if not candidate_level and not cand_text.strip():
        return {
            "score": 0.0, 
            "required_education": required_level or req_text, 
            "candidate_education": "Not specified", 
            "reason": f"Job requires education ({required_level or 'specified in description'}), but no education details were found in the resume."
        }
        
    req_rank = DEGREE_HIERARCHY.get(required_level, 0)
    cand_rank = DEGREE_HIERARCHY.get(candidate_level, 0)
    
    level_met = False
    level_reason = ""
    if req_rank > 0 and cand_rank > 0:
        if cand_rank >= req_rank:
            level_met = True
            level_reason = f"Candidate meets the required {required_level} degree level."
        else:
            level_met = False
            level_reason = f"Candidate's {candidate_level} is below the required {required_level}."
    else:
        level_met = True
        level_reason = "Degree level inferred from context."

    req_subject = _extract_core_subject(req_text)
    cand_subject = _extract_core_subject(cand_text)

    if not req_subject:
        if level_met:
            return {
                "score": 1.0, 
                "required_education": required_level or "Degree", 
                "candidate_education": candidate_level or cand_text, 
                "reason": f"Required degree level met. No specific major was required. {level_reason}"
            }
        else:
            return {
                "score": 0.0, 
                "required_education": required_level or "Degree", 
                "candidate_education": candidate_level or cand_text, 
                "reason": f"Required degree level not met. {level_reason}"
            }

    if not cand_subject:
        return {
            "score": 0.0, 
            "required_education": req_text, 
            "candidate_education": cand_text, 
            "reason": f"Job requires a specific major (related to '{req_subject}') but candidate education only mentions generic terms."
        }

    req_tokens = set(req_subject.split())
    cand_tokens = set(cand_subject.split())
    
    generic_subject_words = {"science", "arts", "applied", "general", "course", "program"}
    req_core = req_tokens - generic_subject_words
    cand_core = cand_tokens - generic_subject_words
    
    if not req_core:
        req_core = req_tokens
    if not cand_core:
        cand_core = cand_tokens

    overlap = req_core & cand_core
    overlap_ratio = len(overlap) / len(req_core) if req_core else 0.0

    semantic_sim = _compute_semantic_similarity(req_subject, cand_subject)
    
    RELATED_MAJORS = {
        "computer science": ["information technology", "software engineering", "computer engineering", "information systems", "computing"],
        "information technology": ["computer science", "software engineering", "computer engineering", "information systems", "computing"],
        "business": ["management", "administration", "commerce", "finance", "accounting", "marketing"],
        "engineering": ["mechanical", "electrical", "civil", "chemical", "industrial", "software"],
    }
    
    is_related = False
    for req_field, related_list in RELATED_MAJORS.items():
        if all(w in req_subject for w in req_field.split()):
            for rel in related_list:
                if all(w in cand_subject for w in rel.split()):
                    is_related = True
                    break
                    
    score = 0.0
    match_quality = "Irrelevant"
    reason_details = []
    
    if level_met:
        if overlap_ratio >= 0.6 or (len(overlap) >= 2):
            score = 1.0
            match_quality = "Exact/Strong Match"
            reason_details.append(f"Major strictly aligns with requirements (Matched terms: {', '.join(overlap)}).")
        elif is_related or (semantic_sim >= 0.6 and len(overlap) >= 1):
            score = 0.8
            match_quality = "Highly Relevant Match"
            reason_details.append(f"Major is highly relevant to the required field.")
        elif overlap_ratio > 0 or semantic_sim >= 0.4:
            score = 0.5
            match_quality = "Partial Match"
            reason_details.append(f"Major has partial relevance to the required field.")
        else:
            score = 0.0
            match_quality = "Mismatch"
            reason_details.append(f"Candidate's major ('{cand_subject}') does not match the required field ('{req_subject}').")
    else:
        if overlap_ratio >= 0.5 or is_related:
            score = 0.5
            match_quality = "Lower Degree Level"
            reason_details.append(f"Major is relevant, but degree level is lower than required.")
        else:
            score = 0.0
            match_quality = "Mismatch"
            reason_details.append(f"Neither degree level nor major match requirements.")

    final_reason = f"{match_quality}: {level_reason} " + " ".join(reason_details)
    
    return {
        "score": score,
        "required_education": required_level or req_text,
        "candidate_education": candidate_level or cand_text,
        "reason": final_reason.strip()
    }


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
    # STRICT COMBINED SCORE: Relevance dominates at 75%.
    # If zero relevant experience, the years score is heavily penalized to
    # prevent unrelated job histories from inflating the percentage.
    relevance_score = relevance_result["relevance_score"]
    has_any_relevant = relevance_result.get("relevant_count", 0) > 0
    if not has_any_relevant:
        # All experience is irrelevant: cap the combined score very low
        combined_exp_score = min(0.10, experience_result["score"] * 0.10)
    else:
        combined_exp_score = (
            experience_result["score"] * 0.25 +
            relevance_score * 0.75
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
        # Use the relevance-adjusted combined score as the rule-based component,
        # NOT the raw years score.  This ensures irrelevant experience cannot
        # inflate the blended percentage.
        blended_exp_score = _blend_scores(
            combined_exp_score * 100,
            ai_result.get("ai_experience_score", combined_exp_score * 100),
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
        score_explanation = ai_result.get("score_explanation", "") # Backwards compatibility if needed
        match_level = ai_result.get("match_level", "Unknown")
        skills_explanation = ai_result.get("skills_explanation", "")
        
        # Blended Experience Explanation: Use hybrid NLP detailed breakdown + LLM insights
        hybrid_breakdown = relevance_result.get("detailed_breakdown", "")
        llm_exp_reason = ai_result.get("experience_explanation", "")
        if hybrid_breakdown and llm_exp_reason:
            experience_explanation = f"{hybrid_breakdown}\n\n--- AI Reasoning ---\n{llm_exp_reason}"
        else:
            experience_explanation = hybrid_breakdown or llm_exp_reason

        education_explanation = ai_result.get("education_explanation", "")
        certification_explanation = ai_result.get("certification_explanation", "")
        projects_explanation = ai_result.get("projects_explanation", "")
        transferable_skills = ai_result.get("transferable_skills", [])
        blended_projects_score = _blend_scores(
            projects_score * 100,
            ai_result.get("ai_projects_score", projects_score * 100),
            ai_available
        )

    else:
        # Fallback: pure rule-based
        blended_skills_score = round(skills_result["score"] * 100, 1)
        # Use relevance-adjusted combined score, not raw years
        blended_exp_score = round(combined_exp_score * 100, 1)
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
        match_level = "Unknown"
        skills_explanation = ""
        experience_explanation = relevance_result.get("detailed_breakdown", "")
        education_explanation = ""
        certification_explanation = ""
        projects_explanation = ""
        transferable_skills = relevance_result.get("transferable_skills", [])
        blended_projects_score = round(projects_score * 100, 1)

    # ── Build reason strings ──────────────────────────────────────────────────
    total_job_skills = len(skills_result["matched"]) + len(skills_result["missing"])
    skills_reason = (
        f"Matched {len(all_matched)} out of {total_job_skills} required skills. "
        f"{'Strong alignment with the technical requirements.' if blended_skills_score >= 70 else 'Several critical skills from the job description are missing from the resume.'}"
    )

    experience_text = resume_data.get("experience", "")
    exp_entries = [e.strip() for e in experience_text.split("|") if e.strip()] if experience_text else []
    relevant_experience = " | ".join(exp_entries[:3]) if exp_entries else "No specific roles extracted."

    # Build a relevance-aware experience reason
    rel_count = relevance_result.get("relevant_count", 0)
    irr_count = relevance_result.get("irrelevant_count", 0)
    total_exp = relevance_result.get("total_entries", len(exp_entries))
    experience_reason_strict = experience_result["reason"]
    if total_exp > 0:
        if rel_count == 0:
            experience_reason_strict = (
                f"None of the {total_exp} work experience(s) are relevant to this position. "
                f"Experience score reflects zero qualifying entries."
            )
        elif irr_count > 0:
            experience_reason_strict = (
                f"{rel_count} of {total_exp} experience(s) are relevant. "
                f"{irr_count} irrelevant experience(s) were excluded from scoring. "
                + experience_result["reason"]
            )

    return {
        "job_id": job.job_id,
        "job_title": job.job_title,
        "department": job.department,
        "location": job.location,
        "job_type": job.job_type.value if job.job_type else None,
        # ── Scores ──
        "match_percentage": final_match_pct,
        "match_level": match_level,
        "skills_score": round(blended_skills_score, 1),
        "skills_explanation": skills_explanation,
        "experience_score": round(blended_exp_score, 1),
        "experience_explanation": experience_explanation,
        "education_score": round(blended_edu_score, 1),
        "education_explanation": education_explanation,
        "certifications_score": round(blended_edu_score, 1), # using edu score as per existing fallback, ideally should be blended_certs_score but preserving logic
        "certification_explanation": certification_explanation,
        "projects_score": round(blended_projects_score, 1),
        "projects_explanation": projects_explanation,
        # ── Skills ──
        "matched_skills": all_matched,
        "missing_skills": all_missing,
        "transferable_skills": transferable_skills,
        # ── Reasons ──
        "skills_reason": skills_reason,
        "experience_reason": experience_reason_strict,
        "experience_relevance_summary": relevance_result.get("reason", ""),
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
