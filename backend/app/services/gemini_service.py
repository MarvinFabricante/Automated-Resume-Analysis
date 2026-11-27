"""
Gemini AI Service
-----------------
Domain-level integration with Google Gemini for semantic resume-to-job match
analysis and multi-candidate comparison.

NOTE: Resume extraction (skills, experience, education, certifications) remains
fully deterministic in `app/extractors/` to minimize API latency and quota usage.
Gemini is invoked for semantic matching analysis and candidate comparison,
backed by `GeminiClient` + `GeminiKeyManager` (primary-first API key failover,
exponential backoff, cooldowns, project-level quota awareness, and thread safety).

All errors (including full key pool exhaustion) degrade gracefully by returning
`None` so callers fall back seamlessly to the local deterministic NLP engine.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

from app.utils.gemini_client import (
    GeminiAllKeysExhaustedError,
    GeminiConfigurationError,
    GeminiError,
    get_gemini_client,
)

logger = logging.getLogger(__name__)


def is_gemini_enabled() -> bool:
    """Return True when Gemini integration is enabled via env and at least one key is loaded."""
    flag = os.getenv("GEMINI_ENABLED", "true").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    client = get_gemini_client()
    client.refresh_keys_if_env_changed()
    return client.is_available


def get_gemini_status() -> Dict[str, Any]:
    """Return non-sensitive Gemini integration and API key pool status metrics."""
    client = get_gemini_client()
    status = client.get_status()
    flag = os.getenv("GEMINI_ENABLED", "true").strip().lower()
    enabled_flag = flag not in {"0", "false", "no", "off"}
    status["enabled"] = bool(enabled_flag and status.get("configured"))
    status["enabled_flag"] = enabled_flag
    return status


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse the first valid JSON object from a Gemini text response."""
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _clamp_score(value: Any, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(lo, min(hi, num)), 1)


def _clean_str_list(values: Any, max_items: int = 12) -> List[str]:
    if not isinstance(values, list):
        return []
    result: List[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
            if len(result) >= max_items:
                break
    return result


MATCH_ANALYSIS_SYSTEM_INSTRUCTION = (
    "You are an expert ATS (Applicant Tracking System) analyst and HR technical evaluator. "
    "Evaluate candidate-job alignment strictly, objectively, and transparently. "
    "Never inflate work experience scores for roles unrelated to the target position. "
    "Always return strictly valid JSON matching the requested schema with no markdown or commentary."
)

MATCH_ANALYSIS_PROMPT = """Evaluate how well this candidate matches the target job position across skills, work experience relevance, education, and certifications.

STRICT EVALUATION RULES:
1. Evaluate work experience RELEVANCE strictly: unrelated jobs must receive a low experience score regardless of total years worked.
2. Acknowledge transferable skills honestly, but transferable skills alone must NOT yield a high work experience score.
3. If the job specifies no requirement for a category (e.g., "None" or "Not specified"), score that category fairly without penalizing the candidate.
4. Provide concise, actionable, HR-facing explanations, strengths, weaknesses, and interview recommendations.
5. Match levels: High Match (80-100), Medium Match (50-79), Low Match (0-49).

Return ONLY a valid JSON object with this exact schema:
{{
  "ai_match_score": <number 0-100>,
  "match_level": "<High Match | Medium Match | Low Match>",
  "skills_score": <number 0-100>,
  "skills_explanation": "<concise explanation of matched and missing skills>",
  "experience_score": <number 0-100>,
  "experience_explanation": "<concise breakdown of role relevance and tenure alignment>",
  "relevance_level": "<Highly Relevant | Partially Relevant | Irrelevant>",
  "transferable_skills": ["skill1", "skill2"],
  "education_score": <number 0-100>,
  "education_explanation": "<concise explanation of education alignment>",
  "certifications_score": <number 0-100>,
  "certification_explanation": "<concise explanation of certifications alignment>",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["gap 1", "gap 2"],
  "ai_summary": "<2-3 sentence executive summary for HR>",
  "matched_skills": ["matched skill 1"],
  "missing_skills": ["missing skill 1"],
  "recommendations": ["HR screening or interview recommendation 1"]
}}

TARGET JOB:
- Title: {job_title}
- Department: {department}
- Description: {job_desc}
- Required Skills: {job_skills}
- Experience Requirements: {exp_req}
- Education Requirements: {edu_req}
- Certifications Requirements: {cert_req}

CANDIDATE PROFILE:
- Name: {name}
- Skills: {skills}
- Years of Experience: {years_exp}
- Education / Highest Degree: {education}
- Certifications: {certifications}
- Work Experience: {experience}
"""


CANDIDATE_COMPARISON_SYSTEM_INSTRUCTION = (
    "You are an expert HR recruitment analyst comparing multiple candidates for a single role. "
    "Rank candidates strictly by job fit using their skills, relevant experience, education, and certifications. "
    "Always return strictly valid JSON matching the requested schema."
)

CANDIDATE_COMPARISON_PROMPT = """Compare the following candidates for the target job opening and rank them from strongest to weakest fit.

Return ONLY a valid JSON object with this exact schema:
{{
  "rankings": [
    {{
      "rank": 1,
      "candidate_name": "<exact candidate name>",
      "match_score": <number 0-100>,
      "score_breakdown_explanation": "<concise breakdown of why this score was assigned>",
      "reasoning": "<why this candidate ranks here compared to others>",
      "key_differentiator": "<primary factor distinguishing this candidate>"
    }}
  ],
  "overall_summary": "<2-4 sentence executive comparison summary stating who is strongest and why>",
  "comparative_insights": ["insight 1", "insight 2", "insight 3"]
}}

TARGET JOB:
- Title: {job_title}
- Department: {department}
- Required Skills: {job_skills}
- Description: {job_desc}
- Experience Requirements: {exp_req}
- Education Requirements: {edu_req}
- Certifications Requirements: {cert_req}

CANDIDATES:
{candidates_text}
"""


def _format_skills_text(raw_skills: Any) -> str:
    if isinstance(raw_skills, list):
        return ", ".join(str(s).strip() for s in raw_skills if str(s).strip()) or "Not specified"
    return str(raw_skills or "").strip() or "Not specified"


def _format_experience_text(resume_data: Dict[str, Any]) -> str:
    exp = resume_data.get("experience")
    if isinstance(exp, str) and exp.strip():
        return exp.strip()[:2500]
    work_exps = resume_data.get("work_experiences")
    if isinstance(work_exps, list) and work_exps:
        lines: List[str] = []
        for entry in work_exps[:8]:
            if isinstance(entry, dict):
                title = entry.get("job_title") or entry.get("title") or ""
                company = entry.get("company") or ""
                duration = entry.get("duration") or entry.get("dates") or ""
                resp = entry.get("responsibilities") or entry.get("description") or ""
                if isinstance(resp, list):
                    resp = "; ".join(str(r) for r in resp[:4])
                parts = [p for p in [f"{title} at {company}".strip(" at"), duration, str(resp)[:300]] if p]
                if parts:
                    lines.append(" | ".join(parts))
            elif entry:
                lines.append(str(entry))
        if lines:
            return "\n".join(lines)[:2500]
    return "Not specified"


def _build_match_prompt(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
    education = (
        resume_data.get("education")
        or resume_data.get("highest_educational_attainment")
        or resume_data.get("highest_degree")
        or resume_data.get("degree")
        or "Not specified"
    )
    certifications = (
        resume_data.get("certifications")
        or resume_data.get("candidate_certifications")
        or "None"
    )
    if isinstance(certifications, list):
        certifications = ", ".join(str(c) for c in certifications if c) or "None"

    return MATCH_ANALYSIS_PROMPT.format(
        name=resume_data.get("fullname") or resume_data.get("candidate_name") or "Candidate",
        skills=_format_skills_text(resume_data.get("skills") or resume_data.get("skills_list")),
        years_exp=resume_data.get("years_experience", 0) or 0,
        education=str(education)[:800],
        certifications=str(certifications)[:600],
        experience=_format_experience_text(resume_data),
        job_title=job_data.get("job_title", ""),
        department=job_data.get("department", ""),
        job_desc=str(job_data.get("description", ""))[:2000],
        job_skills=str(job_data.get("skills_requirements") or job_data.get("skills") or "Not specified")[:1000],
        exp_req=str(job_data.get("experience_requirements") or job_data.get("experience_level") or "Not specified")[:500],
        edu_req=str(job_data.get("education_requirements") or job_data.get("education") or "Not specified")[:500],
        cert_req=str(job_data.get("certifications_requirements") or "None")[:500],
    )


def _normalize_match_result(parsed: Dict[str, Any], model_name: str, key_label: str) -> Dict[str, Any]:
    match_score = _clamp_score(parsed.get("ai_match_score"))
    match_level = str(parsed.get("match_level") or "").strip()
    if match_level not in ("High Match", "Medium Match", "Low Match"):
        match_level = "High Match" if match_score >= 80 else ("Medium Match" if match_score >= 50 else "Low Match")

    raw_cert_score = parsed.get("certifications_score")
    if raw_cert_score is None:
        raw_cert_score = parsed.get("certification_score")

    return {
        "ai_match_score": match_score,
        "match_level": match_level,
        "ai_skills_score": _clamp_score(parsed.get("skills_score")),
        "skills_explanation": str(parsed.get("skills_explanation") or "").strip(),
        "ai_experience_score": _clamp_score(parsed.get("experience_score")),
        "experience_explanation": str(parsed.get("experience_explanation") or "").strip(),
        "relevance_level": str(parsed.get("relevance_level") or "Unknown").strip(),
        "transferable_skills": _clean_str_list(parsed.get("transferable_skills"), max_items=8),
        "ai_education_score": _clamp_score(parsed.get("education_score")),
        "education_explanation": str(parsed.get("education_explanation") or "").strip(),
        "ai_certifications_score": _clamp_score(raw_cert_score) if raw_cert_score is not None else None,
        "certification_explanation": str(parsed.get("certification_explanation") or "").strip(),
        "strengths": _clean_str_list(parsed.get("strengths"), max_items=6),
        "weaknesses": _clean_str_list(parsed.get("weaknesses"), max_items=6),
        "ai_summary": str(parsed.get("ai_summary") or "").strip(),
        "matched_skills": _clean_str_list(parsed.get("matched_skills"), max_items=25),
        "missing_skills": _clean_str_list(parsed.get("missing_skills"), max_items=25),
        "recommendations": _clean_str_list(parsed.get("recommendations"), max_items=6),
        "model_used": "gemini",
        "gemini_model": model_name,
        "gemini_key_label": key_label,
        "ai_powered": True,
    }


def gemini_analyze_match(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Synchronously analyze candidate-job alignment using Gemini with automatic key rotation
    and failover. Returns None on unavailability or exhaustion so callers fall back to NLP.
    """
    if not is_gemini_enabled():
        return None

    try:
        prompt = _build_match_prompt(resume_data, job_data)
        client = get_gemini_client()
        response = client.generate_content(
            prompt,
            system_instruction=MATCH_ANALYSIS_SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=2048,
            response_mime_type="application/json",
            operation_name="match_analysis",
        )
        parsed = _extract_json(response.text)
        if not parsed:
            logger.warning("[GeminiService] Match analysis response did not contain valid JSON.")
            return None

        result = _normalize_match_result(parsed, response.model, response.key_label)
        logger.info(
            "[GeminiService] Match analysis succeeded (model=%s, key=%s, score=%.1f%%, attempts=%d, rotations=%d)",
            response.model,
            response.key_label,
            result["ai_match_score"],
            response.attempts,
            response.rotations,
        )
        return result

    except GeminiAllKeysExhaustedError as exc:
        logger.warning("[GeminiService] Match analysis unavailable (all keys exhausted): %s", exc)
        return None
    except GeminiConfigurationError as exc:
        logger.info("[GeminiService] Match analysis skipped: %s", exc)
        return None
    except GeminiError as exc:
        logger.warning("[GeminiService] Match analysis failed (%s): %s", exc.error_code or "ERROR", exc)
        return None
    except Exception as exc:
        logger.error("[GeminiService] Unexpected error in gemini_analyze_match: %s", get_gemini_client().key_manager.sanitize(exc))
        return None


async def async_gemini_analyze_match(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Async counterpart to `gemini_analyze_match` for non-blocking FastAPI routes."""
    if not is_gemini_enabled():
        return None

    try:
        prompt = _build_match_prompt(resume_data, job_data)
        client = get_gemini_client()
        response = await client.agenerate_content(
            prompt,
            system_instruction=MATCH_ANALYSIS_SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=2048,
            response_mime_type="application/json",
            operation_name="match_analysis",
        )
        parsed = _extract_json(response.text)
        if not parsed:
            logger.warning("[GeminiService] Async match analysis response did not contain valid JSON.")
            return None

        return _normalize_match_result(parsed, response.model, response.key_label)

    except GeminiAllKeysExhaustedError as exc:
        logger.warning("[GeminiService] Async match analysis unavailable (all keys exhausted): %s", exc)
        return None
    except GeminiConfigurationError as exc:
        logger.info("[GeminiService] Async match analysis skipped: %s", exc)
        return None
    except GeminiError as exc:
        logger.warning("[GeminiService] Async match analysis failed (%s): %s", exc.error_code or "ERROR", exc)
        return None
    except Exception as exc:
        logger.error("[GeminiService] Unexpected error in async_gemini_analyze_match: %s", get_gemini_client().key_manager.sanitize(exc))
        return None


def _build_comparison_prompt(job_data: Dict[str, Any], candidates_data: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for idx, cand in enumerate(candidates_data[:15], start=1):
        resume = cand.get("resume_data", cand) if isinstance(cand, dict) else {}
        name = cand.get("candidate_name") or resume.get("fullname") or f"Candidate {idx}"
        skills = _format_skills_text(cand.get("skills") or resume.get("skills") or resume.get("skills_list"))
        years = resume.get("years_experience", cand.get("years_experience", 0)) or 0
        degree = (
            resume.get("highest_degree")
            or resume.get("highest_educational_attainment")
            or resume.get("education")
            or "Not specified"
        )
        exp = _format_experience_text(resume)[:900]
        blocks.append(
            f"--- Candidate {idx} ---\n"
            f"Name: {name}\n"
            f"Skills: {skills}\n"
            f"Years Experience: {years}\n"
            f"Education: {degree}\n"
            f"Experience Summary: {exp}\n"
        )

    return CANDIDATE_COMPARISON_PROMPT.format(
        job_title=job_data.get("job_title", ""),
        department=job_data.get("department", ""),
        job_skills=str(job_data.get("skills_requirements") or job_data.get("skills") or "Not specified")[:1000],
        job_desc=str(job_data.get("description", ""))[:2000],
        exp_req=str(job_data.get("experience_requirements") or job_data.get("experience_level") or "Not specified")[:500],
        edu_req=str(job_data.get("education_requirements") or job_data.get("education") or "Not specified")[:500],
        cert_req=str(job_data.get("certifications_requirements") or "None")[:500],
        candidates_text="\n".join(blocks),
    )


def _normalize_comparison_result(parsed: Dict[str, Any], model_name: str, key_label: str) -> Optional[Dict[str, Any]]:
    raw_rankings = parsed.get("rankings") or parsed.get("ranked_candidates")
    if not isinstance(raw_rankings, list) or not raw_rankings:
        return None

    normalized_rankings: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_rankings, start=1):
        if not isinstance(item, dict):
            continue
        score = _clamp_score(item.get("match_score"))
        normalized_rankings.append(
            {
                "rank": int(item.get("rank") or idx),
                "candidate_name": str(item.get("candidate_name") or f"Candidate {idx}").strip(),
                "match_score": score,
                "score_breakdown_explanation": str(item.get("score_breakdown_explanation") or "").strip(),
                "reasoning": str(item.get("reasoning") or "").strip(),
                "key_differentiator": str(item.get("key_differentiator") or "").strip(),
            }
        )

    if not normalized_rankings:
        return None

    overall_summary = str(parsed.get("overall_summary") or parsed.get("comparison_summary") or "").strip()
    insights = _clean_str_list(parsed.get("comparative_insights"), max_items=6)

    return {
        "rankings": normalized_rankings,
        "ranked_candidates": normalized_rankings,
        "overall_summary": overall_summary,
        "comparison_summary": overall_summary,
        "comparative_insights": insights,
        "model_used": "gemini",
        "gemini_model": model_name,
        "gemini_key_label": key_label,
        "ai_powered": True,
    }


def gemini_compare_candidates(job_data: Dict[str, Any], candidates_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Synchronously compare multiple candidates using Gemini with automatic key rotation
    and failover. Returns None on unavailability so callers fall back to NLP comparison.
    """
    if not is_gemini_enabled() or not candidates_data:
        return None

    try:
        prompt = _build_comparison_prompt(job_data, candidates_data)
        client = get_gemini_client()
        response = client.generate_content(
            prompt,
            system_instruction=CANDIDATE_COMPARISON_SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=3072,
            response_mime_type="application/json",
            operation_name="candidate_comparison",
        )
        parsed = _extract_json(response.text)
        if not parsed:
            logger.warning("[GeminiService] Candidate comparison response did not contain valid JSON.")
            return None

        result = _normalize_comparison_result(parsed, response.model, response.key_label)
        if not result:
            logger.warning("[GeminiService] Candidate comparison JSON missing rankings.")
            return None

        logger.info(
            "[GeminiService] Candidate comparison succeeded for %d candidate(s) (model=%s, key=%s, attempts=%d, rotations=%d)",
            len(candidates_data),
            response.model,
            response.key_label,
            response.attempts,
            response.rotations,
        )
        return result

    except GeminiAllKeysExhaustedError as exc:
        logger.warning("[GeminiService] Candidate comparison unavailable (all keys exhausted): %s", exc)
        return None
    except GeminiConfigurationError as exc:
        logger.info("[GeminiService] Candidate comparison skipped: %s", exc)
        return None
    except GeminiError as exc:
        logger.warning("[GeminiService] Candidate comparison failed (%s): %s", exc.error_code or "ERROR", exc)
        return None
    except Exception as exc:
        logger.error("[GeminiService] Unexpected error in gemini_compare_candidates: %s", get_gemini_client().key_manager.sanitize(exc))
        return None


async def async_gemini_compare_candidates(
    job_data: Dict[str, Any],
    candidates_data: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Async counterpart to `gemini_compare_candidates` for non-blocking FastAPI routes."""
    if not is_gemini_enabled() or not candidates_data:
        return None

    try:
        prompt = _build_comparison_prompt(job_data, candidates_data)
        client = get_gemini_client()
        response = await client.agenerate_content(
            prompt,
            system_instruction=CANDIDATE_COMPARISON_SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=3072,
            response_mime_type="application/json",
            operation_name="candidate_comparison",
        )
        parsed = _extract_json(response.text)
        if not parsed:
            return None
        return _normalize_comparison_result(parsed, response.model, response.key_label)

    except GeminiAllKeysExhaustedError as exc:
        logger.warning("[GeminiService] Async candidate comparison unavailable (all keys exhausted): %s", exc)
        return None
    except GeminiConfigurationError as exc:
        logger.info("[GeminiService] Async candidate comparison skipped: %s", exc)
        return None
    except GeminiError as exc:
        logger.warning("[GeminiService] Async candidate comparison failed (%s): %s", exc.error_code or "ERROR", exc)
        return None
    except Exception as exc:
        logger.error("[GeminiService] Unexpected error in async_gemini_compare_candidates: %s", get_gemini_client().key_manager.sanitize(exc))
        return None


gemini_service = sys.modules[__name__]
