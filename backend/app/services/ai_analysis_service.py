import logging
from typing import Optional

logger = logging.getLogger(__name__)

def analyze_match_with_fallback(resume_data: dict, job_data: dict) -> Optional[dict]:
    """
    Performs AI-powered job matching analysis.
    Uses local Llama 3 8B as the primary engine.
    Falls back to Gemini API if the local LLM fails or produces invalid output.
    """
    from app.services.llama_service import llama_analyze_match
    from app.services.gemini_service import gemini_analyze_match
    
    logger.info("Attempting AI analysis using primary model (Llama 3 8B)...")
    result = llama_analyze_match(resume_data, job_data)
    
    if result:
        result["model_used"] = "llama3"
        return result
        
    logger.warning("Primary model (Llama 3 8B) failed or returned invalid output. Falling back to Gemini API...")
    result = gemini_analyze_match(resume_data, job_data)
    
    if result:
        result["model_used"] = "gemini"
        return result
        
    logger.error("Both primary (Llama) and fallback (Gemini) models failed.")
    return None

def compare_candidates_with_fallback(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    """
    Performs candidate comparison using Llama 3, with Gemini fallback.
    """
    from app.services.llama_service import llama_compare_candidates
    # We will implement gemini_compare_candidates if needed, or just use Llama for now.
    
    logger.info("Attempting candidate comparison using primary model (Llama 3 8B)...")
    result = llama_compare_candidates(job_data, candidates_data)
    
    if result:
        result["model_used"] = "llama3"
        return result
        
    logger.warning("Primary model (Llama 3 8B) failed for comparison. Fallback to Gemini not fully implemented for comparison, returning None.")
    return None
