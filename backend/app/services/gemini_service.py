"""
Gemini AI Service
-----------------
Provides AI-powered job-match analysis:
  gemini_analyze_match(resume_data, job_data) — semantic job-match scoring

NOTE: Resume extraction (skills, experience, education, certifications) is
handled entirely by rule-based extractors in extractors/content/.
Gemini is used ONLY for the analysis/matching stage to reduce API usage
and prevent hitting request limits.

Uses a rotating pool of API keys to avoid rate-limit exhaustion.
Falls back gracefully if all keys are exhausted or an error occurs.
"""

import os
import json
import re
import time
import logging
from itertools import cycle
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key Rotation Pool
# ---------------------------------------------------------------------------

def _load_api_keys() -> list[str]:
    """Load Gemini API keys from environment variables."""
    raw = ",".join(
        value for value in [
            os.getenv("GEMINI_API_KEYS", ""),
            os.getenv("GEMINI_API_KEY", ""),
        ]
        if value
    )
    keys = []
    for key in [k.strip() for k in raw.split(",") if k.strip()]:
        if key not in keys:
            keys.append(key)
    if not keys:
        logger.warning("GEMINI_API_KEYS/GEMINI_API_KEY not set. Gemini features will be disabled.")
    return keys

_api_keys = _load_api_keys()
_key_cycle = cycle(_api_keys) if _api_keys else None
_current_key_index = 0


def _model_candidates() -> list[str]:
    """
    Prefer a higher-accuracy Gemini model, while keeping Flash as a fallback.
    Override with GEMINI_MODEL or GEMINI_MODELS for deployments with a fixed model.
    """
    raw = os.getenv("GEMINI_MODELS") or os.getenv("GEMINI_MODEL") or "gemini-1.5-pro,gemini-1.5-flash"
    models = []
    for model_name in [m.strip() for m in raw.split(",") if m.strip()]:
        if model_name not in models:
            models.append(model_name)
    return models or ["gemini-1.5-pro", "gemini-1.5-flash"]


def _get_model(model_name: str = "gemini-1.5-flash") -> Optional[genai.GenerativeModel]:
    """
    Get a configured Gemini model using the next key in the rotation pool.
    Returns None if no keys are available.
    """
    global _current_key_index, _key_cycle, _api_keys

    if not _api_keys:
        return None

    # Try each key at most once per call
    for _ in range(len(_api_keys)):
        key = next(_key_cycle)
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            return model
        except Exception as e:
            logger.warning(f"Key rotation: failed to configure key (index {_current_key_index}): {e}")
            _current_key_index = (_current_key_index + 1) % len(_api_keys)

    logger.error("All Gemini API keys failed.")
    return None


def _call_with_retry(prompt: str, max_retries: int = 3, max_output_tokens: int = 4096) -> Optional[str]:
    """
    Call Gemini with automatic key rotation on rate-limit errors.
    Returns the response text or None on failure.
    """
    global _key_cycle, _api_keys

    if not _api_keys:
        return None

    last_error = None
    for model_name in _model_candidates():
        # Try every available key for this model.
        for attempt in range(min(max_retries, len(_api_keys))):
            try:
                model = _get_model(model_name)
                if not model:
                    return None

                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.05,
                        max_output_tokens=max_output_tokens,
                    )
                )
                return response.text

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if any(x in error_str for x in ["quota", "rate", "429", "resource exhausted"]):
                    logger.warning(f"Gemini rate limit on {model_name}, attempt {attempt + 1}; rotating key...")
                    time.sleep(1)
                    continue
                if any(x in error_str for x in ["not found", "not supported", "invalid model"]):
                    logger.warning(f"Gemini model {model_name} unavailable; trying fallback model.")
                    break

                logger.error(f"Gemini API error with {model_name}: {e}")
                return None

    logger.error(f"All Gemini keys exhausted. Last error: {last_error}")
    return None


def _extract_json(text: str) -> Optional[dict]:
    """Extract the first valid JSON object from a Gemini response string."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = text.replace("```", "").strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object within the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# 1. Resume Parsing — DEPRECATED
# ---------------------------------------------------------------------------
# Resume extraction is now handled entirely by rule-based extractors
# (regex, NLP, keyword matching, structured parsing) in the
# extractors/content/ modules. This eliminates Gemini API calls during
# the extraction phase, reducing API usage and preventing rate limits.
#
# Gemini AI is reserved ONLY for analysis/matching (see Section 2 below).
# ---------------------------------------------------------------------------


def gemini_parse_resume(resume_text: str) -> Optional[dict]:
    """
    DEPRECATED — Resume extraction no longer uses Gemini AI.

    All extraction is now performed by rule-based extractors:
      - skills_extractor.py  (4-pass keyword/regex/KB matching)
      - experience_extractor.py  (section + date-range parsing)
      - education_extractor.py  (degree hierarchy + institution matching)
      - certifications_extractor.py  (section + known-cert pattern scan)

    This stub returns None so any legacy callers degrade gracefully.
    """
    logger.info("gemini_parse_resume is DEPRECATED. Using rule-based extraction only.")
    return None


# ---------------------------------------------------------------------------
# 2. Job Match Analysis via Gemini
# ---------------------------------------------------------------------------

MATCH_ANALYSIS_PROMPT = """
You are an expert HR recruiter and ATS (Applicant Tracking System) analyst.

Analyze how well this candidate's resume matches the job description and return a precise evaluation.

Return ONLY a valid JSON object (no extra text, no markdown):
{{
  "ai_match_score": <integer 0-100: overall match percentage>,
  "skills_score": <integer 0-100: how well candidate skills match job requirements>,
  "experience_score": <integer 0-100: how well candidate experience matches requirements>,
  "education_score": <integer 0-100: how well candidate education matches requirements>,
  "matched_skills": ["list", "of", "matched", "skills"],
  "missing_skills": ["list", "of", "critical", "missing", "skills"],
  "strengths": ["2-3 specific strengths relevant to this job"],
  "weaknesses": ["2-3 specific gaps or weaknesses for this job"],
  "recommendations": ["2-3 actionable recommendations to improve candidacy"],
  "ai_summary": "3-4 sentence overall assessment of the candidate for this specific role"
}}

Scoring guidelines:
- Be strict and accurate. A 90+ score means an exceptional match.
- 70-89: Good match with minor gaps.
- 50-69: Partial match with significant gaps.
- Below 50: Poor match.
- Separate required qualifications from preferred/nice-to-have qualifications.
- Consider semantic similarity, equivalent tools, and transferable skills, not just exact keywords.
- Do not award credit for skills or experience that are not supported by the candidate data.
- Penalize missing hard requirements more than missing optional skills.
- Keep matched_skills limited to skills that are relevant to this specific job.
- Keep missing_skills limited to important requirements that would materially affect fit.

CANDIDATE RESUME DATA:
Name: {name}
Skills: {skills}
Years of Experience: {years_exp}
Highest Degree: {degree}
Experience: {experience}

JOB DESCRIPTION:
Title: {job_title}
Department: {department}
Required Skills: {job_skills}
Job Description: {job_desc}
Experience Requirements: {exp_req}
Education Requirements: {edu_req}

Return ONLY the JSON. No markdown, no explanation.
"""


def gemini_analyze_match(resume_data: dict, job_data: dict) -> Optional[dict]:
    """
    Use Gemini to semantically analyze how well a resume matches a job.

    Args:
        resume_data: Parsed resume dict (fullname, skills, years_experience, etc.)
        job_data: Job info dict (job_title, department, description, skills_requirements, etc.)

    Returns:
        A dict with AI scores and insights, or None if the call fails.
    """
    if not _api_keys:
        return None

    try:
        prompt = MATCH_ANALYSIS_PROMPT.format(
            name=resume_data.get("fullname", "Candidate"),
            skills=resume_data.get("skills", "Not specified"),
            years_exp=resume_data.get("years_experience", 0),
            degree=resume_data.get("highest_degree", "Not specified"),
            experience=str(resume_data.get("experience", ""))[:2000],
            job_title=job_data.get("job_title", ""),
            department=job_data.get("department", ""),
            job_skills=job_data.get("skills_requirements", ""),
            job_desc=str(job_data.get("description", ""))[:2000],
            exp_req=job_data.get("experience_requirements", "Not specified"),
            edu_req=job_data.get("education_requirements", "Not specified"),
        )

        raw_response = _call_with_retry(prompt, max_output_tokens=4096)
        if not raw_response:
            return None

        parsed = _extract_json(raw_response)
        if not parsed:
            logger.warning("Gemini match analysis: could not extract JSON from response.")
            return None

        # Normalize
        def clamp(val, lo=0, hi=100):
            try:
                return max(lo, min(hi, int(val or 0)))
            except (TypeError, ValueError):
                return 0

        result = {
            "ai_match_score": clamp(parsed.get("ai_match_score")),
            "ai_skills_score": clamp(parsed.get("skills_score")),
            "ai_experience_score": clamp(parsed.get("experience_score")),
            "ai_education_score": clamp(parsed.get("education_score")),
            "matched_skills": [str(s) for s in (parsed.get("matched_skills") or [])],
            "missing_skills": [str(s) for s in (parsed.get("missing_skills") or [])],
            "strengths": [str(s) for s in (parsed.get("strengths") or [])],
            "weaknesses": [str(s) for s in (parsed.get("weaknesses") or [])],
            "recommendations": [str(s) for s in (parsed.get("recommendations") or [])],
            "ai_summary": str(parsed.get("ai_summary", "")).strip(),
        }

        logger.info(f"Gemini match score for {resume_data.get('fullname')}: {result['ai_match_score']}%")
        return result

    except Exception as e:
        logger.error(f"gemini_analyze_match error: {e}")
        return None
