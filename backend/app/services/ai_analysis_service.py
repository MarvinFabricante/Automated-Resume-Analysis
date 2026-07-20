import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AIAnalysisService:
    def analyze_match_with_fallback(self, resume_data: dict, job_data: dict) -> Optional[dict]:
        """
        Performs AI-powered job matching analysis using Gemini.
        """
        from app.services.gemini_service import gemini_analyze_match

        logger.info("Attempting AI analysis using primary model (Gemini)...")
        result = gemini_analyze_match(resume_data, job_data)

        if result:
            result["model_used"] = "gemini"
            return result

        logger.error("Primary model (Gemini) failed.")
        return None

    def compare_candidates_with_fallback(self, job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
        """
        Performs candidate comparison using Gemini.
        """
        from app.services.gemini_service import gemini_compare_candidates

        logger.info("Attempting candidate comparison using primary model (Gemini)...")
        result = gemini_compare_candidates(job_data, candidates_data)

        if result:
            result["model_used"] = "gemini"
            return result

        logger.error("Primary model (Gemini) failed for comparison.")
        return None


ai_analysis_service = AIAnalysisService()


def analyze_match_with_fallback(resume_data: dict, job_data: dict) -> Optional[dict]:
    return ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)


def compare_candidates_with_fallback(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    return ai_analysis_service.compare_candidates_with_fallback(job_data, candidates_data)
