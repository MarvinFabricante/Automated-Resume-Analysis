from app.extractors.text_normalization import SKILL_SEPARATOR, normalize_skill_key, repair_line_hyphenation
import re
import json
import math
import logging
from typing import Optional, Any, List, Dict
from difflib import SequenceMatcher
from app.models.job_description import JobDescription
from app.services.requirement_rules import (
    STATUS_MEETS,
    STATUS_EXCEEDS,
    STATUS_PARTIAL,
    STATUS_NOT_REQUIRED,
    STATUS_MANUAL_REVIEW,
    STATUS_DOES_NOT_MEET,
    format_criterion_reason,
    NO_VALUE_MARKERS,
    normalize_requirement_text,
    is_no_value,
    clean_list_items,
    EDUCATION_LEVELS,
    EDUCATION_SHORT_LABELS,
    EDUCATION_MANUAL_REVIEW_SCORE,
    EDUCATION_LEVEL_MET_WRONG_FIELD_SCORE,
    EDUCATION_LEVEL_MET_UNSPECIFIED_FIELD_SCORE,
    EDUCATION_RELATED_FIELD_SCORE,
    EDUCATION_PARTIAL_FIELD_SCORE,
    EDUCATION_FIELD_SYNONYMS,
    RELATED_EDUCATION_FIELDS,
    parse_education_level,
    compute_education_partial_score,
    compare_graded_certifications,
)

logger = logging.getLogger(__name__)

# Thesis-documented default scoring weights (total = 100%).
# Single source of truth: every new job starts with these unless the admin adjusts them.
WEIGHT_KEYS = (
    "skills_weight",
    "experience_weight",
    "education_weight",
    "certifications_weight",
    "completeness_weight",
)

# Configurable per-criterion weight bounds (whole-number percentages).
MIN_WEIGHT_PCT = 5
MAX_WEIGHT_PCT = 70

THESIS_DEFAULT_WEIGHTS = {
    "skills_weight": 0.40,          # Skills Match
    "experience_weight": 0.30,      # Work Experience Relevance
    "education_weight": 0.15,       # Educational Background
    "certifications_weight": 0.10,  # Certifications and Trainings
    "completeness_weight": 0.05,    # Resume Completeness
}


def validate_scoring_weights(raw: Any) -> Dict[str, float]:
    """
    Strictly validate a 5-criterion scoring weight mapping on the server:
    - All five criteria must be present
    - Each weight must be a whole-number percentage between MIN_WEIGHT_PCT and MAX_WEIGHT_PCT
    - The five weights must sum to exactly 100%
    Raises ValueError with a clear message on any violation.
    """
    if not isinstance(raw, dict):
        try:
            raw = dict(raw)
        except (TypeError, ValueError):
            raise ValueError("Scoring weights must be a key-value mapping.")

    pcts: Dict[str, int] = {}
    for key in WEIGHT_KEYS:
        val = raw.get(key)
        if val is None:
            raise ValueError(f"Missing required weight: {key}.")
        try:
            num = float(val)
        except (TypeError, ValueError):
            raise ValueError(f"Weight '{key}' must be a number.")
        if abs(num * 100 - round(num * 100)) > 1e-4:
            raise ValueError(f"Weight '{key}' must be a whole-number percentage (got {round(num * 100, 2)}%).")
        pct = int(round(num * 100))
        if pct < MIN_WEIGHT_PCT or pct > MAX_WEIGHT_PCT:
            raise ValueError(
                f"Weight '{key}' must be between {MIN_WEIGHT_PCT}% and {MAX_WEIGHT_PCT}% (got {pct}%)."
            )
        pcts[key] = pct

    total_pct = sum(pcts.values())
    if total_pct != 100:
        raise ValueError(f"Scoring weights must add up to exactly 100% (currently {total_pct}%).")

    return {key: round(pct / 100.0, 2) for key, pct in pcts.items()}


def normalize_scoring_weights(raw: Any) -> Optional[Dict[str, float]]:
    """
    Coerce a stored/submitted weights payload (dict or JSON string) into a clean
    dict containing exactly the five scoring components. Returns None when the
    payload is missing or unusable so callers can fall back to the global default.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, dict):
        try:
            raw = dict(raw)
        except (TypeError, ValueError):
            return None

    cleaned: Dict[str, float] = {}
    for key in WEIGHT_KEYS:
        value = raw.get(key)
        if value is None:
            return None
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if num < 0:
            return None
        cleaned[key] = num

    if sum(cleaned.values()) <= 0:
        return None
    return cleaned


def get_job_scoring_weights(job: Any) -> Optional[Dict[str, float]]:
    """Return the job-specific weights (if the job has valid custom weights), else None."""
    if job is None:
        return None
    if isinstance(job, dict):
        raw = job.get("scoring_weights")
    else:
        raw = getattr(job, "scoring_weights", None)
    return normalize_scoring_weights(raw)


_DEFAULT_MATCHING_CONFIG = {
    "weights": dict(THESIS_DEFAULT_WEIGHTS),
    "thresholds": {
        "fuzzy_match_threshold": 0.75,
        "minimum_match_score": 30.0,
        "transferable_skills_cap": 2
    }
}


def get_current_matching_config() -> dict:
    """
    Retrieve active matching parameters from Redis or fallback to defaults.
    Zero-overhead access (< 0.1ms) across async tasks and Celery workers.
    """
    try:
        from app.utils.redis_client import get_sync_redis
        client = get_sync_redis()
        cached = client.get("matching_config:active")
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode("utf-8")
            data = json.loads(cached)
            if isinstance(data, dict) and "weights" in data and "thresholds" in data:
                return data
    except Exception as e:
        logger.debug(f"Failed to fetch matching config from Redis: {e}")

    return _DEFAULT_MATCHING_CONFIG

AI_SCORE_WEIGHT = 0.0
RULE_SCORE_WEIGHT = 1.0 - AI_SCORE_WEIGHT

# Shared 1-8 education level hierarchy (derived from canonical config in requirement_rules.py)
DEGREE_HIERARCHY: dict[str, int] = {
    **{label.upper(): lvl for lvl, label in EDUCATION_LEVELS.items()},
    **{label.upper(): lvl for lvl, label in EDUCATION_SHORT_LABELS.items()},
    "JUNIOR HIGH SCHOOL": 2,
    "SHS": 3,
    "DIPLOMA/VOCATIONAL": 4,
    "ASSOCIATE": 5,
    "BACHELOR": 6,
    "MASTER": 7,
    "PHD": 8,
}

_SKILL_SYNONYMS = {
    "ml": "machine learning",
    "ai/ml": "machine learning",
    "qc": "quality control",
    "qa/qc": "quality control",
    "qa": "quality assurance",
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "nlp": "natural language processing",
}


def _normalize_skill(s: str) -> str:
    """Normalize a skill string for comparison."""
    if not s or is_no_value(s):
        return ""
    s = normalize_skill_key(s)
    # Remove common suffixes/versions to improve matching (e.g., React.js -> react)
    s = re.sub(r'\.js$', '', s)
    s = re.sub(r'[^a-z0-9+#/ ]', '', s).strip()
    if is_no_value(s):
        return ""
    return _SKILL_SYNONYMS.get(s, s)


def _tokenize_skills(skills_input: Any) -> list[str]:
    """Split a skills string or list into individual normalized tokens, dropping no-value markers."""
    if not skills_input or is_no_value(skills_input):
        return []

    if isinstance(skills_input, (list, tuple, set)):
        raw = []
        for item in skills_input:
            if isinstance(item, str):
                if not is_no_value(item):
                    raw.extend(re.split(SKILL_SEPARATOR, repair_line_hyphenation(item)))
            elif isinstance(item, dict) and ("name" in item or "skill_name" in item):
                val = str(item.get("name") or item.get("skill_name") or "")
                if not is_no_value(val):
                    raw.extend(re.split(SKILL_SEPARATOR, repair_line_hyphenation(val)))
            elif item and not is_no_value(item):
                raw.append(str(item))
    else:
        # Split by pipe, comma, semicolon, or bullet
        raw = re.split(SKILL_SEPARATOR, repair_line_hyphenation(str(skills_input)))
    skills = []
    for s in raw:
        if is_no_value(s):
            continue
        cleaned = _normalize_skill(s)
        if cleaned and len(cleaned) > 1 and not is_no_value(cleaned):
            skills.append(cleaned)
    return skills


def _fuzzy_match(a: str, b: str, threshold: Optional[float] = None) -> bool:
    """Check if two skill strings are a fuzzy match."""
    if a == b:
        return True
    # Check if one contains the other
    if a in b or b in a:
        return True
    if threshold is None:
        try:
            cfg = get_current_matching_config()
            threshold = float(cfg.get("thresholds", {}).get("fuzzy_match_threshold", 0.75))
        except Exception:
            threshold = 0.75
    # Use SequenceMatcher for fuzzy comparison
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= threshold


# ── Experience Relevance Analysis ─────────────────────────────────────────
ROLE_FAMILY_KEYWORDS = {
    "software": ["software engineer", "software developer", "software development", "software architecture", "web developer", "developer", "programmer", "coding", "backend", "frontend", "fullstack", "full-stack", "devops", "sre", "rest api", "api", "microservices", "ci/cd", "git", "agile", "scrum", "it support", "helpdesk", "technical support", "system administration", "network administration", "deployment", "python", "javascript", "typescript", "react", "fastapi", "django", "node.js", "sql"],
    "data": ["data analyst", "data analysis", "data scientist", "data science", "data engineer", "data engineering", "data pipeline", "big data", "data visualization", "database", "machine learning", "artificial intelligence", "ai", "analytics", "business intelligence", "statistics", "statistical analysis", "etl", "deep learning", "tableau", "power bi", "powerbi"],
    "design": ["graphic designer", "ui designer", "ux designer", "designer", "ui", "ux", "graphic", "figma", "adobe", "photoshop", "illustrator", "canva", "wireframe", "prototype", "typography", "layout design", "multimedia"],
    "marketing": ["marketing", "seo", "social media", "digital marketing", "advertising", "brand", "copywriter", "copywriting", "campaign", "e-commerce", "shopify"],
    "finance": ["accountant", "accounting", "finance", "auditor", "auditing", "bookkeeper", "bookkeeping", "financial", "cpa", "banking", "investment", "tax", "budget", "budgeting", "accounts payable", "accounts receivable", "reconciliation", "sap", "quickbooks", "xero", "payroll", "billing", "invoicing", "general ledger"],
    "hr": ["human resources", "hr", "recruiter", "recruitment", "talent acquisition", "hiring", "payroll", "compensation", "onboarding", "employee relations", "hris", "training officer", "organizational development"],
    "sales": ["sales", "salesperson", "salesman", "saleswoman", "sales executive", "sales clerk", "sales officer", "account executive", "business development", "relationship manager", "account manager", "revenue", "promodiser", "merchandiser", "b2b sales"],
    "operations": ["operations manager", "operations coordinator", "logistics", "supply chain", "warehouse", "warehouseman", "warehousing", "inventory", "procurement", "purchasing", "shipping", "3pl", "forklift", "stockman", "dispatch", "freight"],
    "healthcare": ["nurse", "doctor", "medical", "healthcare", "clinical", "pharmacy", "patient", "diagnosis", "first aid", "bls", "nursing", "hospital"],
    "education": ["teacher", "instructor", "professor", "tutor", "teaching", "curriculum", "lesson plan", "academic", "lpt", "classroom"],
    "service": ["cashier", "service crew", "barista", "waiter", "waitress", "food service", "fast food", "restaurant", "retail", "customer service", "customer support", "csr", "tsr", "call center", "chat support", "email support", "counter", "crew member", "virtual assistant", "order processing", "pos"],
    "admin": ["administrative", "admin assistant", "office assistant", "executive assistant", "office clerk", "office staff", "secretary", "receptionist", "filing", "clerical", "data encoder", "data entry", "front desk"],
    "engineering": ["civil engineer", "mechanical engineer", "electrical engineer", "industrial engineer", "chemical engineer", "structural", "construction", "cad", "autocad", "blueprint", "maintenance technician", "plant maintenance", "plc", "preventive maintenance", "hvac", "troubleshooting", "welder", "welding", "electrician", "machinist"],
    "legal": ["lawyer", "attorney", "paralegal", "legal", "litigation", "corporate law", "juris doctor", "bar"],
    "manufacturing": ["factory", "assembly", "production", "manufacturing", "quality control", "quality assurance", "qc", "qa", "qa inspector", "qc inspector", "product inspection", "defect reporting", "measuring tools", "machine operator", "machine handling", "cnc", "injection molding", "kiln", "ceramic", "ceramics", "glaze", "tile", "tiles", "plant", "factory worker", "laborer", "iso 9001", "5s", "kaizen", "gmp", "lean manufacturing", "six sigma", "root cause analysis", "process optimization"],
    "science": ["chemist", "chemistry", "chemical analysis", "laboratory", "material testing", "formulation", "r&d", "research and development"],
    "ehs": ["safety officer", "ehs", "osh", "bosh", "cosh", "hazard identification", "pollution control", "denr", "environmental compliance", "safety compliance"],
}

_ROLE_FAMILY_PATTERNS: dict[str, list[re.Pattern]] = {
    family: [re.compile(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', re.IGNORECASE) for kw in keywords]
    for family, keywords in ROLE_FAMILY_KEYWORDS.items()
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

_NON_EXPERIENCE_PLACEHOLDERS = {
    "none", "n/a", "na", "nil", "not specified", "not applicable",
    "no experience", "no work experience", "none yet", "fresh graduate",
    "no prior experience", "no relevant experience", "-", "--",
}

_GENERIC_EXPERIENCE_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "into", "is", "it", "its", "of", "on", "or", "our", "that", "the", "their",
    "them", "this", "to", "was", "were", "will", "with", "you", "your",
    "ability", "abilities", "adaptable", "adaptability", "all", "any", "applicable",
    "area", "areas", "assistant", "assisted", "associate", "attention", "based",
    "candidate", "client", "clients", "collaborate", "communication", "company",
    "competencies", "coord", "coordination", "corp", "current", "customer", "customers",
    "daily", "day", "days", "deadline", "deadlines", "detail", "details", "duties",
    "duty", "ensure", "ensuring", "etc", "experience", "experienced", "fast",
    "flexible", "full", "general", "goal", "goals", "good", "group", "handled",
    "handling", "help", "helped", "high", "hours", "inc", "including", "information",
    "interpersonal", "issue", "issues", "job", "jobs", "knowledge", "lead", "leader",
    "leadership", "level", "looking", "maintain", "maintained", "manage", "managed",
    "management", "member", "members", "minimum", "month", "months", "multitask",
    "multitasking", "must", "need", "needs", "new", "none", "office", "one",
    "organization", "other", "part", "people", "perform", "performed", "person",
    "philippines", "position", "positions", "preferred", "prepare", "prepared",
    "present", "prioritize", "problem", "problems", "process", "processes",
    "professional", "quality", "related", "relevant", "report", "reports",
    "require", "required", "requirements", "responsibilities", "responsibility",
    "responsible", "role", "roles", "rule", "rules", "seeking", "service",
    "services", "shift", "shifts", "skill", "skills", "solving", "staff",
    "store", "stores", "strong", "support", "supported", "task", "tasks",
    "team", "teams", "teamwork", "time", "using", "various", "versatile",
    "way", "work", "worked", "working", "works", "year", "years", "yrs", "yr",
}

_GENERIC_SIM_TOKENS = {
    "and", "or", "the", "for", "with", "full", "senior", "junior", "intern",
    "assistant", "associate", "manager", "supervisor", "officer", "representative",
    "specialist", "executive", "lead", "public", "english", "process", "company",
    "work", "experience", "responsibilities", "duties", "role", "position",
    "team", "staff", "general", "service", "customer", "support", "communication",
    "none", "na", "wala", "nil", "null",
}


def _term_in_text(term: str, text_lower: str) -> bool:
    """Check whether a term appears in text on word/token boundaries."""
    if not term or not text_lower:
        return False
    return bool(re.search(r'(?<!\w)' + re.escape(term.lower()) + r'(?!\w)', text_lower))


def _detect_role_family(text: str, priority_text: str = "") -> str:
    if not text and not priority_text:
        return ""
    best_family, best_score = "", (0, 0)
    for family, patterns in _ROLE_FAMILY_PATTERNS.items():
        title_hits = sum(1 for pat in patterns if pat.search(priority_text)) if priority_text else 0
        total_hits = sum(1 for pat in patterns if pat.search(text)) if text else 0
        # Give title hits extra weight and use them as a deterministic tie-breaker
        score = (total_hits + title_hits * 2, title_hits)
        if (total_hits > 0 or title_hits > 0) and score > best_score:
            best_score = score
            best_family = family
    return best_family


def _detect_all_role_families(text: str) -> dict[str, int]:
    """Return a dict mapping each role family to the number of keyword hits."""
    if not text:
        return {}
    result = {}
    for family, patterns in _ROLE_FAMILY_PATTERNS.items():
        count = sum(1 for pat in patterns if pat.search(text))
        if count > 0:
            result[family] = count
    return result


def _identify_transferable_skills(experience_text: str) -> list[str]:
    if not experience_text:
        return []
    text_lower = experience_text.lower()
    return [
        name for name, indicators in TRANSFERABLE_SKILLS.items()
        if any(_term_in_text(ind, text_lower) for ind in indicators)
    ]


def _extract_grounded_embedding_tokens(embedding_engine: Any, text: str) -> list[str]:
    """
    Extract only vocabulary-grounded skill/domain tokens from text so that
    unmatched prose sentences do not fall back to the non-negative subword SVD
    and fabricate high similarity across unrelated domains.
    """
    if not text or not embedding_engine or is_no_value(text):
        return []

    token_vecs = getattr(embedding_engine, "token_vectors_", None) or {}
    found: list[str] = []
    seen: set[str] = set()

    def _add(tok: str) -> None:
        if is_no_value(tok):
            return
        norm = re.sub(r'[^a-z0-9+#/_ ]', '', tok.lower()).strip().replace(' ', '_')
        if (
            norm
            and len(norm) >= 2
            and len(norm) <= 40
            and norm not in _GENERIC_SIM_TOKENS
            and norm not in NO_VALUE_MARKERS
            and norm not in seen
        ):
            seen.add(norm)
            found.append(norm)

    try:
        embedding_engine._get_spacy()
        if getattr(embedding_engine, "_skills_matcher", None) and getattr(embedding_engine, "_nlp", None):
            doc = embedding_engine._nlp(text)
            for _, start, end in embedding_engine._skills_matcher(doc):
                _add(doc[start:end].text)
    except Exception:
        pass

    words = [w for w in re.findall(r'[a-z0-9+#/]+', text.lower()) if len(w) >= 2]
    for i, w in enumerate(words):
        if w in token_vecs:
            _add(w)
        if i + 1 < len(words):
            bigram = f"{w}_{words[i + 1]}"
            if bigram in token_vecs:
                _add(bigram)

    return found


def _compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity between two text fragments using vocabulary-grounded
    FastText embeddings or spaCy word vectors (when available).
    Returns bounded score [0.0, 1.0].
    """
    try:
        from app.ml_engine import get_production_model
        model = get_production_model()
        if model and model.embedding_engine:
            ee = model.embedding_engine
            tokens_a = _extract_grounded_embedding_tokens(ee, text_a)
            tokens_b = _extract_grounded_embedding_tokens(ee, text_b)
            if tokens_a and tokens_b:
                vec_a = ee.vectorize_tokens(tokens_a)
                vec_b = ee.vectorize_tokens(tokens_b)
                sim = ee.compute_cosine_similarity(vec_a, vec_b)
                return float(sim)
    except Exception:
        pass

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


def _extract_domain_keywords(text: str) -> set[str]:
    """
    Extract meaningful domain/technical terms and multi-word skill phrases from
    a job description or work experience entry, filtering out stopwords, years,
    generic resume boilerplate, no-value markers, and soft/transferable skills.
    """
    if not text or is_no_value(text):
        return set()

    keywords: set[str] = set()

    # 1. Include phrase-matched technical skills if the NLP skills matcher is available
    try:
        from app.ml_engine import get_production_model
        model = get_production_model()
        if model and model.embedding_engine:
            ee = model.embedding_engine
            ee._get_spacy()
            if getattr(ee, "_skills_matcher", None) and getattr(ee, "_nlp", None):
                doc = ee._nlp(text)
                for _, start, end in ee._skills_matcher(doc):
                    norm = _normalize_skill(doc[start:end].text)
                    if norm and len(norm) > 1 and norm not in _GENERIC_EXPERIENCE_WORDS and norm not in NO_VALUE_MARKERS:
                        keywords.add(norm)
    except Exception:
        pass

    # 2. Include short comma/pipe/semicolon-delimited skill phrases
    for chunk in re.split(r'[|,;•]', text):
        if is_no_value(chunk):
            continue
        cleaned = _normalize_skill(chunk)
        words = cleaned.split()
        if 1 <= len(words) <= 3 and len(cleaned) >= 2:
            if not all(w in _GENERIC_EXPERIENCE_WORDS or w in NO_VALUE_MARKERS or w.isdigit() for w in words):
                if cleaned not in _GENERIC_EXPERIENCE_WORDS and cleaned not in NO_VALUE_MARKERS and not cleaned.isdigit():
                    keywords.add(cleaned)

    # 3. Include meaningful individual content words (excluding years/stopwords/boilerplate)
    for tok in re.findall(r'[a-z0-9+#/]{2,}', text.lower()):
        norm = _SKILL_SYNONYMS.get(tok, tok)
        if (
            len(norm) >= 3
            and not norm.isdigit()
            and norm not in _GENERIC_EXPERIENCE_WORDS
            and norm not in NO_VALUE_MARKERS
        ):
            keywords.add(norm)

    return keywords


def _count_job_keyword_hits(entry_text: str, job_keywords: set[str]) -> tuple[int, list[str]]:
    """
    Count how many job-requirement keywords appear in an experience entry
    using word-boundary matching (never partial substring matches).
    Returns (count, list_of_matched_keywords).
    """
    entry_lower = entry_text.lower()
    matched = [kw for kw in job_keywords if len(kw) > 2 and _term_in_text(kw, entry_lower)]
    return len(matched), matched


def _validate_verb_objects_against_job(verbs_objs: list[tuple[str, str]], job_text_lower: str) -> list[tuple[str, str]]:
    """
    Filter verb-object pairs to only those whose meaningful domain object terms
    appear in the job description/requirements on word boundaries.
    """
    relevant = []
    for verb, obj in verbs_objs:
        obj_tokens = [
            t.strip().lower()
            for t in re.findall(r'[a-z0-9+#/]+', obj.lower())
            if len(t.strip()) > 2 and t.strip().lower() not in _GENERIC_EXPERIENCE_WORDS and not t.strip().isdigit()
        ]
        if any(_term_in_text(tok, job_text_lower) for tok in obj_tokens):
            relevant.append((verb, obj))
    return relevant


def calculate_experience_relevance(resume_experience: str, resume_skills: str, job_title: str, job_description: str, transferable_cap: Optional[int] = None) -> dict:
    """
    Evaluate how RELEVANT the candidate's work experience is to the target job.

    STRICT SCORING POLICY:
    ─────────────────────
    • Irrelevant experience contributes ZERO to the experience score.
    • Transferable soft skills alone (without direct domain/technical alignment)
      do NOT qualify an entry as relevant or directly relevant.
    • Only relevant entries count toward the denominator/maximum score.
    • Semantic similarity (grounded domain embeddings) gates borderline decisions.
    • Each entry receives a transparent explanation of why it was scored.
    """
    if transferable_cap is None:
        try:
            cfg = get_current_matching_config()
            transferable_cap = int(cfg.get("thresholds", {}).get("transferable_skills_cap", 2))
        except Exception:
            transferable_cap = 2

    try:
        from app.extractors.nlp.nlp_engine import get_doc, get_verb_object_pairs
        nlp_available = True
    except ImportError:
        nlp_available = False

    job_text = (job_title or "") + " " + (job_description or "")
    job_text_lower = job_text.lower()
    target_family = _detect_role_family(job_text, priority_text=job_title or "")
    target_families = _detect_all_role_families(job_text)
    job_kw = _extract_domain_keywords(job_text)

    raw_entries = [e.strip() for e in (resume_experience or "").split("|") if e.strip()]
    exp_entries = [
        e for e in raw_entries
        if not is_no_value(e)
        and re.sub(r'[^a-z0-9/\- ]', '', e.lower()).strip() not in _NON_EXPERIENCE_PLACEHOLDERS
    ]
    if not exp_entries:
        return {
            "relevance_level": "Irrelevant",
            "relevance_score": 0.0,
            "transferable_skills": [],
            "reason": "No work experience provided to evaluate relevance.",
            "detailed_breakdown": "No work experience provided.",
            "relevant_count": 0,
            "highly_relevant_count": 0,
            "partially_relevant_count": 0,
            "irrelevant_count": 0,
            "total_entries": 0,
            "entry_relevances": [],
        }

    relevant_scores = []     # Scores from Highly Relevant / Partially Relevant entries only
    all_transferable = set()
    breakdown_texts = []
    entry_relevances = []
    relevant_count = 0
    highly_relevant_count = 0
    partially_relevant_count = 0
    irrelevant_count = 0

    for i, entry in enumerate(exp_entries):
        candidate_family = _detect_role_family(entry)
        candidate_families = _detect_all_role_families(entry)
        entry_kw = _extract_domain_keywords(entry)
        direct_overlap = job_kw & entry_kw
        transferable = _identify_transferable_skills(entry)
        all_transferable.update(transferable)

        # Semantic similarity between the experience entry and the job description
        semantic_sim = _compute_semantic_similarity(entry, job_text) if nlp_available else 0.0

        # Job keyword hits inside the entry (word-boundary matched)
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
        family_match = bool(target_family and candidate_family and target_family == candidate_family)
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

        elif secondary_family_overlap and (
            len(direct_overlap) >= 2
            or len(relevant_verbs_objs) >= 1
            or (semantic_sim >= 0.55 and kw_hit_count >= 2)
        ):
            # ── Partially Relevant: related domain with concrete evidence ──
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

        elif transferable and len(direct_overlap) >= 1 and transferable_cap > 0:
            # ── Minimally Relevant: transferable skills backed by at least 1 direct term overlap ──
            relevance = "Partially Relevant"
            score_contrib = min(transferable_cap, len(transferable))
            reasons.append(
                f"⚠️ Limited relevance. Transferable skills detected with minimal overlap "
                f"({', '.join(list(direct_overlap)[:2])}). Score capped at {transferable_cap}/10."
            )

        else:
            # ── Irrelevant: no meaningful domain or technical signal ──
            relevance = "Irrelevant"
            score_contrib = 0  # STRICT: zero contribution
            if candidate_family:
                reasons.append(
                    f"❌ Experience is in the '{candidate_family.title()}' domain, "
                    f"which is not related to the target '{target_family.title() if target_family else 'Unknown'}' domain."
                )
            else:
                reasons.append("❌ No recognizable professional domain alignment detected in this entry.")
            reasons.append(
                "❌ No technical tools, relevant technologies, or domain-specific "
                "responsibilities were found that align with the target position."
            )
            if transferable:
                reasons.append(
                    f"ℹ️ Transferable skills noted ({', '.join(transferable)}), but they are "
                    f"insufficient on their own to qualify as relevant experience for this role."
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
        if relevance == "Highly Relevant":
            relevant_scores.append(score_contrib)
            relevant_count += 1
            highly_relevant_count += 1
        elif relevance == "Partially Relevant":
            relevant_scores.append(score_contrib)
            relevant_count += 1
            partially_relevant_count += 1
        else:
            irrelevant_count += 1

        entry_relevances.append({
            "index": i,
            "entry": entry,
            "relevance": relevance,
        })

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
        "highly_relevant_count": highly_relevant_count,
        "partially_relevant_count": partially_relevant_count,
        "irrelevant_count": irrelevant_count,
        "total_entries": len(exp_entries),
        "entry_relevances": entry_relevances,
    }


def _find_education_context(text: str) -> str:
    """Extract sentences from job description that likely contain education requirements."""
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    ed_sentences = []
    level_pattern = (
        r'\b(bachelor|master|doctorate|ph\.?d|degree|university|college|graduated|'
        r'senior\s+high|junior\s+high|high\s+school|shs|jhs|tesda|vocational|associate|elementary|k-?12)\b'
    )
    for s in sentences:
        if re.search(level_pattern, s, re.IGNORECASE):
            ed_sentences.append(s)
    return " ".join(ed_sentences)


def _extract_core_subject(text: str) -> str:
    """Extract the core field of study by removing generic degree terms, school names, and qualifiers."""
    from app.services.requirement_rules import extract_education_fields
    return " ".join(extract_education_fields(text))


def _resolve_education_text(resume_data: dict) -> str:
    """Resolve candidate education string from resume/application fields, skipping no-value markers."""
    if not isinstance(resume_data, dict):
        return ""
    candidates: list[str] = []
    seen: set[str] = set()
    for key in ("education", "degree", "highest_degree"):
        val = normalize_requirement_text(resume_data.get(key))
        if val and val.lower() not in seen:
            seen.add(val.lower())
            candidates.append(val)
    if candidates:
        return " | ".join(candidates)
    fallback = normalize_requirement_text(resume_data.get("highest_educational_attainment"))
    return fallback or ""


_UMBRELLA_GENERIC_FIELD_WORDS: frozenset[str] = frozenset({
    "science", "arts", "applied", "general", "studies", "course", "program",
})


def _evaluate_education_field_alignment(req_fields: list[str], cand_fields: list[str]) -> tuple[str, str, str]:
    """
    Compare candidate's fields against job's required field options.
    Returns (match_type, matched_req_field, matched_cand_field) where match_type is
    one of 'exact', 'related', 'partial', 'unspecified', or 'mismatch'.
    """
    if not cand_fields:
        return "unspecified", req_fields[0], ""

    # 1. Exact / canonical synonym match, including broad umbrella requirements
    #    (e.g. "engineering" <= "civil engineering", "supply chain" <= "supply chain management")
    for rf in req_fields:
        rf_canon = EDUCATION_FIELD_SYNONYMS.get(rf, rf)
        rf_tokens = set(rf_canon.split())
        rf_specific = rf_tokens - _UMBRELLA_GENERIC_FIELD_WORDS
        for cf in cand_fields:
            cf_canon = EDUCATION_FIELD_SYNONYMS.get(cf, cf)
            cf_tokens = set(cf_canon.split())
            if rf_canon == cf_canon or (rf_tokens and rf_tokens == cf_tokens):
                return "exact", rf, cf
            if rf_specific and rf_tokens and rf_tokens <= cf_tokens:
                return "exact", rf, cf

    # 2. Related major table (checked symmetrically)
    for rf in req_fields:
        rf_canon = EDUCATION_FIELD_SYNONYMS.get(rf, rf)
        rf_words = set(rf_canon.split())
        for cf in cand_fields:
            cf_canon = EDUCATION_FIELD_SYNONYMS.get(cf, cf)
            cf_words = set(cf_canon.split())
            for table_key, rel_list in RELATED_EDUCATION_FIELDS.items():
                tk_words = set(table_key.split())
                if tk_words <= rf_words:
                    if any(set(rel.split()) <= cf_words for rel in rel_list):
                        return "related", rf, cf
                if tk_words <= cf_words:
                    if any(set(rel.split()) <= rf_words for rel in rel_list):
                        return "related", rf, cf

    # 3. Partial token overlap on meaningful field words
    generic = {"science", "arts", "applied", "general", "course", "program", "studies", "technology", "management"}
    for rf in req_fields:
        rf_core = set(rf.split()) - generic
        if not rf_core:
            rf_core = set(rf.split())
        for cf in cand_fields:
            cf_core = set(cf.split()) - generic
            if not cf_core:
                cf_core = set(cf.split())
            if rf_core & cf_core:
                return "partial", rf, cf

    return "mismatch", req_fields[0], cand_fields[0]


def calculate_education_match(
    resume_education: str,
    job_description: str,
    education_req: str = None,
    education_entries: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """
    Compare candidate's education against job requirements using the shared
    1-8 Philippine education hierarchy, ongoing/undergraduate completion rules,
    no-value normalization, and separate field-of-study verification.
    """
    cand_parsed = parse_education_level(
        resume_education,
        is_job_requirement=False,
        entries=education_entries,
    )

    if education_req is not None:
        if is_no_value(education_req):
            from app.services.requirement_rules import education_display_label
            cand_label = education_display_label(resume_education, education_entries) or "None provided"
            return {
                "score": 1.0,
                "status": STATUS_NOT_REQUIRED,
                "has_requirement": False,
                "needs_manual_review": False,
                "required_education": "Not required",
                "candidate_education": cand_label,
                "reason": format_criterion_reason(
                    STATUS_NOT_REQUIRED,
                    "No education requirement for this position.",
                ),
            }
        req_text = str(education_req).strip()
    else:
        req_text = _find_education_context(job_description)
        if is_no_value(req_text):
            from app.services.requirement_rules import education_display_label
            cand_label = education_display_label(resume_education, education_entries) or "None provided"
            return {
                "score": 1.0,
                "status": STATUS_NOT_REQUIRED,
                "has_requirement": False,
                "needs_manual_review": False,
                "required_education": "Not required",
                "candidate_education": cand_label,
                "reason": format_criterion_reason(
                    STATUS_NOT_REQUIRED,
                    "No education requirement for this position.",
                ),
            }

    req_parsed = parse_education_level(req_text, is_job_requirement=True)

    if not req_parsed["recognized"] or req_parsed["level"] is None:
        logger.warning("Unrecognized job education requirement text (manual review): %r", req_text)
        cand_disp = cand_parsed["label"] or normalize_requirement_text(resume_education) or "None provided"
        return {
            "score": EDUCATION_MANUAL_REVIEW_SCORE,
            "status": STATUS_MANUAL_REVIEW,
            "has_requirement": True,
            "needs_manual_review": True,
            "required_education": req_text,
            "candidate_education": cand_disp,
            "reason": format_criterion_reason(
                STATUS_MANUAL_REVIEW,
                f"Job education requirement ('{req_text}') could not be automatically parsed; HR review recommended.",
            ),
        }

    req_level = int(req_parsed["level"])
    req_label = EDUCATION_SHORT_LABELS[req_level]
    req_fields = list(req_parsed["field_options"] or [])
    req_display = f"{req_label} in {' or '.join(req_fields)}" if req_fields else req_label

    if cand_parsed["is_no_value"]:
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "has_requirement": True,
            "needs_manual_review": False,
            "required_education": req_display,
            "candidate_education": "None provided",
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"Requires {req_display}; no education details were provided on the resume.",
            ),
        }

    if not cand_parsed["recognized"] or cand_parsed["level"] is None:
        logger.warning("Unrecognized candidate education text (manual review): %r", resume_education)
        raw_cand_disp = normalize_requirement_text(resume_education) or "Unrecognized"
        return {
            "score": EDUCATION_MANUAL_REVIEW_SCORE,
            "status": STATUS_MANUAL_REVIEW,
            "has_requirement": True,
            "needs_manual_review": True,
            "required_education": req_display,
            "candidate_education": raw_cand_disp,
            "reason": format_criterion_reason(
                STATUS_MANUAL_REVIEW,
                f"Candidate education ('{raw_cand_disp}') could not be automatically verified against required {req_display}. HR manual review recommended.",
            ),
        }

    cand_level = int(cand_parsed["level"])
    cand_label = EDUCATION_SHORT_LABELS[cand_level]
    is_ongoing = bool(cand_parsed["is_ongoing"])
    pursuing_level = cand_parsed.get("pursuing_level") or cand_level

    # Gather fields from entries that actually meet/exceed req_level (or all cand fields if below)
    if cand_level >= req_level:
        qualifying_fields: list[str] = []
        seen_qf: set[str] = set()
        for entry in cand_parsed.get("parsed_entries") or []:
            if (entry.get("level") or 0) >= req_level:
                for f in entry.get("field_options") or []:
                    if f not in seen_qf:
                        seen_qf.add(f)
                        qualifying_fields.append(f)
        cand_fields = qualifying_fields or list(cand_parsed["field_options"] or [])
    else:
        cand_fields = list(cand_parsed["field_options"] or [])

    from app.services.requirement_rules import education_display_label
    cand_display = education_display_label(resume_education, education_entries)

    # Case 1: Job does NOT require a specific field/course
    if not req_fields:
        if cand_level > req_level:
            return {
                "score": 1.0,
                "status": STATUS_EXCEEDS,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_EXCEEDS,
                    f"Candidate has {cand_display}, exceeding the required {req_label}.",
                ),
            }
        if cand_level == req_level:
            return {
                "score": 1.0,
                "status": STATUS_MEETS,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_MEETS,
                    f"Candidate has {cand_display}, meeting the required {req_label}.",
                ),
            }

        # cand_level < req_level
        proportional_score = compute_education_partial_score(cand_level, req_level)
        if is_ongoing and pursuing_level >= req_level:
            return {
                "score": proportional_score,
                "status": STATUS_PARTIAL,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_PARTIAL,
                    f"Requires {req_label}; candidate is currently an undergraduate/enrolled (highest completed level: {cand_label}).",
                ),
            }
        return {
            "score": proportional_score,
            "status": STATUS_DOES_NOT_MEET,
            "has_requirement": True,
            "needs_manual_review": False,
            "required_education": req_display,
            "candidate_education": cand_display,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"Requires {req_label}; candidate has {cand_label}.",
            ),
        }

    # Case 2: Job explicitly requires a specific course / field of study
    field_match, matched_req_field, matched_cand_field = _evaluate_education_field_alignment(
        req_fields, cand_fields
    )
    req_field_str = " or ".join(req_fields)

    if cand_level >= req_level:
        if field_match == "exact":
            status = STATUS_EXCEEDS if cand_level > req_level else STATUS_MEETS
            detail = (
                f"Candidate has {cand_label} in {matched_cand_field}, exceeding the required {req_label} in {matched_req_field}."
                if cand_level > req_level
                else f"Candidate has {cand_label} in {matched_cand_field}, meeting the required {req_label} in {matched_req_field}."
            )
            return {
                "score": 1.0,
                "status": status,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(status, detail),
            }

        lvl_prefix = (
            f"Exceeds {req_label} level with {cand_label}"
            if cand_level > req_level
            else f"Meets {req_label} level"
        )
        if field_match == "related":
            return {
                "score": EDUCATION_RELATED_FIELD_SCORE,
                "status": STATUS_PARTIAL,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_PARTIAL,
                    f"{lvl_prefix} with a related field ({matched_cand_field}; requires {req_field_str}).",
                ),
            }
        if field_match == "partial":
            return {
                "score": EDUCATION_PARTIAL_FIELD_SCORE,
                "status": STATUS_PARTIAL,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_PARTIAL,
                    f"{lvl_prefix} with partial field alignment ({matched_cand_field}; requires {req_field_str}).",
                ),
            }
        if field_match == "unspecified":
            return {
                "score": EDUCATION_LEVEL_MET_UNSPECIFIED_FIELD_SCORE,
                "status": STATUS_PARTIAL,
                "has_requirement": True,
                "needs_manual_review": False,
                "required_education": req_display,
                "candidate_education": cand_display,
                "reason": format_criterion_reason(
                    STATUS_PARTIAL,
                    f"{lvl_prefix}, but specific field of study ({req_field_str}) was not listed on the resume.",
                ),
            }

        # Being overqualified in level never fixes a wrong field
        return {
            "score": EDUCATION_LEVEL_MET_WRONG_FIELD_SCORE,
            "status": STATUS_PARTIAL,
            "has_requirement": True,
            "needs_manual_review": False,
            "required_education": req_display,
            "candidate_education": cand_display,
            "reason": format_criterion_reason(
                STATUS_PARTIAL,
                f"{lvl_prefix}, but field of study does not match (Requires {req_field_str}; candidate has {matched_cand_field}).",
            ),
        }

    # cand_level < req_level with specific required field
    level_ratio = compute_education_partial_score(cand_level, req_level)
    field_factor = 0.85 if field_match in ("exact", "related", "partial") else 0.40
    partial_score = round(level_ratio * field_factor, 2)

    if is_ongoing and pursuing_level >= req_level:
        return {
            "score": partial_score,
            "status": STATUS_PARTIAL,
            "has_requirement": True,
            "needs_manual_review": False,
            "required_education": req_display,
            "candidate_education": cand_display,
            "reason": format_criterion_reason(
                STATUS_PARTIAL,
                f"Requires {req_display}; candidate is currently an undergraduate/enrolled (highest completed level: {cand_label}).",
            ),
        }

    return {
        "score": partial_score,
        "status": STATUS_DOES_NOT_MEET,
        "has_requirement": True,
        "needs_manual_review": False,
        "required_education": req_display,
        "candidate_education": cand_display,
        "reason": format_criterion_reason(
            STATUS_DOES_NOT_MEET,
            f"Requires {req_display}; candidate has {cand_display}.",
        ),
    }


def calculate_skills_match(resume_skills: str, job_skills: str, fuzzy_threshold: Optional[float] = None) -> dict:
    """
    Compare resume skills against job requirements.
    Skills are non-hierarchical (match / no-match).
    """
    if is_no_value(job_skills):
        return {
            "score": 1.0,
            "status": STATUS_NOT_REQUIRED,
            "has_requirement": False,
            "matched": [],
            "missing": [],
            "reason": format_criterion_reason(
                STATUS_NOT_REQUIRED,
                "No specific skills requirement for this position.",
            ),
        }

    resume_tokens = _tokenize_skills(resume_skills)
    job_tokens = _tokenize_skills(job_skills)

    if not job_tokens:
        return {
            "score": 1.0,
            "status": STATUS_NOT_REQUIRED,
            "has_requirement": False,
            "matched": [],
            "missing": [],
            "reason": format_criterion_reason(
                STATUS_NOT_REQUIRED,
                "No specific skills requirement for this position.",
            ),
        }

    if not resume_tokens:
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "has_requirement": True,
            "matched": [],
            "missing": job_tokens,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"No matching skills found on resume (required: {', '.join(job_tokens[:6])}).",
            ),
        }

    matched = []
    missing = []

    for job_skill in job_tokens:
        found = False
        for resume_skill in resume_tokens:
            if _fuzzy_match(resume_skill, job_skill, threshold=fuzzy_threshold):
                matched.append(job_skill)
                found = True
                break
        if not found:
            missing.append(job_skill)

    score = len(matched) / len(job_tokens) if job_tokens else 0.0
    if len(matched) == len(job_tokens):
        status = STATUS_MEETS
        detail = f"Matched all {len(matched)} required skill(s): {', '.join(matched[:6])}."
    elif matched:
        status = STATUS_PARTIAL
        detail = (
            f"Matched {len(matched)} of {len(job_tokens)} required skills "
            f"({', '.join(matched[:5])}); missing {', '.join(missing[:5])}."
        )
    else:
        status = STATUS_DOES_NOT_MEET
        detail = f"None of the required skills matched ({', '.join(missing[:6])})."

    return {
        "score": score,
        "status": status,
        "has_requirement": True,
        "matched": matched,
        "missing": missing,
        "reason": format_criterion_reason(status, detail),
    }


def _extract_years_from_text(text: Any, explicit_req: bool = False) -> int:
    """Extract minimum required years of experience from a job requirement or description."""
    if text is None:
        return 0
    if isinstance(text, (int, float)):
        val = int(text)
        return val if 0 < val <= 50 else 0
    if is_no_value(text):
        return 0

    raw = str(text).strip()
    if not raw:
        return 0
    if explicit_req and re.fullmatch(r'\d+', raw):
        val = int(raw)
        return val if 0 < val <= 50 else 0

    max_years = 0
    # Parse ranges like "3-5 years" or "2 to 4 yrs" by taking the minimum bound ("3", "2")
    range_pattern = r'\b(\d+)\s*(?:-|–|—|to)\s*\d+\s*\+?\s*(?:years?|yrs?)\b'
    cleaned = raw
    for m in re.finditer(range_pattern, raw, re.IGNORECASE):
        try:
            val = int(m.group(1))
            if 0 < val <= 50:
                max_years = max(max_years, val)
        except ValueError:
            continue
    cleaned = re.sub(range_pattern, ' ', cleaned, flags=re.IGNORECASE)

    patterns = [
        r'(?:minimum|at least|min)\s*(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp|relevant|professional|work|in\s+)',
    ]
    if explicit_req:
        patterns.append(r'\b(\d+)\s*\+?\s*(?:years?|yrs?)\b')

    for pattern in patterns:
        for m in re.findall(pattern, cleaned, re.IGNORECASE):
            try:
                val = int(m)
                if 0 < val <= 50:
                    max_years = max(max_years, val)
            except ValueError:
                continue

    return max_years


def calculate_experience_match(resume_years: int, job_description: str, experience_req: str = None) -> dict:
    """
    Compare resume years of experience against job requirements using >= hierarchy.
    More experience never penalizes a candidate; 'None'/empty requirement earns full credit.
    """
    explicit_non_empty_no_value = (
        experience_req is not None
        and is_no_value(experience_req)
    )
    has_non_no_value_explicit_text = (
        experience_req is not None and not is_no_value(experience_req)
    )

    if explicit_non_empty_no_value:
        required_years = 0
    else:
        required_years = _extract_years_from_text(experience_req, explicit_req=True) if experience_req else 0
        if required_years == 0:
            required_years = _extract_years_from_text(job_description, explicit_req=False)

    resume_years = resume_years or 0

    def _yr_label(val: int | float) -> str:
        num = int(val) if float(val).is_integer() else val
        return f"{num} yr{'s' if num != 1 else ''}"

    if required_years == 0:
        if has_non_no_value_explicit_text and not explicit_non_empty_no_value:
            detail = (
                f"No minimum years specified in requirement (candidate has {_yr_label(resume_years)})."
                if resume_years > 0
                else "No minimum years specified in experience requirement."
            )
            return {
                "score": 1.0 if resume_years > 0 else 0.5,
                "status": STATUS_MEETS if resume_years > 0 else STATUS_PARTIAL,
                "has_requirement": True,
                "has_years_requirement": False,
                "required_years": 0,
                "candidate_years": resume_years,
                "below_minimum": False,
                "gap_years": 0,
                "reason": format_criterion_reason(
                    STATUS_MEETS if resume_years > 0 else STATUS_PARTIAL,
                    detail,
                ),
            }

        detail = (
            f"No experience requirement for this position (candidate has {_yr_label(resume_years)})."
            if resume_years > 0
            else "No experience requirement for this position."
        )
        return {
            "score": 1.0,
            "status": STATUS_NOT_REQUIRED,
            "has_requirement": False,
            "has_years_requirement": False,
            "required_years": 0,
            "candidate_years": resume_years,
            "below_minimum": False,
            "gap_years": 0,
            "reason": format_criterion_reason(STATUS_NOT_REQUIRED, detail),
        }

    if resume_years <= 0:
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "has_requirement": True,
            "has_years_requirement": True,
            "required_years": required_years,
            "candidate_years": 0,
            "below_minimum": True,
            "gap_years": required_years,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"Gap reported: experience below minimum — required {_yr_label(required_years)}, "
                f"but no experience duration was extracted from resume.",
            ),
        }

    if resume_years > required_years:
        return {
            "score": 1.0,
            "status": STATUS_EXCEEDS,
            "has_requirement": True,
            "has_years_requirement": True,
            "required_years": required_years,
            "candidate_years": resume_years,
            "below_minimum": False,
            "gap_years": 0,
            "reason": format_criterion_reason(
                STATUS_EXCEEDS,
                f"Candidate has {_yr_label(resume_years)} of experience (exceeds required {_yr_label(required_years)}).",
            ),
        }

    if resume_years == required_years:
        return {
            "score": 1.0,
            "status": STATUS_MEETS,
            "has_requirement": True,
            "has_years_requirement": True,
            "required_years": required_years,
            "candidate_years": resume_years,
            "below_minimum": False,
            "gap_years": 0,
            "reason": format_criterion_reason(
                STATUS_MEETS,
                f"Candidate has {_yr_label(resume_years)} of experience, meeting the {_yr_label(required_years)} requirement.",
            ),
        }

    score = round(resume_years / required_years, 2)
    gap_years = max(0, required_years - resume_years)
    status = STATUS_PARTIAL if score >= 0.4 else STATUS_DOES_NOT_MEET
    return {
        "score": score,
        "status": status,
        "has_requirement": True,
        "has_years_requirement": True,
        "required_years": required_years,
        "candidate_years": resume_years,
        "below_minimum": True,
        "gap_years": gap_years,
        "reason": format_criterion_reason(
            status,
            f"Gap reported: experience below minimum — {_yr_label(resume_years)} vs "
            f"{_yr_label(required_years)} required ({int(score * 100)}% of minimum; {_yr_label(gap_years)} short).",
        ),
    }


_LEVEL_TO_LEGACY_LABEL = {
    8: "DOCTORATE",
    7: "MASTER",
    6: "BACHELOR",
    5: "ASSOCIATE",
    4: "DIPLOMA/VOCATIONAL",
    3: "SENIOR HIGH SCHOOL",
    2: "HIGH SCHOOL",
    1: "ELEMENTARY",
}


def _extract_education_requirement(text: str) -> str:
    """Extract the education level required from text using the shared hierarchy."""
    parsed = parse_education_level(text, is_job_requirement=True)
    if parsed.get("is_no_value") or not parsed.get("recognized") or not parsed.get("level"):
        return ""
    return _LEVEL_TO_LEGACY_LABEL.get(parsed["level"], "")


_NO_CERT_REQUIREMENTS = {
    "",
    "none",
    "none required",
    "no",
    "no certification",
    "no certifications",
    "no certification required",
    "no certifications required",
    "no specific certification",
    "no specific certifications",
    "no specific certification required",
    "no specific certifications required",
    "n/a",
    "na",
    "nil",
    "not required",
    "not applicable",
    "not specified",
    "optional",
    "-",
    "--",
}

_GENERIC_CERT_REQ_PHRASES = {
    "relevant certification",
    "relevant certifications",
    "any relevant certification",
    "any relevant certifications",
    "certification",
    "certifications",
    "certified",
    "certificate",
    "certificates",
}

_GENERIC_CERT_WORDS = {
    "certification", "certifications", "certified", "certificate", "certificates",
    "credential", "credentials", "license", "licensed", "licenses", "licensure",
    "eligibility", "eligible", "training", "trainings", "seminar", "seminars",
    "workshop", "workshops", "bootcamp", "bootcamps", "course", "courses",
    "program", "programs", "completion", "participation", "attendance",
    "achievement", "excellence", "appreciation", "recognition", "merit",
    "relevant", "required", "preferred", "plus", "advantage", "must", "have",
    "holder", "passer", "registered", "professional", "national", "level",
    "in", "of", "for", "and", "or", "the", "a", "an", "with", "to", "on", "at",
    "none", "na", "wala", "nil", "null",
}

_AMBIGUOUS_SINGLE_CERT_TOKENS = {
    "safety", "management", "operations", "control", "systems", "design",
    "analysis", "support", "planning", "testing", "maintenance", "quality",
    "service", "services", "security", "development", "engineering", "health",
    "business", "technical", "digital", "data", "project", "office",
}

_CERT_ABBREVIATIONS = {
    "cpa": "certified public accountant",
    "chrp": "certified human resource professional",
    "pmp": "project management professional",
    "cka": "certified kubernetes administrator",
    "bosh": "basic occupational safety and health",
    "cosh": "construction occupational safety and health",
    "bls": "basic life support",
    "lpt": "licensed professional teacher",
    "rce": "registered civil engineer",
    "ree": "registered electrical engineer",
    "rme": "registered mechanical engineer",
    "rche": "registered chemical engineer",
    "cse": "civil service eligibility",
}


def _is_no_cert_requirement(text: Any) -> bool:
    """Return True when a certification requirement string represents 'none' / not required."""
    if is_no_value(text):
        return True
    norm = re.sub(r'[.\s]+$', '', str(text).strip().lower())
    return norm in _NO_CERT_REQUIREMENTS


def _normalize_cert_text(text: str) -> str:
    """Normalize a certification name for boundary-safe comparison."""
    if not text:
        return ""
    s = re.sub(r'[-_/]+', ' ', str(text).lower().strip())
    s = re.sub(r'[^a-z0-9+#.\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _normalize_certifications_input(certs_input: Any) -> list[str]:
    """Normalize a certifications string/list into clean individual certification names."""
    if not certs_input:
        return []

    raw_items: list[str] = []
    if isinstance(certs_input, (list, tuple, set)):
        for item in certs_input:
            if isinstance(item, dict):
                val = item.get("canonical_name") or item.get("name") or ""
                if val:
                    raw_items.extend(clean_list_items(val))
            elif item:
                raw_items.extend(clean_list_items(item))
    else:
        raw_items = clean_list_items(certs_input)

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        label = re.sub(r'\s+', ' ', str(item)).strip()
        if not label or is_no_value(label):
            continue
        low = re.sub(r'[.\s]+$', '', label.lower())
        if low in _NO_CERT_REQUIREMENTS or low in {"unknown", "none specified"}:
            continue
        if low not in seen:
            seen.add(low)
            cleaned.append(label)
    return cleaned


def _extract_cert_alternatives(req_cert: str) -> list[str]:
    """Expand 'A or B' / '(A or B)' requirement clauses into individual alternatives."""
    raw = str(req_cert or "").strip()
    if not raw:
        return []

    paren_match = re.search(r'\(([^)]+)\)', raw)
    if paren_match:
        inner = paren_match.group(1)
        if re.search(r'\b(?:or)\b|/', inner, re.IGNORECASE):
            opts = [p.strip() for p in re.split(r'\s+(?:or)\s+|/', inner, flags=re.IGNORECASE) if p.strip()]
            if opts:
                return opts

    if re.search(r'\s+(?:or)\s+|/', raw, re.IGNORECASE):
        opts = [p.strip() for p in re.split(r'\s+(?:or)\s+|/', raw, flags=re.IGNORECASE) if p.strip()]
        if len(opts) > 1:
            return opts

    return [raw]


def _cert_core_tokens(norm_text: str) -> list[str]:
    """Extract meaningful domain/identifier tokens from a normalized certification string."""
    tokens = re.findall(r'[a-z0-9+#]+', norm_text.lower())
    return [t for t in tokens if (len(t) >= 2 or t.isdigit()) and t not in _GENERIC_CERT_WORDS]


def _cert_item_matches(cand_cert: str, req_cert: str, fuzzy_threshold: Optional[float] = None) -> bool:
    """Strictly determine whether a candidate certification satisfies a required certification item."""
    cand_norm = _normalize_cert_text(cand_cert)
    if not cand_norm:
        return False

    if fuzzy_threshold is None:
        try:
            cfg = get_current_matching_config()
            fuzzy_threshold = float(cfg.get("thresholds", {}).get("fuzzy_match_threshold", 0.75))
        except Exception:
            fuzzy_threshold = 0.75

    cand_core_tokens = _cert_core_tokens(cand_norm)
    cand_core_str = " ".join(cand_core_tokens)
    cand_variants = [cand_norm]
    if cand_norm in _CERT_ABBREVIATIONS:
        cand_variants.append(_CERT_ABBREVIATIONS[cand_norm])
    for tok in cand_core_tokens:
        if tok in _CERT_ABBREVIATIONS:
            cand_variants.append(_CERT_ABBREVIATIONS[tok])

    for alt in _extract_cert_alternatives(req_cert):
        alt_norm = _normalize_cert_text(alt)
        if not alt_norm:
            continue

        alt_variants = [alt_norm]
        if alt_norm in _CERT_ABBREVIATIONS:
            alt_variants.append(_CERT_ABBREVIATIONS[alt_norm])

        for av in alt_variants:
            for cv in cand_variants:
                if av == cv:
                    return True

        alt_core = _cert_core_tokens(alt_norm)
        if not alt_core:
            continue

        # All meaningful tokens (or their known expansion) must appear on word boundaries
        if all(
            any(_term_in_text(tok, cv) for cv in cand_variants)
            or (tok in _CERT_ABBREVIATIONS and any(_term_in_text(_CERT_ABBREVIATIONS[tok], cv) for cv in cand_variants))
            for tok in alt_core
        ):
            return True

        # Fuzzy match only on stripped core strings of sufficient length to avoid short-acronym false positives
        alt_core_str = " ".join(alt_core)
        if len(alt_core_str) >= 5 and len(cand_core_str) >= 5:
            if SequenceMatcher(None, cand_core_str, alt_core_str).ratio() >= fuzzy_threshold:
                return True

    return False


def _filter_relevant_certifications(cand_certs: list[str], job_title: str, job_description: str) -> list[str]:
    """Return only candidate certifications that have genuine domain/role relevance to the target job."""
    if not cand_certs:
        return []

    job_text = f"{job_title or ''} {job_description or ''}".strip()
    if not job_text:
        return []

    job_families = set(_detect_all_role_families(job_text).keys())
    job_kw = _extract_domain_keywords(job_text) - _GENERIC_CERT_WORDS

    relevant: list[str] = []
    for cert in cand_certs:
        cert_norm = _normalize_cert_text(cert)
        core_tokens = _cert_core_tokens(cert_norm)
        core_text = " ".join(core_tokens)
        if not core_text:
            continue

        # Expand known certification abbreviations for family/keyword matching
        expanded_parts = [cert, core_text]
        for tok in core_tokens:
            if tok in _CERT_ABBREVIATIONS:
                expanded_parts.append(_CERT_ABBREVIATIONS[tok])
        cert_eval_text = " ".join(expanded_parts)

        cert_families = set(_detect_all_role_families(cert_eval_text).keys())
        family_overlap = bool(cert_families & job_families)

        cert_kw = (_extract_domain_keywords(cert_eval_text) - _GENERIC_CERT_WORDS) | set(core_tokens)
        direct_overlap = cert_kw & job_kw
        specific_overlap = [tok for tok in direct_overlap if tok not in _AMBIGUOUS_SINGLE_CERT_TOKENS]

        if family_overlap or len(direct_overlap) >= 2 or len(specific_overlap) >= 1:
            relevant.append(cert)

    return relevant


def calculate_certifications_match(
    resume_certs: Any,
    job_description: str,
    certifications_req: str = None,
    fuzzy_threshold: Optional[float] = None,
    job_title: str = "",
) -> dict:
    """
    Compare resume certifications against job requirements, supporting graded certification
    hierarchies (e.g. TESDA NC I < NC II < NC III < NC IV) and no-value normalization.
    """
    cand_certs = _normalize_certifications_input(resume_certs)
    req_raw = normalize_requirement_text(certifications_req)
    req_norm = re.sub(r'[.\s]+$', '', req_raw.lower()) if req_raw else ""
    explicit_no_req = _is_no_cert_requirement(certifications_req)

    has_specific_req = False
    has_generic_req = False
    required_certs = "None"
    req_items: list[str] = []

    if req_raw and not explicit_no_req:
        if req_norm in _GENERIC_CERT_REQ_PHRASES:
            required_certs = req_raw
            has_generic_req = True
        else:
            parsed = [p.strip() for p in re.split(r'[|,\n;•]', req_raw) if p.strip()]
            meaningful = [
                p for p in parsed
                if not is_no_value(p) and _cert_core_tokens(_normalize_cert_text(p))
            ]
            if meaningful:
                required_certs = req_raw
                req_items = meaningful
                has_specific_req = True
            else:
                required_certs = req_raw
                has_generic_req = True

    cand_display = ", ".join(cand_certs) if cand_certs else "None provided"

    if not has_specific_req and not has_generic_req:
        if not cand_certs:
            return {
                "score": 1.0,
                "status": STATUS_NOT_REQUIRED,
                "required_certifications": "None",
                "candidate_certifications": "None provided",
                "matched_certifications": [],
                "is_relevant": False,
                "has_requirement": False,
                "reason": format_criterion_reason(
                    STATUS_NOT_REQUIRED,
                    "No certification requirement for this position.",
                ),
            }
        relevant_certs = _filter_relevant_certifications(cand_certs, job_title, job_description)
        detail = (
            f"No certification requirement for this position (candidate holds relevant certification(s): {', '.join(relevant_certs)})."
            if relevant_certs
            else f"No certification requirement for this position (candidate listed: {cand_display})."
        )
        return {
            "score": 1.0,
            "status": STATUS_NOT_REQUIRED,
            "required_certifications": "None",
            "candidate_certifications": cand_display,
            "matched_certifications": relevant_certs,
            "is_relevant": bool(relevant_certs),
            "has_requirement": False,
            "reason": format_criterion_reason(STATUS_NOT_REQUIRED, detail),
        }

    if not cand_certs:
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "required_certifications": required_certs,
            "candidate_certifications": "None provided",
            "matched_certifications": [],
            "is_relevant": False,
            "has_requirement": True,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"No certification found. Job requires {required_certs}.",
            ),
        }

    if has_generic_req:
        relevant_certs = _filter_relevant_certifications(cand_certs, job_title, job_description)
        if relevant_certs:
            return {
                "score": 1.0,
                "status": STATUS_MEETS,
                "required_certifications": required_certs,
                "candidate_certifications": ", ".join(relevant_certs),
                "matched_certifications": relevant_certs,
                "is_relevant": True,
                "has_requirement": True,
                "reason": format_criterion_reason(
                    STATUS_MEETS,
                    f"Candidate holds relevant certification(s) ({', '.join(relevant_certs)}) aligned with this role.",
                ),
            }
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "required_certifications": required_certs,
            "candidate_certifications": cand_display,
            "matched_certifications": [],
            "is_relevant": False,
            "has_requirement": True,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"Candidate certifications ({cand_display}) do not match the required {required_certs} for this role.",
            ),
        }

    # Mode A: Specific required certifications (supports graded certification hierarchies)
    total_req_score = 0.0
    matched_cands: list[str] = []
    matched_reqs: list[str] = []
    exceeds_any = False

    for req_item in req_items:
        best_req_score = 0.0
        best_cand_item: Optional[str] = None
        best_exceeds = False
        alts = _extract_cert_alternatives(req_item)

        for cand_item in cand_certs:
            graded_handled = False
            for alt in alts:
                graded = compare_graded_certifications(cand_item, alt)
                if graded is not None:
                    graded_handled = True
                    if graded["matched"]:
                        if 1.0 > best_req_score or (1.0 == best_req_score and graded["exceeds"] and not best_exceeds):
                            best_req_score = 1.0
                            best_cand_item = cand_item
                            best_exceeds = bool(graded["exceeds"])
                    elif graded["below_level"] and graded["score"] > best_req_score:
                        best_req_score = float(graded["score"])
                        best_cand_item = cand_item
                        best_exceeds = False

            if not graded_handled and _cert_item_matches(cand_item, req_item, fuzzy_threshold=fuzzy_threshold):
                if 1.0 > best_req_score:
                    best_req_score = 1.0
                    best_cand_item = cand_item
                    best_exceeds = False

        if best_req_score > 0.0 and best_cand_item:
            total_req_score += best_req_score
            if best_cand_item not in matched_cands:
                matched_cands.append(best_cand_item)
            if best_req_score >= 1.0 and req_item not in matched_reqs:
                matched_reqs.append(req_item)
            if best_exceeds:
                exceeds_any = True

    if total_req_score <= 0.0:
        return {
            "score": 0.0,
            "status": STATUS_DOES_NOT_MEET,
            "required_certifications": required_certs,
            "candidate_certifications": cand_display,
            "matched_certifications": [],
            "matched_requirements": [],
            "is_relevant": False,
            "has_requirement": True,
            "reason": format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                f"Candidate certifications ({cand_display}) do not match the required {required_certs}.",
            ),
        }

    score = round(total_req_score / len(req_items), 4)
    if score >= 1.0:
        status = STATUS_EXCEEDS if exceeds_any else STATUS_MEETS
        detail = (
            f"Candidate exceeds required certification ({required_certs}) with {', '.join(matched_cands)}."
            if exceeds_any
            else f"Matched required certification(s): {', '.join(matched_cands)}."
        )
    else:
        status = STATUS_PARTIAL
        detail = (
            f"Partially meets certification requirement ({required_certs}); "
            f"candidate holds {', '.join(matched_cands)}."
        )

    return {
        "score": score,
        "status": status,
        "required_certifications": required_certs,
        "candidate_certifications": ", ".join(matched_cands) if matched_cands else cand_display,
        "matched_certifications": matched_cands,
        "matched_requirements": matched_reqs,
        "is_relevant": score >= 1.0,
        "has_requirement": True,
        "reason": format_criterion_reason(status, detail),
    }


def _format_years_label(val: int | float) -> str:
    """Format a year count compactly (e.g. '3 yrs', '1 yr', '0.5 yrs')."""
    num = int(val) if float(val).is_integer() else round(float(val), 1)
    return f"{num} yr{'s' if num != 1 else ''}"


def _format_years_word(val: int | float) -> str:
    """Format a year count in prose (e.g. '3 years', '1 year', '0.5 years')."""
    num = int(val) if float(val).is_integer() else round(float(val), 1)
    return f"{num} year{'s' if num != 1 else ''}"


_LEGACY_APPLICANT_REC_RE = re.compile(
    r'(?:to your resume|tailor your resume|maximize ats|consider taking online courses|'
    r'improve your candidacy|ensure your certifications section|so the ats can|'
    r'to bridge the \d+(?:\.\d+)?-year gap|your resume reflects)',
    re.IGNORECASE,
)


def is_legacy_applicant_recommendation(text: str) -> bool:
    """Return True if a stored recommendation string is applicant-facing resume advice."""
    return bool(text and _LEGACY_APPLICANT_REC_RE.search(str(text)))


def _generate_recommendations(
    skills_result: dict,
    experience_result: dict,
    education_result: dict,
    job_title: str,
    certs_result: Optional[dict] = None,
    relevance_result: Optional[dict] = None,
    match_percentage: Optional[float] = None,
) -> list[str]:
    """
    Generate actionable HR screening, interview probing, and placement recommendations
    based on the candidate's gap analysis for the target role.
    """
    recommendations: list[str] = []
    role_label = job_title or "this position"

    # 1. Overall screening & placement guidance
    if match_percentage is not None:
        if match_percentage >= 80:
            recommendations.append(
                f"Strong overall fit ({match_percentage:.0f}%) for {role_label} — prioritize for technical and behavioral interview and confirm start availability."
            )
        elif match_percentage < 50:
            recommendations.append(
                f"Low overall alignment ({match_percentage:.0f}%) for {role_label} — consider redirecting to better-matched open positions or evaluate trainability before advancing."
            )

    # 2. Skills probing for the interviewer (only when skills are required)
    if skills_result.get("has_requirement", True):
        missing_skills = skills_result.get("missing") or []
        matched_skills = skills_result.get("matched") or []
        if missing_skills:
            missing_list = ", ".join([str(s).title() for s in missing_skills[:5]])
            recommendations.append(
                f"Probe practical familiarity and onboarding needs for missing required skills: {missing_list}."
            )
        elif matched_skills:
            matched_sample = ", ".join([str(s).title() for s in matched_skills[:4]])
            recommendations.append(
                f"Validate hands-on depth and real-world scenarios across matched core skills: {matched_sample}."
            )

    # 3. Experience & role-relevance probing (only when experience is required)
    if experience_result.get("has_requirement", True) and experience_result.get("status") != "Not confirmed":
        req_years = experience_result.get("required_years", 0) or 0
        cand_years = experience_result.get("candidate_years", 0) or 0
        total_years = experience_result.get("total_years", cand_years) or cand_years
        rel_count = (relevance_result or {}).get("relevant_count", 0) or 0
        total_entries = (relevance_result or {}).get("total_entries", 0) or 0

        if total_entries > 0 and rel_count == 0:
            yr_ctx = _format_years_word(total_years) if total_years > 0 else "prior"
            recommendations.append(
                f"Candidate's {yr_ctx} work history is in an unrelated domain — ask how transferable skills apply to {role_label} and assess ramp-up time."
            )
        elif req_years > 0 and cand_years < req_years:
            gap = max(0, req_years - cand_years)
            recommendations.append(
                f"Relevant experience ({_format_years_word(cand_years)}) is {_format_years_word(gap)} below the {_format_years_word(req_years)} requirement — probe whether hands-on projects or domain training offset the tenure gap."
            )
        elif cand_years == 0 and total_years == 0:
            recommendations.append(
                f"Work tenure was not explicitly quantified on the resume — verify exact employment dates and duration for {role_label} during initial screening."
            )
        elif rel_count > 0 and experience_result.get("score", 0) >= 0.8:
            recommendations.append(
                f"Confirm day-to-day scope, independent ownership, and measurable outcomes from the candidate's {_format_years_word(cand_years)} of relevant experience."
            )

    # 4. Certifications / compliance & education verification
    cert_source = certs_result if certs_result is not None else {}
    cert_has_req = cert_source.get("has_requirement", True)
    req_certs = cert_source.get("required_certifications", "None")
    cand_certs = cert_source.get("candidate_certifications", "None")
    certs_relevant = bool(cert_source.get("is_relevant"))
    if cert_has_req and req_certs and not is_no_value(req_certs) and not certs_relevant:
        recommendations.append(
            f"Confirm whether the candidate holds, is renewing, or is willing to obtain required credentials ({req_certs})."
        )
    elif certs_relevant and cand_certs and not is_no_value(cand_certs) and cand_certs != "None provided":
        recommendations.append(
            f"Verify authenticity and validity dates of relevant credentials ({cand_certs}) during pre-employment screening."
        )

    edu_status = education_result.get("status")
    if edu_status == STATUS_MANUAL_REVIEW or education_result.get("needs_manual_review"):
        recommendations.append(
            "Manually review the candidate's educational background (unrecognized degree/attainment format)."
        )
    elif (
        edu_status not in (STATUS_NOT_REQUIRED, STATUS_EXCEEDS, STATUS_MEETS)
        and (education_result.get("score", 1.0) or 0.0) < 0.5
    ):
        req_edu = education_result.get("required_education", "required degree")
        cand_edu = education_result.get("candidate_education", "listed background")
        recommendations.append(
            f"Assess whether practical experience compensates for the education gap ({cand_edu} vs {req_edu})."
        )

    if not recommendations:
        recommendations.append(
            f"Conduct structured behavioral and technical validation tailored to {role_label} responsibilities and team fit."
        )

    return recommendations[:4]


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


def calculate_location_match(candidate_location: str, job_location: str) -> dict:
    """
    Compare resume location against job location requirements.
    Returns a dict with score and details.
    """
    if not job_location or job_location.lower() in ['remote', 'anywhere', 'flexible', 'wfh']:
        return {"score": 1.0, "reason": "Job is remote or location is flexible."}
    
    if not candidate_location:
        if any(term in job_location.lower() for term in ['remote', 'anywhere', 'flexible', 'wfh']):
            return {"score": 1.0, "reason": "Job is remote or location is flexible."}
        return {"score": 0.5, "reason": "Candidate location not specified."}
        
    cand_loc = candidate_location.lower()
    job_loc = job_location.lower()
    
    if cand_loc in job_loc or job_loc in cand_loc:
        return {"score": 1.0, "reason": "Candidate location matches job location."}
        
    if 'hybrid' in job_loc:
        return {"score": 0.8, "reason": "Job is hybrid, assuming partial location match."}
        
    return {"score": 0.0, "reason": f"Candidate location ({candidate_location}) does not match job location ({job_location})."}


def _generate_nlp_strengths(skills_result: dict, experience_result: dict, education_result: dict, relevance_result: dict, certs_result: dict) -> list[str]:
    """Generate strengths list from NLP analysis results."""
    strengths = []
    if skills_result.get("has_requirement", True):
        if skills_result["score"] >= 0.7:
            strengths.append(f"Strong skills alignment — matched {len(skills_result['matched'])} of {len(skills_result['matched']) + len(skills_result['missing'])} required skills.")
        elif skills_result["score"] >= 0.4:
            strengths.append(f"Moderate skills match — {len(skills_result['matched'])} relevant skills identified.")

    relevant_count = relevance_result.get("relevant_count", 0) or 0
    irrelevant_count = relevance_result.get("irrelevant_count", 0) or 0
    duration_verified = experience_result.get("duration_verified", irrelevant_count == 0)
    cand_years = experience_result.get("candidate_years", 0) or 0
    req_years = experience_result.get("required_years", 0) or 0
    if (
        experience_result.get("has_requirement", True)
        and relevant_count > 0
        and duration_verified
        and cand_years > 0
        and experience_result.get("score", 0) >= 0.8
    ):
        yr_text = _format_years_word(cand_years)
        if req_years > 0:
            strengths.append(f"Meets or exceeds the experience requirement with {yr_text} of relevant experience.")
        else:
            strengths.append(f"Brings {yr_text} of relevant work experience.")

    highly_rel_count = relevance_result.get("highly_relevant_count")
    if highly_rel_count is None:
        highly_rel_count = relevance_result.get("relevant_count", 0)
    partially_rel_count = relevance_result.get("partially_relevant_count", 0)
    if highly_rel_count > 0:
        strengths.append(f"{highly_rel_count} work experience(s) are directly relevant to this position.")
    elif partially_rel_count > 0:
        strengths.append(f"{partially_rel_count} work experience(s) are partially relevant to this position.")
    transferable = relevance_result.get("transferable_skills", [])
    if transferable:
        strengths.append(f"Transferable skills: {', '.join(transferable[:4])}.")

    edu_status = education_result.get("status")
    if edu_status == STATUS_EXCEEDS:
        strengths.append(
            f"Exceeds the education requirement ({education_result.get('candidate_education')} vs {education_result.get('required_education')})."
        )
    elif edu_status == STATUS_MEETS or (
        edu_status not in (STATUS_NOT_REQUIRED, STATUS_MANUAL_REVIEW)
        and education_result.get("score", 0) >= 0.8
    ):
        strengths.append("Education background aligns well with job requirements.")

    certs_is_relevant = certs_result.get("is_relevant")
    if certs_is_relevant is None:
        certs_is_relevant = (
            not is_no_value(certs_result.get("required_certifications", "None"))
            and certs_result.get("candidate_certifications", "None") not in ("None", "None provided", "Unrelated", "")
        )
    cert_status = certs_result.get("status")
    if certs_is_relevant and certs_result["score"] >= 0.8:
        if certs_result.get("has_requirement", True) and not is_no_value(certs_result.get("required_certifications", "None")):
            if cert_status == STATUS_EXCEEDS:
                strengths.append(
                    f"Exceeds certification requirement ({', '.join(certs_result.get('matched_certifications') or [])})."
                )
            else:
                strengths.append("Relevant certifications meet the job requirements.")
        else:
            rel_certs = certs_result.get("matched_certifications") or []
            if rel_certs:
                strengths.append(f"Holds relevant certifications for this role ({', '.join(rel_certs[:3])}).")

    if not strengths:
        strengths.append("Resume was successfully parsed and analyzed.")
    return strengths[:5]


def _generate_nlp_weaknesses(skills_result: dict, experience_result: dict, education_result: dict, relevance_result: dict, certs_result: dict) -> list[str]:
    """Generate weaknesses list from NLP analysis results."""
    weaknesses = []
    if experience_result.get("has_requirement", True) and experience_result.get("status") != "Not confirmed":
        req_years = experience_result.get("required_years", 0) or 0
        cand_years = experience_result.get("candidate_years", 0) or 0
        total_years = experience_result.get("total_years", cand_years) or cand_years
        if req_years > 0 and (experience_result.get("below_minimum") or cand_years < req_years):
            gap = max(0, req_years - cand_years)
            rel_suffix = " relevant" if total_years > cand_years else ""
            weaknesses.append(
                f"Gap reported: experience below minimum ({_format_years_label(cand_years)}{rel_suffix} "
                f"vs {_format_years_label(req_years)} required; {_format_years_label(gap)} short)."
            )
    if skills_result.get("has_requirement", True) and skills_result["missing"]:
        missing_sample = ", ".join([s.title() for s in skills_result["missing"][:4]])
        weaknesses.append(f"Missing critical skills: {missing_sample}.")
    if experience_result.get("has_requirement", True) and experience_result.get("status") != "Not confirmed":
        irr_count = relevance_result.get("irrelevant_count", 0)
        total = relevance_result.get("total_entries", 0)
        if irr_count > 0 and irr_count == total:
            weaknesses.append("None of the work experience entries are relevant to this position.")
        elif irr_count > 0:
            weaknesses.append(f"{irr_count} of {total} experience entries are not relevant to this role.")
    edu_status = education_result.get("status")
    if edu_status not in (STATUS_NOT_REQUIRED, STATUS_MANUAL_REVIEW) and education_result["score"] < 0.5:
        weaknesses.append("Education does not fully meet the job requirements.")
    if (
        certs_result.get("has_requirement", True)
        and certs_result.get("status") != "Not confirmed"
        and certs_result["score"] < 0.5
        and not is_no_value(certs_result.get("required_certifications", "None"))
    ):
        weaknesses.append("Required certifications are missing or do not match.")
    return weaknesses[:5]


def _generate_nlp_summary(resume_data: dict, job_title: str, final_pct: float, skills_result: dict, relevance_result: dict) -> str:
    """Generate a human-readable analysis summary using NLP results."""
    name = resume_data.get("fullname", "The candidate")
    matched = len(skills_result["matched"])
    total = matched + len(skills_result["missing"]) + len(skills_result.get("not_confirmed", []))
    rel_count = relevance_result.get("relevant_count", 0)
    total_exp = relevance_result.get("total_entries", 0)

    if final_pct >= 80:
        level_desc = "a strong match"
    elif final_pct >= 50:
        level_desc = "a moderate match"
    else:
        level_desc = "a low match"

    summary = f"{name} is {level_desc} ({final_pct:.0f}%) for the {job_title} position. "
    if skills_result.get("has_requirement", True) and total > 0:
        summary += f"Skills analysis shows {matched}/{total} required skills matched. "
    if total_exp > 0:
        summary += f"{rel_count} of {total_exp} work experience(s) are relevant to this role. "
    else:
        summary += "No work experience entries were provided. "
    return summary.strip()


def _generate_nlp_skills_explanation(skills_result: dict) -> str:
    """Generate a detailed skills explanation from NLP matching."""
    if not skills_result.get("has_requirement", True):
        return skills_result.get("reason") or format_criterion_reason(
            STATUS_NOT_REQUIRED,
            "No specific skills requirements were found in the job description.",
        )
    matched = skills_result["matched"]
    missing = skills_result["missing"]
    total = len(matched) + len(missing) + len(skills_result.get("not_confirmed", []))
    if total == 0:
        return format_criterion_reason(
            STATUS_NOT_REQUIRED,
            "No specific skills requirements were found in the job description.",
        )
    pct = round(skills_result["score"] * 100)
    parts = [f"Skills Match: {pct}% ({len(matched)}/{total} required skills found)."]
    if matched:
        parts.append(f"Matched: {', '.join([s.title() for s in matched[:8]])}.")
    if skills_result.get("not_confirmed"):
        parts.append("Not confirmed: " + ", ".join(skills_result["not_confirmed"]) + ".")
    if missing:
        parts.append(f"Missing: {', '.join([s.title() for s in missing[:8]])}.")
    return " ".join(parts)


_MFG_JOB_TITLE_RE = re.compile(
    r'\b(?:manufactur\w*|production|factory|plant|operator|machin\w*|assembly|assembl\w*|'
    r'warehouse|kiln|glazing|tile|ceramic|welding|smaw|tig|fabrication|forklift|industrial)\b',
    re.I,
)


def build_job_specific_questions(
    resume_data: dict,
    job,
    skills_result: dict,
    experience_result: dict,
    education_result: dict,
    certs_result: dict,
    relevance_result: dict,
    requirement_evaluations: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Generate follow-up clarification questions tailored to the target job
    requisition (`job_title`, `department`, missing skills, certifications, experience).
    """
    job_id = str(getattr(job, "job_id", None) or getattr(job, "id", None) or "job")
    job_slug = re.sub(r'[^a-zA-Z0-9]+', '_', job_id).strip('_').lower() or "job"
    job_title = (getattr(job, "job_title", None) or getattr(job, "title", None) or "this position").strip()
    department = (getattr(job, "department", None) or "").strip()
    skills_req = (getattr(job, "skills_requirements", None) or "").strip()
    job_desc = (getattr(job, "description", None) or "").strip()
    job_text = f"{job_title} {department} {job_desc}"

    questions: list[dict] = []

    req_years = int(experience_result.get("required_years", 0) or 0)
    cand_years = int(experience_result.get("candidate_years", 0) or 0)
    rel_score = float(relevance_result.get("relevance_score", 0.0) or 0.0)
    rel_count = int(relevance_result.get("relevant_count", 0) or 0)
    is_mfg_job = bool(_MFG_JOB_TITLE_RE.search(job_text))

    exp_text = str(resume_data.get("experience") or "")
    work_exps = resume_data.get("work_experiences") or []
    total_exp_months = int(resume_data.get("total_experience_months") or 0)
    raw_years_exp = float(resume_data.get("years_experience") or 0)
    has_dated_work_exp = any(
        isinstance(we, dict)
        and (
            int(we.get("duration_months") or 0) > 0
            or (
                bool(str(we.get("start_date") or "").strip())
                and (bool(str(we.get("end_date") or "").strip()) or bool(we.get("is_current")))
            )
            or bool(re.search(r"\b(?:19|20)\d{2}\b", str(we.get("duration") or we.get("dates") or "")))
        )
        for we in work_exps
    )
    has_explicit_years = (
        cand_years > 0
        or raw_years_exp > 0
        or total_exp_months > 0
        or has_dated_work_exp
        or bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:\+?\s*)?(?:years?|yrs?)\b", exp_text, re.IGNORECASE))
        or bool(re.search(r"\b(?:19|20)\d{2}\s*[-–—to]+\s*(?:(?:19|20)\d{2}|present|current)\b", exp_text, re.IGNORECASE))
    )

    if experience_result.get("has_requirement", True) and not has_explicit_years:
        if is_mfg_job:
            q_text = f"How many years of manufacturing experience do you have for the {job_title} role?"
        elif department:
            q_text = f"How many years of {job_title} ({department}) experience do you have?"
        else:
            q_text = f"How many years of {job_title} experience do you have?"
        if req_years > 0:
            q_text += f" (Target requirement: {req_years}+ years)"
        questions.append({
            "id": f"clarify_{job_slug}_years_experience",
            "field": "years_experience",
            "job_id": job_id,
            "job_title": job_title,
            "question": q_text,
            "type": "number",
            "placeholder": "e.g. 2",
            "required": True,
            "domain": department or ("Manufacturing" if is_mfg_job else "General"),
            "reason": f"Clarifying direct experience duration for {job_title}.",
        })

    from app.services.requirement_confirmation import evaluate_requirements, confirmation_questions
    rows = requirement_evaluations if requirement_evaluations is not None else evaluate_requirements(resume_data, job, _normalize_skill)
    questions.extend(confirmation_questions(rows, job))

    low_job = job_text.lower()
    if re.search(r'\b(?:quality|qc|qa|inspection|audit)\b', low_job):
        fit_q = f"What quality inspection standards, defect checks, or testing instruments have you used relevant to {job_title}?"
    elif re.search(r'\b(?:maint|technician|mechanic|electric|engineer)\b', low_job):
        fit_q = f"What equipment troubleshooting, preventive maintenance, or engineering systems have you handled for {job_title}?"
    elif is_mfg_job:
        fit_q = f"What production lines, factory machinery, or shift operations have you handled relevant to {job_title}?"
    elif re.search(r'\b(?:hr|human\s+resource|recruit|payroll)\b', low_job):
        fit_q = f"What HR processes (recruitment, timekeeping, payroll, or DOLE compliance) have you handled for {job_title}?"
    elif re.search(r'\b(?:account|finance|bookkeep|audit|tax)\b', low_job):
        fit_q = f"What accounting systems, tax compliance filings, or financial reporting tasks have you managed for {job_title}?"
    elif re.search(r'\b(?:software|developer|programmer|it|data|network|cloud|backend|frontend)\b', low_job):
        fit_q = f"What systems, codebases, or production deployments have you delivered relevant to {job_title}?"
    else:
        fit_q = f"What daily responsibilities or accomplishments best qualify you for {job_title} ({department or 'this role'})?"

    has_exp_description = bool(exp_text.strip()) or any(
        isinstance(we, dict)
        and (
            bool(str(we.get("job_title") or "").strip())
            or bool(str(we.get("responsibilities") or we.get("description") or "").strip())
        )
        for we in work_exps
    )
    if experience_result.get("has_requirement", True) and (rel_count == 0 or not has_exp_description):
        questions.append({
            "id": f"clarify_{job_slug}_role_fit",
            "field": "relevance",
            "job_id": job_id,
            "job_title": job_title,
            "question": fit_q,
            "type": "text",
            "placeholder": f"Describe experience relevant to {job_title}",
            "required": False,
            "domain": department or "General",
            "reason": f"Role-specific clarification for {job_title}.",
        })

    return questions


def _extract_entry_duration_months(entry_text: str, work_exp: Optional[dict] = None) -> int:
    """Extract duration in months for a single work experience entry."""
    if isinstance(work_exp, dict):
        try:
            dur = int(work_exp.get("duration_months") or 0)
            if dur > 0:
                return dur
        except (TypeError, ValueError):
            pass
        date_str = " - ".join(
            p for p in [str(work_exp.get("start_date") or "").strip(), str(work_exp.get("end_date") or "").strip()]
            if p
        )
        if not date_str:
            date_str = str(work_exp.get("duration") or work_exp.get("dates") or "").strip()
        if date_str:
            entry_text = f"{entry_text} ({date_str})" if entry_text else date_str

    if not entry_text:
        return 0

    try:
        from app.extractors.content.experience_extractor import _parse_date_and_duration
        _, _, dur_months, _ = _parse_date_and_duration(entry_text)
        if dur_months > 0:
            return dur_months
    except Exception:
        pass

    yr_matches = re.findall(r'\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b', entry_text, re.IGNORECASE)
    if yr_matches:
        try:
            yrs = max(float(m) for m in yr_matches)
            if 0 < yrs < 50:
                return max(1, round(yrs * 12))
        except ValueError:
            pass

    mo_matches = re.findall(r'\b(\d+)\s*(?:months?|mos?)\b', entry_text, re.IGNORECASE)
    if mo_matches:
        try:
            mos = max(int(m) for m in mo_matches)
            if 0 < mos < 600:
                return mos
        except ValueError:
            pass

    return 0


def _match_work_exp_for_entry(entry_text: str, idx: int, total_entries: int, work_exps: list) -> Optional[dict]:
    """Find the structured work_experiences dict corresponding to a pipe-delimited entry."""
    if not isinstance(work_exps, list) or not work_exps:
        return None
    entry_lower = entry_text.lower()
    for we in work_exps:
        if not isinstance(we, dict):
            continue
        title = str(we.get("job_title") or we.get("role") or we.get("title") or "").strip().lower()
        company = str(we.get("company_name") or we.get("company") or "").strip().lower()
        if title and company and title in entry_lower and company in entry_lower:
            return we
    for we in work_exps:
        if not isinstance(we, dict):
            continue
        title = str(we.get("job_title") or we.get("role") or we.get("title") or "").strip().lower()
        if title and title in entry_lower:
            return we
    if len(work_exps) == total_entries and 0 <= idx < len(work_exps) and isinstance(work_exps[idx], dict):
        return work_exps[idx]
    return None


def _resolve_relevant_experience_years(
    resume_data: dict,
    resume_years: int | float,
    relevance_result: dict,
) -> tuple[int | float, bool]:
    """
    Determine years of experience attributable to relevant roles only.
    Returns (relevant_years, duration_verified).
    """
    relevant_count = int(relevance_result.get("relevant_count", 0) or 0)
    irrelevant_count = int(relevance_result.get("irrelevant_count", 0) or 0)
    total_entries = int(relevance_result.get("total_entries", 0) or 0)

    if total_entries == 0:
        return 0, False

    if relevant_count == 0:
        return 0, True

    if irrelevant_count == 0:
        return resume_years, True

    entry_relevances = relevance_result.get("entry_relevances") or []
    work_exps = resume_data.get("work_experiences") or []
    relevant_months = 0
    irrelevant_months = 0

    for item in entry_relevances:
        idx = int(item.get("index", 0) or 0)
        entry_text = str(item.get("entry") or "")
        rel_label = item.get("relevance", "Irrelevant")
        matched_we = _match_work_exp_for_entry(entry_text, idx, len(entry_relevances), work_exps)
        months = _extract_entry_duration_months(entry_text, matched_we)
        if rel_label in ("Highly Relevant", "Partially Relevant"):
            relevant_months += months
        else:
            irrelevant_months += months

    if relevant_months + irrelevant_months > 0:
        if relevant_months == 0:
            rel_years: int | float = 0
        elif relevant_months < 12:
            rel_years = round(relevant_months / 12.0, 1)
        else:
            rel_years = round(relevant_months / 12.0)
        if resume_years > 0 and rel_years > resume_years:
            rel_years = resume_years
        return rel_years, True

    return resume_years, False


def _resolve_experience_text(resume_data: dict) -> str:
    """Resolve pipe-delimited experience text, falling back to structured work_experiences, stripping no-value markers."""
    raw = normalize_requirement_text(resume_data.get("experience"))
    if raw:
        cleaned_entries = [
            e.strip() for e in raw.split("|")
            if normalize_requirement_text(e)
        ]
        if cleaned_entries:
            return " | ".join(cleaned_entries)
    work_exps = resume_data.get("work_experiences") or []
    if not isinstance(work_exps, list):
        return ""
    parts = []
    for we in work_exps:
        if not isinstance(we, dict):
            continue
        title = normalize_requirement_text(we.get("job_title") or we.get("role") or we.get("title"))
        company = normalize_requirement_text(we.get("company_name") or we.get("company"))
        resp = we.get("responsibilities") or we.get("description") or []
        if isinstance(resp, list):
            resp_text = "; ".join(
                normalize_requirement_text(r) for r in resp if normalize_requirement_text(r)
            )
        else:
            resp_text = normalize_requirement_text(resp)
        header = f"{title} at {company}" if (title and company) else (title or company)
        entry = f"{header} - Responsibilities: {resp_text}" if (header and resp_text) else (header or resp_text)
        if entry:
            parts.append(entry)
    return " | ".join(parts)


def calculate_match_score(
    resume_data: dict,
    job,
    use_ai: bool = False,
    matching_config: Optional[dict] = None,
    log_prediction: bool = True,
) -> dict:
    """
    Calculate the overall match score between a parsed resume and a job.

    Scoring Strategy (100% NLP + Rule-Based):
    ──────────────────────────────────────────
    Weights are resolved per job: if the job has its own `scoring_weights`
    (set by an admin), those are used; otherwise the global default weights
    from System Settings apply. Thresholds always come from System Settings.
    Skills + Experience Relevance + Education + Certifications + Resume Completeness

    All analysis is performed locally using spaCy NLP, keyword matching,
    fuzzy matching, and rule-based heuristics. No external AI API is used.
    """
    if matching_config is None:
        matching_config = get_current_matching_config()

    thresholds = matching_config.get("thresholds") or {}

    job_weights = get_job_scoring_weights(job)
    if job_weights is not None:
        weights = job_weights
        weights_source = "job"
    else:
        weights = matching_config.get("weights") or {}
        weights_source = "global"

    w_skills = float(weights.get("skills_weight", THESIS_DEFAULT_WEIGHTS["skills_weight"]))
    w_exp = float(weights.get("experience_weight", THESIS_DEFAULT_WEIGHTS["experience_weight"]))
    w_edu = float(weights.get("education_weight", THESIS_DEFAULT_WEIGHTS["education_weight"]))
    w_certs = float(weights.get("certifications_weight", THESIS_DEFAULT_WEIGHTS["certifications_weight"]))
    w_completeness = float(weights.get("completeness_weight", THESIS_DEFAULT_WEIGHTS["completeness_weight"]))

    fuzzy_th = float(thresholds.get("fuzzy_match_threshold", 0.75))
    min_score = float(thresholds.get("minimum_match_score", 30.0))
    trans_cap = int(thresholds.get("transferable_skills_cap", 2))

    # If job is passed as a dictionary, adapt it to an object with attribute access
    if isinstance(job, dict):
        from types import SimpleNamespace
        job = SimpleNamespace(
            id=job.get("id", None),
            job_id=job.get("job_id", ""),
            job_title=job.get("job_title", "Unknown Job"),
            department=job.get("department", ""),
            location=job.get("location", ""),
            job_type=job.get("job_type", None),
            description=job.get("description", ""),
            skills_requirements=job.get("skills_requirements", ""),
            experience_requirements=job.get("experience_requirements", None),
            education_requirements=job.get("education_requirements", None),
            certifications_requirements=job.get("certifications_requirements", None),
            scoring_weights=job.get("scoring_weights", None),
        )

    from app.services.requirement_confirmation import evaluate_requirements, apply_confirmations
    requirement_evaluations = evaluate_requirements(
        resume_data, job, _normalize_skill, matching_config.get("related_terms")
    )
    resume_data = apply_confirmations(resume_data, requirement_evaluations)

    # ── Rule-based scoring ────────────────────────────────────────────────────
    resume_skills = resume_data.get("skills", "")
    job_skills = job.skills_requirements or ""
    skills_result = calculate_skills_match(resume_skills, job_skills, fuzzy_threshold=fuzzy_th)
    skill_rows = [r for r in requirement_evaluations if r["field"] == "skills"]
    if skill_rows:
        matched = [r["requirement"] for r in skill_rows if r["status"] == STATUS_MEETS]
        failed = [r["requirement"] for r in skill_rows if r["status"] == STATUS_DOES_NOT_MEET]
        pending = [r["requirement"] for r in skill_rows if r["status"] in ("Not confirmed", "Possible match")]
        status = "Not confirmed" if pending else (STATUS_MEETS if not failed else STATUS_PARTIAL if matched else STATUS_DOES_NOT_MEET)
        skills_result.update(score=len(matched) / len(skill_rows), matched=matched, missing=failed,
                             not_confirmed=pending, status=status)
        skills_result["reason"] = format_criterion_reason(status,
            f"{len(matched)} of {len(skill_rows)} skills confirmed; {len(pending)} not confirmed; {len(failed)} answered No.")
    skills_status = skills_result.get(
        "status",
        STATUS_NOT_REQUIRED if not skills_result.get("has_requirement", True) else STATUS_MEETS,
    )

    resume_years = resume_data.get("years_experience", 0) or 0
    job_desc = (job.description or "") + " " + (job.skills_requirements or "")

    # Experience RELEVANCE analysis (evaluated before years-of-experience check so
    # tenure on unrelated roles is never credited as meeting the job's requirement).
    resume_experience = _resolve_experience_text(resume_data)
    relevance_result = calculate_experience_relevance(
        resume_experience, resume_skills, job.job_title, job_desc, transferable_cap=trans_cap
    )
    relevant_years, duration_verified = _resolve_relevant_experience_years(
        resume_data, resume_years, relevance_result
    )
    total_exp_entries = relevance_result.get("total_entries", 0) or 0
    effective_exp_years = (
        relevant_years
        if (total_exp_entries > 0 and (relevance_result.get("relevant_count", 0) == 0 or duration_verified))
        else resume_years
    )
    raw_exp_req = getattr(job, 'experience_requirements', None)
    exp_req_arg = "" if (raw_exp_req is None or is_no_value(raw_exp_req)) else str(raw_exp_req)
    experience_result = calculate_experience_match(
        effective_exp_years, job_desc, exp_req_arg
    )
    experience_result["total_years"] = resume_years
    experience_result["duration_verified"] = duration_verified
    exp_has_requirement = bool(experience_result.get("has_requirement", True))

    if exp_has_requirement and resume_years > effective_exp_years:
        req_yrs_exp = experience_result.get("required_years", 0) or 0
        gap_yrs_exp = experience_result.get("gap_years", max(0, req_yrs_exp - effective_exp_years))
        other_ctx = f"{_format_years_label(resume_years)} unrelated" if effective_exp_years == 0 else f"{_format_years_label(resume_years)} total"
        if experience_result.get("below_minimum") and req_yrs_exp > 0:
            experience_result["reason"] = format_criterion_reason(
                experience_result.get("status", STATUS_PARTIAL),
                (
                    f"Gap reported: experience below minimum — {_format_years_label(effective_exp_years)} relevant "
                    f"({other_ctx}) vs {_format_years_label(req_yrs_exp)} required "
                    f"({_format_years_label(gap_yrs_exp)} short)."
                ),
            )
        elif req_yrs_exp == 0 and effective_exp_years == 0:
            experience_result["reason"] = format_criterion_reason(
                STATUS_DOES_NOT_MEET,
                "No relevant work experience found for this position.",
            )

    rel_count = relevance_result.get("relevant_count", 0)
    irr_count = relevance_result.get("irrelevant_count", 0)
    if not exp_has_requirement:
        # Bug 2 fix: "None" / no experience requirement earns full credit at its normal weight
        combined_exp_score = 1.0
        exp_status = STATUS_NOT_REQUIRED
    else:
        # STRICT COMBINED SCORE: Relevance dominates at 75%.
        relevance_score = relevance_result["relevance_score"]
        has_any_relevant = rel_count > 0
        if not has_any_relevant:
            combined_exp_score = min(0.10, experience_result["score"] * 0.10)
            exp_status = STATUS_DOES_NOT_MEET
        else:
            combined_exp_score = (
                experience_result["score"] * 0.25 +
                relevance_score * 0.75
            )
            if experience_result.get("below_minimum"):
                max_below_min_score = round(
                    experience_result["score"] * 0.65 + min(relevance_score, experience_result["score"]) * 0.35,
                    4,
                )
                combined_exp_score = min(combined_exp_score, max_below_min_score)
            exp_status = experience_result.get("status") or STATUS_MEETS
            if irr_count > 0 and experience_result.get("below_minimum"):
                exp_status = STATUS_PARTIAL if combined_exp_score >= 0.4 else STATUS_DOES_NOT_MEET

    # Education matching (shared 1-8 hierarchy + ongoing rules + separate field check + manual review)
    resume_education = _resolve_education_text(resume_data)
    raw_edu_req = getattr(job, 'education_requirements', None)
    edu_req_arg = "" if (raw_edu_req is None or is_no_value(raw_edu_req)) else str(raw_edu_req)
    education_result = calculate_education_match(
        resume_education,
        job_desc,
        edu_req_arg,
        education_entries=resume_data.get("education_entries"),
    )
    edu_status = education_result.get("status", STATUS_MEETS)

    # Certifications matching (never fall back to skills — only actual certifications)
    raw_certs = resume_data.get("certifications")
    if not raw_certs or (isinstance(raw_certs, str) and _is_no_cert_requirement(raw_certs)):
        raw_certs = resume_data.get("candidate_certifications") or resume_data.get("certifications_list") or ""
    if isinstance(raw_certs, str) and is_no_value(raw_certs):
        raw_certs = ""
    certs_result = calculate_certifications_match(
        raw_certs,
        job_desc,
        getattr(job, 'certifications_requirements', None),
        fuzzy_threshold=fuzzy_th,
        job_title=getattr(job, 'job_title', "") or "",
    )
    certs_status = certs_result.get(
        "status",
        STATUS_NOT_REQUIRED if not certs_result.get("has_requirement", True) else STATUS_MEETS,
    )

    # Sync certification requirement evaluations with confident resume matches (e.g. graded NC levels or abbreviations)
    cert_rows = [r for r in requirement_evaluations if r["field"] == "certifications"]
    if cert_rows:
        matched_cert_req_keys = {_normalize_skill(m) for m in (certs_result.get("matched_requirements") or [])}
        cert_fully_matched = float(certs_result.get("score", 0.0) or 0.0) >= 1.0
        for row in cert_rows:
            if row.get("source") == "Confirmed by applicant":
                continue
            if cert_fully_matched or _normalize_skill(row["requirement"]) in matched_cert_req_keys:
                row["status"] = STATUS_MEETS
                row["source"] = "Resume"
        # Ensure positive applicant confirmations on certifications (including generic phrases) count in score
        confirmed_certs = [r for r in cert_rows if r["status"] == STATUS_MEETS]
        if confirmed_certs and float(certs_result.get("score", 0.0) or 0.0) < (len(confirmed_certs) / len(cert_rows)):
            certs_result["score"] = round(len(confirmed_certs) / len(cert_rows), 4)
            if certs_result["score"] >= 1.0:
                certs_result["status"] = STATUS_MEETS
                certs_result["is_relevant"] = True
                certs_result["reason"] = format_criterion_reason(
                    STATUS_MEETS,
                    f"Confirmed required certification(s): {', '.join(r['requirement'] for r in confirmed_certs)}.",
                )
        denied_certs = [r for r in cert_rows if r.get("answer") == "no"]
        if denied_certs:
            # A remaining alias (e.g. "BOSH Certified") must not override an
            # explicit No to "BOSH". Retain graded credit for other requirements.
            credits = [
                0.0 if r.get("answer") == "no" else
                1.0 if r["status"] == STATUS_MEETS else
                calculate_certifications_match(
                    raw_certs, job_desc, r["requirement"],
                    fuzzy_threshold=fuzzy_th, job_title=getattr(job, "job_title", "") or "",
                )["score"]
                for r in cert_rows
            ]
            certs_result["score"] = sum(credits) / len(cert_rows)
            certs_result["status"] = STATUS_PARTIAL if any(credits) else STATUS_DOES_NOT_MEET
            certs_result["is_relevant"] = False
            certs_result["reason"] = format_criterion_reason(
                certs_result["status"],
                f"Applicant answered No: {', '.join(r['requirement'] for r in denied_certs)}.",
            )

    for field, result in (("experience", experience_result), ("certifications", certs_result)):
        rows = [r for r in requirement_evaluations if r["field"] == field]
        pending = [r for r in rows if r["status"] in ("Not confirmed", "Possible match")]
        if pending:
            existing_detail = re.sub(
                r"^(?:Does not meet|Partially meets|Meets requirement|Exceeds requirement|Not confirmed|Needs manual review|Not required):\s*",
                "",
                str(result.get("reason") or "").strip(),
                flags=re.I,
            )
            pending_text = "Awaiting applicant confirmation: " + "; ".join(r["requirement"] for r in pending)
            combined_detail = f"{existing_detail} {pending_text}".strip() if existing_detail else pending_text
            result["status"] = "Not confirmed"
            result["reason"] = format_criterion_reason("Not confirmed", combined_detail)
            if field == "experience":
                exp_status = "Not confirmed"
            else:
                certs_status = "Not confirmed"
    certs_status = certs_result.get("status", certs_status)

    # Location matching
    resume_location = resume_data.get("location", "")
    location_result = calculate_location_match(resume_location, getattr(job, 'location', None))

    # Resume Completeness matching (Thesis Criterion: 5%)
    raw_completeness = resume_data.get("completeness_score")
    if raw_completeness is None:
        # Compute completeness from the 4 core profile/form sections (0-100), ignoring no-value placeholders
        has_personal = bool(
            normalize_requirement_text(resume_data.get("fullname"))
            or normalize_requirement_text(resume_data.get("email"))
            or normalize_requirement_text(resume_data.get("phone"))
        )
        raw_skills_val = resume_data.get("skills")
        skills_list_val = clean_list_items(resume_data.get("skills_list") or [])
        has_skills = bool(normalize_requirement_text(raw_skills_val) or skills_list_val)
        has_exp = bool(
            normalize_requirement_text(resume_experience)
            or resume_data.get("work_experiences")
            or (resume_data.get("years_experience") or 0) > 0
        )
        has_edu = bool(
            normalize_requirement_text(resume_education)
            or normalize_requirement_text(resume_data.get("highest_degree"))
            or normalize_requirement_text(resume_data.get("degree"))
            or resume_data.get("education_entries")
        )
        present_core = sum(1 for flag in (has_personal, has_skills, has_exp, has_edu) if flag)
        raw_completeness = round((present_core / 4.0) * 100.0, 1)
    try:
        completeness_num = float(raw_completeness)
        completeness_score_val = (completeness_num / 100.0) if completeness_num > 1.0 else completeness_num
    except (ValueError, TypeError):
        completeness_score_val = 1.0
    completeness_score_val = max(0.0, min(1.0, completeness_score_val))

    # ── Weighted NLP composite (normalized by sum of active weights) ──────────
    # Thesis model: Skills (40%), Experience (30%), Education (15%), Certifications (10%), Completeness (5%)
    total_w = w_skills + w_exp + w_edu + w_certs + w_completeness
    if total_w <= 0:
        total_w = 1.0

    rule_match_pct = (
        (skills_result["score"] * w_skills) +
        (combined_exp_score * w_exp) +
        (education_result["score"] * w_edu) +
        (certs_result["score"] * w_certs) +
        (completeness_score_val * w_completeness)
    ) / total_w * 100

    # ── NLP baseline + optional Gemini AI semantic blending ──────────────────
    blended_skills_score = round(skills_result["score"] * 100, 1)
    blended_exp_score = round(combined_exp_score * 100, 1)
    blended_edu_score = round(education_result["score"] * 100, 1)
    blended_certs_score = round(certs_result["score"] * 100, 1)
    blended_location_score = round(location_result["score"] * 100, 1)
    blended_completeness_score = round(completeness_score_val * 100, 1)
    final_match_pct = min(100.0, round(rule_match_pct, 1))

    all_matched = list(skills_result["matched"])
    all_missing = list(skills_result["missing"])
    final_recommendations = _generate_recommendations(
        skills_result,
        experience_result,
        education_result,
        job.job_title,
        certs_result=certs_result,
        relevance_result=relevance_result,
        match_percentage=final_match_pct,
    )

    pct_skills = round((w_skills / total_w) * 100)
    pct_exp = round((w_exp / total_w) * 100)
    pct_edu = round((w_edu / total_w) * 100)
    pct_certs = round((w_certs / total_w) * 100)
    pct_completeness = round((w_completeness / total_w) * 100)

    # ── Optional Gemini semantic scoring (gracefully falls back to NLP) ───────
    ai_powered = False
    gemini_model_used: Optional[str] = None
    gemini_result: Optional[dict] = None
    if use_ai:
        try:
            from app.services.gemini_service import gemini_analyze_match, is_gemini_enabled

            if is_gemini_enabled():
                job_payload = {
                    "job_title": getattr(job, "job_title", ""),
                    "department": getattr(job, "department", ""),
                    "description": getattr(job, "description", "") or "",
                    "skills_requirements": getattr(job, "skills_requirements", "") or "",
                    "experience_requirements": getattr(job, "experience_requirements", "") or "",
                    "education_requirements": getattr(job, "education_requirements", "") or "",
                    "certifications_requirements": getattr(job, "certifications_requirements", "") or "",
                }
                gemini_result = gemini_analyze_match(resume_data, job_payload)
        except Exception as ai_err:
            logger.warning(f"Gemini match analysis skipped (falling back to NLP): {ai_err}")
            gemini_result = None

    if gemini_result:
        try:
            raw_ai_w = max(0.0, float(thresholds.get("ai_score_weight", 0.8)))
            raw_rule_w = max(0.0, float(thresholds.get("rule_score_weight", 0.2)))
            blend_total = raw_ai_w + raw_rule_w
            ai_w = (raw_ai_w / blend_total) if blend_total > 0 else 0.8
            rule_w = (raw_rule_w / blend_total) if blend_total > 0 else 0.2

            def _blend_dim(rule_v: float, ai_v: Optional[float]) -> float:
                if ai_v is None:
                    return round(rule_v, 1)
                return round(max(0.0, min(100.0, rule_v * rule_w + float(ai_v) * ai_w)), 1)

            final_match_pct = _blend_dim(final_match_pct, gemini_result.get("ai_match_score"))
            if skills_status != STATUS_NOT_REQUIRED:
                blended_skills_score = _blend_dim(blended_skills_score, gemini_result.get("ai_skills_score"))
            if exp_status != STATUS_NOT_REQUIRED:
                blended_exp_score = _blend_dim(blended_exp_score, gemini_result.get("ai_experience_score"))
            if edu_status != STATUS_NOT_REQUIRED:
                blended_edu_score = _blend_dim(blended_edu_score, gemini_result.get("ai_education_score"))
            if certs_status != STATUS_NOT_REQUIRED and gemini_result.get("ai_certifications_score") is not None:
                blended_certs_score = _blend_dim(blended_certs_score, gemini_result.get("ai_certifications_score"))

            all_matched = _merge_unique(all_matched, gemini_result.get("matched_skills") or [])
            matched_keys = {_normalize_skill(s) for s in all_matched}
            all_missing = [
                s for s in _merge_unique(all_missing, gemini_result.get("missing_skills") or [])
                if _normalize_skill(s) not in matched_keys
            ]
            if gemini_result.get("recommendations"):
                final_recommendations = list(gemini_result["recommendations"])

            ai_powered = True
            gemini_model_used = gemini_result.get("gemini_model")
        except Exception as blend_err:
            logger.warning(f"Failed blending Gemini result; using NLP baseline: {blend_err}")
            gemini_result = None
            ai_powered = False

    # ── Generate insights ────────────────────────────────────────────────────
    if final_match_pct >= 80:
        match_level = "High Match"
    elif final_match_pct >= 50:
        match_level = "Medium Match"
    else:
        match_level = "Low Match"

    meets_threshold = final_match_pct >= min_score

    relevance_level = relevance_result.get("relevance_level", "Unknown")
    transferable_skills = relevance_result.get("transferable_skills", [])
    if gemini_result and gemini_result.get("transferable_skills"):
        transferable_skills = _merge_unique(transferable_skills, gemini_result.get("transferable_skills") or [])

    strengths = (
        list(gemini_result["strengths"])
        if (gemini_result and gemini_result.get("strengths"))
        else _generate_nlp_strengths(skills_result, experience_result, education_result, relevance_result, certs_result)
    )
    weaknesses = (
        list(gemini_result["weaknesses"])
        if (gemini_result and gemini_result.get("weaknesses"))
        else _generate_nlp_weaknesses(skills_result, experience_result, education_result, relevance_result, certs_result)
    )
    ai_summary = (
        gemini_result["ai_summary"]
        if (gemini_result and gemini_result.get("ai_summary"))
        else _generate_nlp_summary(resume_data, job.job_title, final_match_pct, skills_result, relevance_result)
    )
    if any(r["status"] in ("Not confirmed", "Possible match") for r in requirement_evaluations):
        ai_summary += " Score reflects confirmed evidence; unconfirmed requirements are pending, not failures."
    skills_explanation = (
        gemini_result["skills_explanation"]
        if (gemini_result and gemini_result.get("skills_explanation"))
        else _generate_nlp_skills_explanation(skills_result)
    )
    experience_explanation = (
        gemini_result["experience_explanation"]
        if (gemini_result and gemini_result.get("experience_explanation"))
        else (
            experience_result.get("reason", "")
            if not exp_has_requirement
            else (relevance_result.get("detailed_breakdown", "") or experience_result.get("reason", ""))
        )
    )
    education_explanation = (
        gemini_result["education_explanation"]
        if (gemini_result and gemini_result.get("education_explanation"))
        else education_result.get("reason", "")
    )
    certification_explanation = (
        gemini_result["certification_explanation"]
        if (gemini_result and gemini_result.get("certification_explanation"))
        else certs_result.get("reason", "")
    )
    location_explanation = location_result.get("reason", "")
    completeness_explanation = f"Candidate resume completeness assessed at {blended_completeness_score}%."

    if ai_powered and gemini_result:
        score_explanation = (
            f"Gemini AI Semantic Fit ({round(ai_w * 100)}%) + ATS Rule Validation ({round(rule_w * 100)}%): "
            f"Overall {final_match_pct}% (Gemini {gemini_result.get('ai_match_score', final_match_pct)}%, "
            f"ATS Rule {min(100.0, round(rule_match_pct, 1))}%)"
        )
    else:
        score_explanation = (
            f"NLP Analysis: Skills {blended_skills_score}% (weight {pct_skills}%) + "
            f"Experience {blended_exp_score}% (weight {pct_exp}%) + "
            f"Education {blended_edu_score}% (weight {pct_edu}%) + "
            f"Certifications {blended_certs_score}% (weight {pct_certs}%) + "
            f"Resume Completeness {blended_completeness_score}% (weight {pct_completeness}%) = {final_match_pct}%"
        )

    # ── Build reason strings ──────────────────────────────────────────────────
    skills_reason = skills_result.get("reason", "")

    experience_text = resume_experience
    exp_entries = [e.strip() for e in experience_text.split("|") if e.strip()] if experience_text else []
    relevant_experience = " | ".join(exp_entries[:3]) if exp_entries else "No specific roles extracted."

    rel_count = relevance_result.get("relevant_count", 0)
    irr_count = relevance_result.get("irrelevant_count", 0)
    total_exp = relevance_result.get("total_entries", len(exp_entries))
    experience_reason_strict = experience_result["reason"]
    if exp_has_requirement and total_exp > 0 and exp_status != "Not confirmed":
        if rel_count == 0:
            strict_detail = (
                f"None of the {total_exp} work experience(s) are relevant to this position. "
                f"Experience score reflects zero qualifying entries."
            )
            if experience_result.get("below_minimum"):
                strict_detail += f" {experience_result['reason']}"
            experience_reason_strict = format_criterion_reason(STATUS_DOES_NOT_MEET, strict_detail)
        elif irr_count > 0:
            experience_reason_strict = format_criterion_reason(
                exp_status,
                (
                    f"{rel_count} of {total_exp} experience(s) are relevant. "
                    f"{irr_count} irrelevant experience(s) were excluded from scoring. "
                    + experience_result["reason"]
                ),
            )

    # ── Self-Improving ML Engine Evaluation & Feedback Logging ──
    ml_eval = None
    try:
        from app.ml_engine import get_production_model, get_feedback_db
        prod_model = get_production_model()
        cand_skills = resume_data.get("skills", "")
        job_skills = (
            job.skills_requirements if hasattr(job, "skills_requirements")
            else (job.get("skills_requirements", "") if isinstance(job, dict) else (getattr(job, "description", "") or ""))
        )
        cand_title = resume_data.get("job_title", "") or resume_experience or "applicant"
        target_title = job.get("job_title", "") if isinstance(job, dict) else getattr(job, "job_title", "")
        cand_years = resume_data.get("years_experience", 0) or 0
        req_years = experience_result.get("required_years", 0) or 0
        cand_edu = resume_education
        req_edu = getattr(job, "education_requirements", "") if not isinstance(job, dict) else job.get("education_requirements", "")

        ml_eval = prod_model.predict(
            candidate_skills=cand_skills,
            job_skills=job_skills,
            candidate_title=cand_title,
            job_title=target_title,
            candidate_years=cand_years,
            required_years=req_years,
            candidate_edu=cand_edu,
            required_edu=req_edu,
        )

        # Log live candidate prediction to Phase 3 feedback DB for HITL tracking
        cand_email = resume_data.get("email")
        cand_name = resume_data.get("fullname")
        cand_id = resume_data.get("id") or resume_data.get("application_id")
        resume_ident = cand_id or cand_email or cand_name or "anonymous"

        job_code = job.get("job_id") if isinstance(job, dict) else getattr(job, "job_id", None)
        job_db_id = job.get("id") if isinstance(job, dict) else getattr(job, "id", None)
        job_ident = str(job_code or job_db_id or "unknown")

        if log_prediction:
            fb_db = get_feedback_db()
            fb_db.log_live_prediction(
                resume_id=str(resume_ident),
                job_id=str(job_ident),
                resume_skills=cand_skills,
                job_skills=job_skills,
                resume_titles=cand_title,
                job_titles=target_title,
                candidate_years=cand_years,
                required_years=req_years,
                candidate_edu=cand_edu,
                required_edu=req_edu,
                feature_vector=ml_eval["feature_vector"],
                predicted_fit_score=ml_eval["fit_probability"],
                candidate_email=cand_email,
                candidate_name=cand_name,
                job_code=job_code,
            )
    except Exception as ml_err:
        logger.debug(f"Notice during ML scoring or live prediction logging: {ml_err}")

    followup_questions = build_job_specific_questions(
        resume_data=resume_data,
        job=job,
        skills_result=skills_result,
        experience_result=experience_result,
        education_result=education_result,
        certs_result=certs_result,
        relevance_result=relevance_result,
        requirement_evaluations=requirement_evaluations,
    )

    req_yrs_gap = experience_result.get("required_years", 0) or 0
    cand_yrs_gap = experience_result.get("candidate_years", 0) or 0
    below_min_exp = bool(
        exp_has_requirement
        and exp_status != "Not confirmed"
        and experience_result.get("below_minimum", req_yrs_gap > 0 and cand_yrs_gap < req_yrs_gap)
    )
    gap_years_val = int(math.ceil(float(experience_result.get("gap_years", max(0, req_yrs_gap - cand_yrs_gap)) or 0))) if below_min_exp else 0
    if below_min_exp:
        cand_label = _format_years_label(cand_yrs_gap)
        if resume_years > cand_yrs_gap:
            other_ctx = f"{_format_years_label(resume_years)} unrelated" if cand_yrs_gap == 0 else f"{_format_years_label(resume_years)} total"
            cand_label = f"{cand_label} relevant ({other_ctx})"
        experience_gaps_text = (
            f"Gap reported: experience below minimum — Required: {req_yrs_gap} yrs | "
            f"Candidate: {cand_label} "
            f"({gap_years_val} yr{'s' if gap_years_val != 1 else ''} short)"
        )
        requirement_gaps = [experience_gaps_text]
        if experience_gaps_text not in ai_summary:
            ai_summary = f"{ai_summary} {experience_gaps_text}."
    else:
        experience_gaps_text = None
        requirement_gaps = []

    completeness_status = (
        STATUS_MEETS if blended_completeness_score >= 75
        else (STATUS_PARTIAL if blended_completeness_score >= 25 else STATUS_DOES_NOT_MEET)
    )
    criteria_evaluations = {
        "skills": {
            "status": skills_status,
            "score": round(blended_skills_score, 1),
            "weight": pct_skills,
            "has_requirement": bool(skills_result.get("has_requirement", True)),
            "reason": skills_reason,
        },
        "experience": {
            "status": exp_status,
            "score": round(blended_exp_score, 1),
            "weight": pct_exp,
            "has_requirement": exp_has_requirement,
            "reason": experience_reason_strict,
        },
        "education": {
            "status": edu_status,
            "score": round(blended_edu_score, 1),
            "weight": pct_edu,
            "has_requirement": bool(education_result.get("has_requirement", True)),
            "needs_manual_review": bool(education_result.get("needs_manual_review", False)),
            "reason": education_result.get("reason", ""),
        },
        "certifications": {
            "status": certs_status,
            "score": round(blended_certs_score, 1),
            "weight": pct_certs,
            "has_requirement": bool(certs_result.get("has_requirement", True)),
            "reason": certs_result.get("reason", ""),
        },
        "completeness": {
            "status": completeness_status,
            "score": round(blended_completeness_score, 1),
            "weight": pct_completeness,
            "has_requirement": True,
            "reason": completeness_explanation,
        },
    }

    job_has_skills_req = bool(skills_result.get("has_requirement", False))
    job_has_exp_req = bool(exp_has_requirement)
    job_has_edu_req = bool(education_result.get("has_requirement", False))
    job_has_certs_req = bool(certs_result.get("has_requirement", False))
    job_has_any_requirement = any((job_has_skills_req, job_has_exp_req, job_has_edu_req, job_has_certs_req))

    eligibility_reasons: list[str] = []
    if job_has_any_requirement:
        if not meets_threshold:
            eligibility_reasons.append(
                f"Overall match score ({final_match_pct:.1f}%) is below the accepted minimum requirement ({min_score:.1f}%)."
            )
        if job_has_skills_req and blended_skills_score <= 0 and final_match_pct < max(min_score, 45.0):
            missing_preview = ", ".join(all_missing[:4]) if all_missing else "required role skills"
            eligibility_reasons.append(
                f"None of the required skills were matched (missing: {missing_preview})."
            )
        if below_min_exp and not meets_threshold:
            eligibility_reasons.append(
                f"Experience is below minimum requirement ({cand_yrs_gap} yr{'s' if cand_yrs_gap != 1 else ''} vs {req_yrs_gap} yr{'s' if req_yrs_gap != 1 else ''} required)."
            )
        if job_has_edu_req and edu_status == STATUS_DOES_NOT_MEET and not meets_threshold:
            eligibility_reasons.append(
                f"Education does not meet the required qualification ({education_result.get('required_education', 'specified degree')})."
            )
        if job_has_certs_req and certs_status == STATUS_DOES_NOT_MEET and not meets_threshold:
            eligibility_reasons.append(
                f"Missing required certification(s) ({certs_result.get('required_certifications', 'specified certification')})."
            )

    eligible_to_apply = (not job_has_any_requirement) or (meets_threshold and len(eligibility_reasons) == 0)

    return {
        "job_id": job.get("job_id") if isinstance(job, dict) else getattr(job, "job_id", None),
        "job_title": job.get("job_title", "Unknown Job") if isinstance(job, dict) else getattr(job, "job_title", "Unknown Job"),
        "department": job.get("department", "") if isinstance(job, dict) else getattr(job, "department", ""),
        "location": job.get("location", "") if isinstance(job, dict) else getattr(job, "location", ""),
        "job_type": job.get("job_type", None) if isinstance(job, dict) else (getattr(job.job_type, "value", None) if getattr(job, "job_type", None) else None),
        # ── Scores ──
        "match_percentage": final_match_pct,
        "match_level": match_level,
        "ml_fit_percentage": ml_eval["fit_percentage"] if ml_eval else None,
        "ml_fit_probability": ml_eval["fit_probability"] if ml_eval else None,
        "ml_features": ml_eval["features"] if ml_eval else None,
        "ml_model_version": ml_eval["model_version"] if ml_eval else None,
        "skills_score": round(blended_skills_score, 1),
        "skills_explanation": skills_explanation,
        "skills_status": skills_status,
        "experience_score": round(blended_exp_score, 1),
        "experience_explanation": experience_explanation,
        "experience_status": exp_status,
        "education_score": round(blended_edu_score, 1),
        "education_explanation": education_explanation,
        "education_status": edu_status,
        "certifications_score": round(blended_certs_score, 1),
        "certification_explanation": certification_explanation,
        "certifications_status": certs_status,
        "completeness_score": round(blended_completeness_score, 1),
        "completeness_explanation": completeness_explanation,
        "location_score": round(blended_location_score, 1),
        "location_explanation": location_explanation,
        "criteria_evaluations": criteria_evaluations,
        # ── Skills ──
        "matched_skills": all_matched,
        "missing_skills": all_missing,
        "not_confirmed_skills": skills_result.get("not_confirmed", []),
        "requirement_evaluations": requirement_evaluations,
        "transferable_skills": transferable_skills,
        # ── Reasons ──
        "skills_reason": skills_reason,
        "experience_reason": experience_reason_strict,
        "experience_relevance_summary": relevance_result.get("reason", ""),
        "education_reason": education_result.get("reason", ""),
        "certifications_reason": certs_result.get("reason", ""),
        "location_reason": location_result.get("reason", ""),
        # ── Experience ──
        "relevant_experience": relevant_experience,
        "experience_gaps": experience_gaps_text,
        "experience_below_minimum": below_min_exp,
        "experience_gap_years": gap_years_val,
        "requirement_gaps": requirement_gaps,
        # ── Education / Certifications ──
        "required_degree": education_result.get("required_education", "Not specified"),
        "candidate_degree": education_result.get("candidate_education", "Not specified"),
        "required_certifications": certs_result.get("required_certifications", "None"),
        "candidate_certifications": certs_result.get("candidate_certifications", "None"),
        # ── AI / NLP Insights ──
        "recommendations": final_recommendations,
        "ai_summary": ai_summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "ai_powered": ai_powered,
        "model_used": "gemini" if ai_powered else "nlp",
        "gemini_model": gemini_model_used,
        "relevance_level": relevance_level,
        "score_explanation": score_explanation,
        "meets_threshold": meets_threshold,
        "minimum_match_score": min_score,
        "eligible_to_apply": eligible_to_apply,
        "eligibility_reasons": eligibility_reasons,
        "followup_questions": followup_questions,
        "clarification_questions": followup_questions,
        "applied_weights": {
            "skills": pct_skills,
            "experience": pct_exp,
            "education": pct_edu,
            "certifications": pct_certs,
            "completeness": pct_completeness,
        },
        "weights_source": weights_source,
    }


def nlp_analyze_match(resume_data: dict, job_data: dict, matching_config: Optional[dict] = None) -> dict:
    """
    Wrapper for calculate_match_score that accepts a dictionary for job_data.
    Used by the AI Analysis service to provide purely NLP-based results
    when AI is disabled or removed.
    """
    class MockJob:
        def __init__(self, data: dict):
            self.job_id = data.get("job_id")
            self.job_title = data.get("job_title", "Unknown Role")
            self.department = data.get("department", "")
            self.location = data.get("location", "")
            self.job_type = None
            self.description = data.get("description", "")
            self.skills_requirements = data.get("skills_requirements", "")
            self.experience_requirements = data.get("experience_requirements", "")
            self.education_requirements = data.get("education_requirements", "")
            self.certifications_requirements = data.get("certifications_requirements", "")
            self.scoring_weights = data.get("scoring_weights")
            
        def get(self, key, default=None):
            return getattr(self, key, default)

    mock_job = MockJob(job_data)
    result = calculate_match_score(resume_data, mock_job, use_ai=False, matching_config=matching_config)
    
    # Map the unified output to the format previously expected from Gemini
    return {
        "ai_match_score": result["match_percentage"],
        "ai_skills_score": result["skills_score"],
        "ai_experience_score": result["experience_score"],
        "ai_education_score": result["education_score"],
        "ai_certifications_score": result["certifications_score"],
        "completeness_score": result["completeness_score"],
        "skills_status": result.get("skills_status"),
        "experience_status": result.get("experience_status"),
        "education_status": result.get("education_status"),
        "certifications_status": result.get("certifications_status"),
        "criteria_evaluations": result.get("criteria_evaluations"),
        "required_degree": result.get("required_degree"),
        "candidate_degree": result.get("candidate_degree"),
        "ai_summary": result["ai_summary"],
        "strengths": result["strengths"],
        "weaknesses": result["weaknesses"],
        "recommendations": result["recommendations"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "requirement_evaluations": result["requirement_evaluations"],
        "not_confirmed_skills": result.get("not_confirmed_skills", []),
        "transferable_skills": result["transferable_skills"],
        "skills_reason": result.get("skills_reason"),
        "experience_reason": result.get("experience_reason"),
        "education_reason": result.get("education_reason"),
        "certifications_reason": result.get("certifications_reason"),
        "required_certifications": result.get("required_certifications"),
        "candidate_certifications": result.get("candidate_certifications"),
        "experience_gaps": result.get("experience_gaps"),
        "experience_below_minimum": result.get("experience_below_minimum", False),
        "experience_gap_years": result.get("experience_gap_years", 0),
        "requirement_gaps": result.get("requirement_gaps", []),
        "relevance_level": result["relevance_level"],
        "match_level": result["match_level"],
        "score_explanation": result["score_explanation"],
        "skills_explanation": result["skills_explanation"],
        "experience_explanation": result["experience_explanation"],
        "education_explanation": result["education_explanation"],
        "certification_explanation": result["certification_explanation"],
        "meets_threshold": result.get("meets_threshold", True),
        "minimum_match_score": result.get("minimum_match_score", 30.0),
        "applied_weights": result.get("applied_weights", {}),
    }


def nlp_compare_candidates(job_data: dict, candidates_data: list[dict]) -> dict:
    """
    Compare multiple candidates against a job description using pure NLP.
    Returns rankings and comparative insights without external AI.
    """
    analyzed_candidates = []
    
    for candidate in candidates_data:
        # We reuse the nlp_analyze_match function to get scores and insights for each candidate
        resume_data = candidate.get("resume_data", candidate)
        match_info = nlp_analyze_match(resume_data, job_data)
        
        analyzed_candidates.append({
            "candidate_name": candidate.get("candidate_name", resume_data.get("fullname", "Unknown Candidate")),
            "candidate_id": candidate.get("candidate_id"),
            "match_score": match_info["ai_match_score"],
            "strengths": match_info["strengths"],
            "weaknesses": match_info["weaknesses"],
            "match_level": match_info["match_level"],
            "skills_score": match_info["ai_skills_score"],
            "experience_score": match_info["ai_experience_score"],
            "education_score": match_info["ai_education_score"],
            "certifications_score": match_info.get("ai_certifications_score"),
            "skills_status": match_info.get("skills_status"),
            "experience_status": match_info.get("experience_status"),
            "education_status": match_info.get("education_status"),
            "certifications_status": match_info.get("certifications_status"),
            "education_needs_manual_review": match_info.get("education_status") == STATUS_MANUAL_REVIEW,
            "education_reason": match_info.get("education_reason"),
            "required_degree": match_info.get("required_degree"),
            "candidate_degree": match_info.get("candidate_degree"),
        })
    
    # Sort candidates by match_score descending
    analyzed_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Generate overall summary and comparative insights
    if not analyzed_candidates:
        return {
            "ranked_candidates": [],
            "overall_summary": "No candidates provided for comparison.",
            "comparative_insights": []
        }
        
    top_candidate = analyzed_candidates[0]
    overall_summary = f"Compared {len(analyzed_candidates)} candidate(s) for the '{job_data.get('job_title', 'Unknown')}' position. "
    all_zero = all(c.get("match_score", 0) == 0 for c in analyzed_candidates)

    if all_zero or top_candidate.get("match_score", 0) == 0:
        overall_summary += "None of the candidates meet the requirements for this role (all scored 0% match)."
    elif len(analyzed_candidates) > 1 and top_candidate["match_score"] == analyzed_candidates[1]["match_score"]:
        overall_summary += f"Top candidates {top_candidate['candidate_name']} and {analyzed_candidates[1]['candidate_name']} are tied with an equal {top_candidate['match_score']}% match."
    elif top_candidate["match_score"] >= 75:
        overall_summary += f"The strongest candidate is {top_candidate['candidate_name']} with an exceptional {top_candidate['match_score']}% match, highly aligned with the required skills and experience."
    elif top_candidate["match_score"] >= 50:
        overall_summary += f"The leading candidate is {top_candidate['candidate_name']} with a {top_candidate['match_score']}% match. They meet many requirements but have some gaps."
    else:
        overall_summary += f"The best candidate is {top_candidate['candidate_name']} ({top_candidate['match_score']}% match), though none of the candidates are a strong fit for the role."

    comparative_insights = []
    if len(analyzed_candidates) > 1:
        second_candidate = analyzed_candidates[1]
        score_diff = top_candidate["match_score"] - second_candidate["match_score"]
        if all_zero or (top_candidate.get("match_score", 0) == 0 and second_candidate.get("match_score", 0) == 0):
            comparative_insights.append("All compared candidates currently lack matching skills or experience for this role.")
        elif score_diff == 0:
            comparative_insights.append(f"{top_candidate['candidate_name']} and {second_candidate['candidate_name']} are tied with an equal match score of {top_candidate['match_score']}%.")
        elif score_diff >= 15:
            comparative_insights.append(f"{top_candidate['candidate_name']} is a significantly better match than the others, leading by {score_diff}% over the runner-up.")
        elif score_diff <= 5:
            comparative_insights.append(f"{top_candidate['candidate_name']} and {second_candidate['candidate_name']} are very closely matched, separated by only {score_diff}%.")
            
        # Check skill differences
        if top_candidate.get("skills_score", 0) > 0 and top_candidate.get("skills_score", 0) > second_candidate.get("skills_score", 0) + 10:
            comparative_insights.append(f"{top_candidate['candidate_name']} has a clear advantage in required technical skills.")
        
        # Check experience differences
        if top_candidate.get("experience_score", 0) > 0 and top_candidate.get("experience_score", 0) > second_candidate.get("experience_score", 0) + 10:
            comparative_insights.append(f"{top_candidate['candidate_name']}'s past experience is much more relevant to the role.")

    return {
        "ranked_candidates": analyzed_candidates,
        "overall_summary": overall_summary,
        "comparative_insights": comparative_insights
    }


async def match_resume_to_all_jobs(db, resume_data: dict, use_ai: bool = False) -> list[dict]:
    """
    Match parsed resume data against all active jobs in the database.
    Leverages Celery background tasks to process all jobs in parallel,
    significantly speeding up the NLP analysis process.
    """
    from app.repositories.job_description_repository import JobDescriptionRepository
    from celery import group
    from app.tasks import match_single_job_task
    import asyncio
    
    jobs = await JobDescriptionRepository.get_all_active(db, include_inactive=False)
    
    if not jobs:
        return []
        
    job_dicts = []
    for job in jobs:
        job_dicts.append({
            "job_id": job.job_id,
            "job_title": job.job_title,
            "department": job.department,
            "location": job.location,
            "description": job.description,
            "skills_requirements": job.skills_requirements,
            "experience_requirements": job.experience_requirements,
            "education_requirements": getattr(job, "education_requirements", ""),
            "certifications_requirements": getattr(job, "certifications_requirements", ""),
            "scoring_weights": get_job_scoring_weights(job),
        })
        
    # Fan out to celery workers for parallel processing
    task_group = group([match_single_job_task.s(resume_data, jd, use_ai) for jd in job_dicts])
    
    def _wait_for_group():
        result = task_group.apply_async()
        # Wait up to 30 seconds for all parallel workers to finish their NLP tasks
        return result.get(timeout=30)
        
    try:
        # Offload the blocking wait to a thread so we don't freeze the FastAPI event loop
        matches = await asyncio.to_thread(_wait_for_group)
    except Exception as e:
        logger.error(f"Celery group matching failed or timed out: {e}. Falling back to sequential execution.")
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
        try:
            numeric_id = int(job_id)
            job = await JobDescriptionRepository.get_by_id(db, numeric_id)
        except (ValueError, TypeError):
            pass

    if not job or not getattr(job, "is_active", True):
        return None
    
    return calculate_match_score(resume_data, job, use_ai=use_ai)


import sys
job_matching_service = sys.modules[__name__]
