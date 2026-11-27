"""
AI Analysis Service
-------------------
Orchestrates grounded hybrid NLP/Rule-Based + Google Gemini AI analysis with
seamless automatic fallback and strict ATS guardrails.

Pipeline:
1. Computes deterministic ATS/NLP baseline metrics, thesis criterion weights,
   Philippine credential hierarchy, verified experience tenure, and applicant
   clarification guardrails.
2. When Gemini is enabled, configured, and within daily quota budget, passes a
   compact structured summary of the deterministic NLP audit into `gemini_service`
   (Flash-Lite/Flash with primary-first key failover, SHA-256 caching, and
   thinking_budget=0) for semantic skill discovery, contextual relevance calibration,
   and transparent "why this score?" reasoning.
3. Blends Gemini semantic scores with deterministic ATS guardrails using configured
   `ai_score_weight` / `rule_score_weight` (default balanced 40% Gemini / 60% ATS Rules)
   while strictly honoring NOT_REQUIRED categories, applicant "No" denials, and
   unrelated-experience caps.
4. Falls back gracefully to deterministic NLP results whenever Gemini is disabled,
   budget-capped, rate-limited, or exhausted — without interrupting UX.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_HYBRID_AI_WEIGHT = 0.40
DEFAULT_HYBRID_RULE_WEIGHT = 0.60


def _resolve_blend_weights(matching_config: Optional[Dict[str, Any]] = None) -> Tuple[float, float]:
    """Resolve normalized (ai_weight, rule_weight) from active matching thresholds."""
    thresholds = (matching_config or {}).get("thresholds") or {}
    if not thresholds:
        try:
            from app.services.job_matching_service import get_current_matching_config

            thresholds = (get_current_matching_config() or {}).get("thresholds") or {}
        except Exception:
            thresholds = {}

    if "ai_score_weight" not in thresholds and "rule_score_weight" not in thresholds:
        return DEFAULT_HYBRID_AI_WEIGHT, DEFAULT_HYBRID_RULE_WEIGHT

    try:
        ai_w = float(thresholds.get("ai_score_weight", DEFAULT_HYBRID_AI_WEIGHT))
        rule_w = float(thresholds.get("rule_score_weight", DEFAULT_HYBRID_RULE_WEIGHT))
    except (TypeError, ValueError):
        return DEFAULT_HYBRID_AI_WEIGHT, DEFAULT_HYBRID_RULE_WEIGHT

    ai_w = max(0.0, ai_w)
    rule_w = max(0.0, rule_w)
    total = ai_w + rule_w
    if total <= 0:
        return DEFAULT_HYBRID_AI_WEIGHT, DEFAULT_HYBRID_RULE_WEIGHT
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


def _extract_denied_requirement_keys(requirement_evaluations: Any) -> set[str]:
    denied: set[str] = set()
    if not isinstance(requirement_evaluations, list):
        return denied
    for row in requirement_evaluations:
        if not isinstance(row, dict):
            continue
        if str(row.get("answer") or "").strip().lower() == "no":
            req = str(row.get("requirement") or "").strip().lower()
            if req:
                denied.add(req)
    return denied


def build_deterministic_why_this_score(result: Dict[str, Any]) -> List[str]:
    """
    Build concise, plain-language bullets explaining WHY the match score was reached
    purely from deterministic NLP/ATS evaluation evidence (used as fallback or alongside Gemini).
    """
    reasons: List[str] = []
    matched = result.get("matched_skills") or []
    missing = result.get("missing_skills") or []
    skills_sc = result.get("skills_score", result.get("ai_skills_score"))
    exp_sc = result.get("experience_score", result.get("ai_experience_score"))
    edu_reason = str(result.get("education_reason") or "").strip()
    certs_reason = str(result.get("certifications_reason") or "").strip()
    certs_status = str(result.get("certifications_status") or "").strip()

    if matched:
        sample = ", ".join(str(s) for s in matched[:4])
        extra = f" (+{len(matched) - 4} more)" if len(matched) > 4 else ""
        reasons.append(f"Skills alignment ({round(float(skills_sc or 0))}%): matched {sample}{extra}.")
    elif missing:
        reasons.append(f"Missing core required skills: {', '.join(str(s) for s in missing[:4])}.")

    if missing and matched:
        reasons.append(f"Skill gaps lowering the score: {', '.join(str(s) for s in missing[:4])}.")

    exp_gap = str(result.get("experience_gaps") or "").strip()
    exp_rel = str(result.get("relevance_level") or "").strip()
    if exp_gap:
        reasons.append(exp_gap)
    elif exp_sc is not None:
        exp_reason = str(result.get("experience_reason") or "").strip()
        if exp_reason:
            reasons.append(exp_reason[:180])
        elif exp_rel:
            reasons.append(f"Work experience assessed as {exp_rel.lower()} ({round(float(exp_sc))}%).")

    if edu_reason and len(reasons) < 4:
        reasons.append(edu_reason[:180])

    if certs_reason and certs_status != "Not required" and len(reasons) < 4:
        reasons.append(certs_reason[:180])

    return reasons[:4]


def _merge_gemini_with_nlp_baseline(
    baseline: Dict[str, Any],
    gemini_res: Dict[str, Any],
    matching_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge Gemini semantic insights with deterministic ATS baseline & strict guardrails."""
    from app.services.requirement_rules import (
        STATUS_DOES_NOT_MEET,
        STATUS_NOT_REQUIRED,
        format_criterion_reason,
    )

    ai_w, rule_w = _resolve_blend_weights(matching_config)
    merged = dict(baseline)

    nlp_overall = float(baseline.get("ai_match_score") or 0.0)
    gemini_overall = gemini_res.get("ai_match_score")

    # Blend overall and category scores while preserving NOT_REQUIRED categories
    merged["ai_match_score"] = _blend(nlp_overall, gemini_overall, ai_w, rule_w)

    if baseline.get("skills_status") != STATUS_NOT_REQUIRED:
        merged["ai_skills_score"] = _blend(
            baseline.get("ai_skills_score"), gemini_res.get("ai_skills_score"), ai_w, rule_w
        )
    if baseline.get("experience_status") != STATUS_NOT_REQUIRED:
        blended_exp = _blend(
            baseline.get("ai_experience_score"), gemini_res.get("ai_experience_score"), ai_w, rule_w
        )
        # Strict guardrail: prevent unrelated roles from being inflated to high experience scores
        if (
            baseline.get("experience_status") == STATUS_DOES_NOT_MEET
            and str(baseline.get("relevance_level") or "").lower() == "irrelevant"
            and float(baseline.get("ai_experience_score") or 0.0) <= 10.0
            and str(gemini_res.get("relevance_level") or "").lower() != "highly relevant"
        ):
            blended_exp = min(35.0, blended_exp)
        merged["ai_experience_score"] = blended_exp
    if baseline.get("education_status") != STATUS_NOT_REQUIRED:
        merged["ai_education_score"] = _blend(
            baseline.get("ai_education_score"), gemini_res.get("ai_education_score"), ai_w, rule_w
        )
    if baseline.get("certifications_status") != STATUS_NOT_REQUIRED and gemini_res.get("ai_certifications_score") is not None:
        merged["ai_certifications_score"] = _blend(
            baseline.get("ai_certifications_score"),
            gemini_res.get("ai_certifications_score"),
            ai_w,
            rule_w,
        )

    final_score = merged["ai_match_score"]
    merged["match_level"] = "High Match" if final_score >= 80 else ("Medium Match" if final_score >= 50 else "Low Match")

    # Merge skill lists while respecting explicit applicant "No" denials
    denied_keys = _extract_denied_requirement_keys(baseline.get("requirement_evaluations"))
    gemini_matched_candidates = _merge_unique_lists(
        gemini_res.get("matched_skills") or [],
        gemini_res.get("semantic_matched_skills") or [],
    )
    safe_gemini_matched = [s for s in gemini_matched_candidates if s.strip().lower() not in denied_keys]

    matched = _merge_unique_lists(baseline.get("matched_skills") or [], safe_gemini_matched)
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

    # Enrich qualitative explanations while preserving deterministic status prefixes
    ai_summary = gemini_res.get("ai_summary") or baseline.get("ai_summary") or ""
    exp_gap = baseline.get("experience_gaps")
    if exp_gap and exp_gap not in ai_summary:
        ai_summary = f"{ai_summary} {exp_gap}.".strip()
    merged["ai_summary"] = ai_summary

    why_list = list(gemini_res.get("why_this_score") or [])
    if not why_list:
        why_list = build_deterministic_why_this_score(merged)
    merged["why_this_score"] = why_list

    if gemini_res.get("strengths"):
        merged["strengths"] = gemini_res["strengths"]
    if gemini_res.get("weaknesses"):
        merged["weaknesses"] = gemini_res["weaknesses"]
    if gemini_res.get("recommendations"):
        merged["recommendations"] = gemini_res["recommendations"]

    if gemini_res.get("skills_explanation"):
        merged["skills_explanation"] = gemini_res["skills_explanation"]
        if baseline.get("skills_status"):
            merged["skills_reason"] = format_criterion_reason(
                baseline["skills_status"], gemini_res["skills_explanation"]
            )
    if gemini_res.get("experience_explanation"):
        merged["experience_explanation"] = gemini_res["experience_explanation"]
        if baseline.get("experience_status") and baseline.get("experience_status") != STATUS_NOT_REQUIRED:
            merged["experience_reason"] = format_criterion_reason(
                baseline["experience_status"], gemini_res["experience_explanation"]
            )
    if gemini_res.get("education_explanation"):
        merged["education_explanation"] = gemini_res["education_explanation"]
        if baseline.get("education_status") and baseline.get("education_status") != STATUS_NOT_REQUIRED:
            merged["education_reason"] = format_criterion_reason(
                baseline["education_status"], gemini_res["education_explanation"]
            )
    if gemini_res.get("certification_explanation"):
        merged["certification_explanation"] = gemini_res["certification_explanation"]
        if baseline.get("certifications_status") and baseline.get("certifications_status") != STATUS_NOT_REQUIRED:
            merged["certifications_reason"] = format_criterion_reason(
                baseline["certifications_status"], gemini_res["certification_explanation"]
            )

    merged["nlp_baseline_score"] = round(nlp_overall, 1)
    merged["gemini_semantic_score"] = round(float(gemini_overall), 1) if gemini_overall is not None else None
    merged["score_explanation"] = (
        f"Hybrid ATS Rules ({round(rule_w * 100)}%) + Gemini Semantic AI ({round(ai_w * 100)}%): "
        f"Overall {final_score}% (ATS Rule {round(nlp_overall, 1)}%, "
        f"Gemini Semantic {gemini_res.get('ai_match_score', final_score)}%)"
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
    Perform grounded hybrid job matching analysis using deterministic NLP/ATS rules
    first, then enriching & calibrating with Gemini AI (passing the compact NLP audit
    so Gemini never flies blind). Falls back cleanly to local NLP on exhaustion.
    """
    from app.services.job_matching_service import nlp_analyze_match
    from app.services.gemini_service import gemini_analyze_match, is_gemini_enabled

    baseline = nlp_analyze_match(resume_data, job_data, matching_config=matching_config)

    if is_gemini_enabled():
        logger.info("Attempting grounded Hybrid NLP + Gemini AI match analysis...")
        gemini_result = gemini_analyze_match(resume_data, job_data, nlp_baseline=baseline)
        if gemini_result:
            if baseline:
                return _merge_gemini_with_nlp_baseline(baseline, gemini_result, matching_config=matching_config)
            gemini_result["model_used"] = "gemini"
            gemini_result["ai_powered"] = True
            gemini_result["fallback_used"] = False
            return gemini_result

        logger.warning("Gemini AI match analysis unavailable or exhausted; falling back to local NLP analysis.")
        if baseline:
            baseline["why_this_score"] = baseline.get("why_this_score") or build_deterministic_why_this_score(baseline)
            baseline["model_used"] = "nlp"
            baseline["ai_powered"] = False
            baseline["fallback_used"] = True
            return baseline
        return None

    logger.info("Running local NLP match analysis (Gemini disabled or unconfigured)...")
    if baseline:
        baseline["why_this_score"] = baseline.get("why_this_score") or build_deterministic_why_this_score(baseline)
        baseline["model_used"] = "nlp"
        baseline["ai_powered"] = False
        baseline["fallback_used"] = False
        return baseline

    logger.error("NLP match analysis failed.")
    return None


def compare_candidates_with_fallback(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    """
    Compare multiple candidates for a job using deterministic NLP scorecards first,
    then enriching with a single compact Gemini comparative analysis (grounded in the
    NLP metrics) with automatic fallback to local NLP comparison.
    """
    from app.services.job_matching_service import nlp_compare_candidates
    from app.services.gemini_service import gemini_compare_candidates, is_gemini_enabled

    baseline = nlp_compare_candidates(job_data, candidates_data)

    if is_gemini_enabled() and candidates_data:
        logger.info("Attempting grounded Hybrid NLP + Gemini AI candidate comparison...")
        gemini_result = gemini_compare_candidates(job_data, candidates_data, nlp_baseline=baseline)
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
