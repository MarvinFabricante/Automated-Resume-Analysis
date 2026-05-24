import os
import json
import logging
import requests
from typing import Optional
from app.services.gemini_service import MATCH_ANALYSIS_PROMPT, _extract_json

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama3")

def llama_analyze_match(resume_data: dict, job_data: dict) -> Optional[dict]:
    """
    Use local Llama 3 to semantically analyze how well a resume matches a job.
    Returns a dict with AI scores and insights, or None if the call fails.
    """
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

        payload = {
            "model": LLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.05,
                "num_predict": 2048
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        result_json = response.json()
        raw_response = result_json.get("response", "")
        
        parsed = _extract_json(raw_response)
        if not parsed:
            logger.warning("Llama match analysis: could not extract JSON from response.")
            return None

        # Normalize
        def clamp(val, lo=0, hi=100):
            try:
                return max(lo, min(hi, int(float(val or 0))))
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

        logger.info(f"Llama 3 match score for {resume_data.get('fullname')}: {result['ai_match_score']}%")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Llama 3 API connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"llama_analyze_match error: {e}")
        return None

CANDIDATE_COMPARISON_PROMPT = """
You are an expert HR recruiter and ATS (Applicant Tracking System) analyst.

Analyze and perform a deep, detailed comparison of these candidates for the following job description.
Your goal is to identify the most qualified candidate based on job fit and clearly explain all scoring and ranking decisions.

Return ONLY a valid JSON object (no extra text, no markdown):
{{
  "rankings": [
    {{
      "rank": 1,
      "candidate_name": "Name of the candidate",
      "match_score": <integer 0-100>,
      "score_breakdown_explanation": "Explain exactly how this candidate achieved this final percentage score based on their specific skills, experience, and education matching the job requirements.",
      "reasoning": "Detailed explanation of why they are ranked here. Explain why they are better (or worse) than the others based on job requirements.",
      "key_differentiator": "The primary reason this candidate stands out compared to the rest."
    }}
  ],
  "comparison_summary": "A comprehensive summary comparing the candidates. Explain the reasoning behind score differences between candidates, and definitively state why the top candidate is the most qualified for the job."
}}

JOB DESCRIPTION:
Title: {job_title}
Department: {department}
Required Skills: {job_skills}
Job Description: {job_desc}
Experience Requirements: {exp_req}
Education Requirements: {edu_req}

CANDIDATES DATA:
{candidates_text}

Return ONLY the JSON. No markdown, no explanation.
"""

def llama_compare_candidates(job_data: dict, candidates_data: list[dict]) -> Optional[dict]:
    """
    Use local Llama 3 to compare multiple candidates for a specific job.
    """
    try:
        candidates_text = ""
        for i, cand in enumerate(candidates_data):
            candidates_text += f"\n--- Candidate {i+1} ---\n"
            candidates_text += f"Name: {cand.get('fullname', 'Unknown')}\n"
            candidates_text += f"Skills: {cand.get('skills', 'None')}\n"
            candidates_text += f"Years Experience: {cand.get('years_experience', 0)}\n"
            candidates_text += f"Degree: {cand.get('highest_degree', 'None')}\n"
            candidates_text += f"Experience Summary: {str(cand.get('experience', ''))[:1000]}\n"

        prompt = CANDIDATE_COMPARISON_PROMPT.format(
            job_title=job_data.get("job_title", ""),
            department=job_data.get("department", ""),
            job_skills=job_data.get("skills_requirements", ""),
            job_desc=str(job_data.get("description", ""))[:2000],
            exp_req=job_data.get("experience_requirements", "Not specified"),
            edu_req=job_data.get("education_requirements", "Not specified"),
            candidates_text=candidates_text
        )

        payload = {
            "model": LLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.05,
                "num_predict": 2048
            }
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        
        result_json = response.json()
        raw_response = result_json.get("response", "")
        
        parsed = _extract_json(raw_response)
        if not parsed:
            logger.warning("Llama candidate comparison: could not extract JSON.")
            return None

        return parsed

    except Exception as e:
        logger.error(f"llama_compare_candidates error: {e}")
        return None


class LlamaService:
    llama_analyze_match = staticmethod(llama_analyze_match)
    llama_compare_candidates = staticmethod(llama_compare_candidates)


llama_service = LlamaService()
