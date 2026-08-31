"""
NLP Analysis Service
--------------------
Provides NLP-powered job-match analysis WITHOUT any external AI APIs.
All scoring is performed locally using spaCy NLP, keyword matching,
fuzzy matching, and rule-based heuristics.

Replaces the previous Gemini AI-based analysis with a fully local,
deterministic NLP pipeline that maximizes accuracy through comprehensive
keyword matching against job descriptions and requirements.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIAnalysisService:
    def analyze_match_with_fallback(self, resume_data: dict, job_data: dict) -> Optional[dict]:
        """
        Performs NLP-powered job matching analysis using local rule-based
        and keyword matching systems. No external AI API is used.
        """
        from app.services.job_matching_service import nlp_analyze_match

        logger.info("Running NLP-based match analysis (no external AI)...")
        result = nlp_analyze_match(resume_data, job_data)

        if result:
            result["model_used"] = "nlp"
            return result

        logger.error("NLP match analysis failed.")
        return None

    def compare_candidates_with_fallback(self, job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
        """
        Performs candidate comparison using local NLP analysis.
        No external AI API is used.
        """
        from app.services.job_matching_service import nlp_compare_candidates

        logger.info("Running NLP-based candidate comparison (no external AI)...")
        result = nlp_compare_candidates(job_data, candidates_data)

        if result:
            result["model_used"] = "nlp"
            return result

        logger.error("NLP candidate comparison failed.")
        return None


ai_analysis_service = AIAnalysisService()


def analyze_match_with_fallback(resume_data: dict, job_data: dict) -> Optional[dict]:
    return ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)


def compare_candidates_with_fallback(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    return ai_analysis_service.compare_candidates_with_fallback(job_data, candidates_data)
