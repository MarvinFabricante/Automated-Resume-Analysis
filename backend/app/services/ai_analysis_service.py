"""
AI Analysis Service
-------------------
Orchestrates hybrid Gemini AI + deterministic local NLP analysis with seamless
automatic fallback.

Pipeline:
1. Computes deterministic ATS/NLP baseline metrics & strict requirement guardrails.
2. When Gemini is enabled and configured, invokes `gemini_service` (backed by
   primary-first API key failover, exponential backoff, cooldowns, and concurrency
   controls) for semantic scoring and narrative insights.
3. Blends Gemini semantic scores with deterministic ATS guardrails using configured
   `ai_score_weight` / `rule_score_weight` thresholds while preserving structured
   requirement evaluations.
4. Falls back gracefully to deterministic NLP results whenever all Gemini keys are
   unavailable, rate-limited, exhausted, or unconfigured — without interrupting UX.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _resolve_blend_weights(matching_config: Optional[Dict[str, Any]] = None) -> Tuple[float, float]:
    """Resolve normalized (ai_weight, rule_weight) from active matching thresholds."""
    thresholds = (matching_config or {}).get("thresholds") or {}
    if not thresholds:
        try:
            from app.services.job_matching_service import get_current_matching_config

            thresholds = (get_current_matching_config() or {}).get("thresholds") or {}
        except Exception:
            thresholds = {}

    try:
        ai_w = float(thresholds.get("ai_score_weight", 0.8))
        rule_w = float(thresholds.get("rule_score_weight", 0.2))
    except (TypeError, ValueError):
        return 0.8, 0.2

    ai_w = max(0.0, ai_w)
    rule_w = max(0.0, rule_w)
    total = ai_w + rule_w
    if total <= 0:
        return 0.8, 0.2
    return ai_w / total, rule_w / total


def _blend(rule_val: Optional[float], ai_val: Optional[float], ai_w: float, rule_w: float) -> float:
    r = float(rule_val or 0.0)
    if ai_val is None:
        return round(r, 1)
    a = float(ai_val)
    return round(max(0.0, min(100.0, r * rule_w + a * ai_w)), 1)


def _merge_unique_lists(primary: List[str], secondary: List[str]) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()
    for item in list(primary or []) + list(secondary or []):
        cleaned = str(item).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            merged.append(cleaned)
    return merged


def _merge_gemini_with_nlp_baseline(
    baseline: Dict[str, Any],
    gemini_res: Dict[str, Any],
    matching_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge Gemini semantic insights with deterministic ATS baseline & guardrails."""
    from app.services.requirement_rules import STATUS_NOT_REQUIRED

    ai_w, rule_w = _resolve_blend_weights(matching_config)
    merged = dict(baseline)

    # Blend overall and category scores while preserving NOT_REQUIRED categories
    merged["ai_match_score"] = _blend(baseline.get("ai_match_score"), gemini_res.get("ai_match_score"), ai_w, rule_w)

    if baseline.get("skills_status") != STATUS_NOT_REQUIRED:
        merged["ai_skills_score"] = _blend(baseline.get("ai_skills_score"), gemini_res.get("ai_skills_score"), ai_w, rule_w)
    if baseline.get("experience_status") != STATUS_NOT_REQUIRED:
        merged["ai_experience_score"] = _blend(baseline.get("ai_experience_score"), gemini_res.get("ai_experience_score"), ai_w, rule_w)
    if baseline.get("education_status") != STATUS_NOT_REQUIRED:
        merged["ai_education_score"] = _blend(baseline.get("ai_education_score"), gemini_res.get("ai_education_score"), ai_w, rule_w)
    if baseline.get("certifications_status") != STATUS_NOT_REQUIRED and gemini_res.get("ai_certifications_score") is not None:
        merged["ai_certifications_score"] = _blend(
            baseline.get("ai_certifications_score"),
            gemini_res.get("ai_certifications_score"),
            ai_w,
            rule_w,
        )

    final_score = merged["ai_match_score"]
    merged["match_level"] = "High Match" if final_score >= 80 else ("Medium Match" if final_score >= 50 else "Low Match")

    # Merge skill lists (preferring deterministic confirmed matches + semantic discoveries)
    matched = _merge_unique_lists(baseline.get("matched_skills") or [], gemini_res.get("matched_skills") or [])
    matched_lower = {s.lower() for s in matched}
    missing = [
        s for s in _merge_unique_lists(baseline.get("missing_skills") or [], gemini_res.get("missing_skills") or [])
        if s.lower() not in matched_lower
    ]
    merged["matched_skills"] = matched
    merged["missing_skills"] = missing
    merged["transferable_skills"] = _merge_unique_lists(
        baseline.get("transferable_skills") or [],
        gemini_res.get("transferable_skills") or [],
    )

    # Enrich qualitative explanations while retaining deterministic fallback text
    ai_summary = gemini_res.get("ai_summary") or baseline.get("ai_summary") or ""
    exp_gap = baseline.get("experience_gaps")
    if exp_gap and exp_gap not in ai_summary:
        ai_summary = f"{ai_summary} {exp_gap}.".strip()
    merged["ai_summary"] = ai_summary

    if gemini_res.get("strengths"):
        merged["strengths"] = gemini_res["strengths"]
    if gemini_res.get("weaknesses"):
        merged["weaknesses"] = gemini_res["weaknesses"]
    if gemini_res.get("recommendations"):
        merged["recommendations"] = gemini_res["recommendations"]
    if gemini_res.get("skills_explanation"):
        merged["skills_explanation"] = gemini_res["skills_explanation"]
    if gemini_res.get("experience_explanation"):
        merged["experience_explanation"] = gemini_res["experience_explanation"]
    if gemini_res.get("education_explanation"):
        merged["education_explanation"] = gemini_res["education_explanation"]
    if gemini_res.get("certification_explanation"):
        merged["certification_explanation"] = gemini_res["certification_explanation"]

    merged["score_explanation"] = (
        f"Gemini AI ({round(ai_w * 100)}%) + ATS Rule Validation ({round(rule_w * 100)}%): "
        f"Overall {final_score}% (Gemini Semantic {gemini_res.get('ai_match_score', final_score)}%, "
        f"ATS Rule {baseline.get('ai_match_score', final_score)}%)"
    )
    merged["model_used"] = "gemini"
    merged["gemini_model"] = gemini_res.get("gemini_model")
    merged["ai_powered"] = True
    merged["fallback_used"] = False
    return merged


def analyze_match_with_fallback(
    resume_data: dict,
    job_data: dict,
    matching_config: Optional[dict] = None,
) -> Optional[dict]:
    """
    Perform job matching analysis using Gemini AI as primary semantic analyzer
    with automatic, graceful fallback to local deterministic NLP analysis.
    """
    from app.services.job_matching_service import nlp_analyze_match
    from app.services.gemini_service import gemini_analyze_match, is_gemini_enabled

    baseline = nlp_analyze_match(resume_data, job_data, matching_config=matching_config)

    if is_gemini_enabled():
        logger.info("Attempting Gemini AI match analysis (with automatic key failover and NLP fallback)...")
        gemini_result = gemini_analyze_match(resume_data, job_data)
        if gemini_result:
            if baseline:
                return _merge_gemini_with_nlp_baseline(baseline, gemini_result, matching_config=matching_config)
            gemini_result["model_used"] = "gemini"
            gemini_result["ai_powered"] = True
            gemini_result["fallback_used"] = False
            return gemini_result

        logger.warning("Gemini AI match analysis unavailable or exhausted; falling back to local NLP analysis.")
        if baseline:
            baseline["model_used"] = "nlp"
            baseline["ai_powered"] = False
            baseline["fallback_used"] = True
            return baseline
        return None

    logger.info("Running local NLP match analysis (Gemini disabled or unconfigured)...")
    if baseline:
        baseline["model_used"] = "nlp"
        baseline["ai_powered"] = False
        baseline["fallback_used"] = False
        return baseline

    logger.error("NLP match analysis failed.")
    return None


def compare_candidates_with_fallback(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    """
    Compare multiple candidates for a job using Gemini AI as primary semantic ranker
    with automatic fallback to local deterministic NLP comparison.
    """
    from app.services.job_matching_service import nlp_compare_candidates
    from app.services.gemini_service import gemini_compare_candidates, is_gemini_enabled

    baseline = nlp_compare_candidates(job_data, candidates_data)

    if is_gemini_enabled() and candidates_data:
        logger.info("Attempting Gemini AI candidate comparison (with automatic key failover and NLP fallback)...")
        gemini_result = gemini_compare_candidates(job_data, candidates_data)
        if gemini_result:
            if baseline:
                # Merge deterministic candidate telemetry into Gemini rankings where names match
                baseline_by_name = {
                    str(c.get("candidate_name") or "").strip().lower(): c
                    for c in (baseline.get("ranked_candidates") or [])
                }
                enriched_ranked: List[Dict[str, Any]] = []
                for item in gemini_result.get("ranked_candidates") or []:
                    name_key = str(item.get("candidate_name") or "").strip().lower()
                    base_cand = baseline_by_name.get(name_key)
                    if base_cand:
                        merged_cand = {**base_cand, **item}
                    else:
                        merged_cand = dict(item)
                    enriched_ranked.append(merged_cand)

                return {
                    **baseline,
                    **gemini_result,
                    "ranked_candidates": enriched_ranked or baseline.get("ranked_candidates", []),
                    "overall_summary": gemini_result.get("overall_summary") or baseline.get("overall_summary", ""),
                    "comparative_insights": gemini_result.get("comparative_insights") or baseline.get("comparative_insights", []),
                    "model_used": "gemini",
                    "ai_powered": True,
                    "fallback_used": False,
                }

            gemini_result["model_used"] = "gemini"
            gemini_result["ai_powered"] = True
            gemini_result["fallback_used"] = False
            return gemini_result

        logger.warning("Gemini AI candidate comparison unavailable or exhausted; falling back to local NLP comparison.")
        if baseline:
            baseline["model_used"] = "nlp"
            baseline["ai_powered"] = False
            baseline["fallback_used"] = True
            return baseline
        return None

    logger.info("Running local NLP candidate comparison (Gemini disabled or unconfigured)...")
    if baseline:
        baseline["model_used"] = "nlp"
        baseline["ai_powered"] = False
        baseline["fallback_used"] = False
        return baseline

    logger.error("NLP candidate comparison failed.")
    return None


ai_analysis_service = sys.modules[__name__]
