import re
from typing import List, Optional, Dict, Any
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.job_matching_service import calculate_match_score


def normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def normalize_phone(phone: Optional[str]) -> str:
    return re.sub(r"[^0-9]", "", phone or "")


async def compare_candidates_service(
    db: AsyncSession,
    application_ids: List[int],
    reference_job_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compare multiple candidates for HR evaluation.
    Enforces that every candidate is a distinct person (rejects duplicate applicant_id, email, or phone with 422).
    Supports cross-job comparison by re-scoring candidates against a common reference job.
    """
    if not application_ids or len(application_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least two candidates are required for comparison."
        )

    # 1. Reject identical application IDs
    if len(application_ids) != len(set(application_ids)):
        raise HTTPException(
            status_code=422,
            detail="Cannot compare the same application multiple times. Comparison is for choosing between different people."
        )

    # 2. Fetch applications
    stmt = select(JobApplication).where(JobApplication.id.in_(application_ids))
    res = await db.execute(stmt)
    apps = list(res.scalars().all())

    if len(apps) != len(application_ids):
        found_ids = {a.id for a in apps}
        missing_ids = [aid for aid in application_ids if aid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Application(s) {missing_ids} not found."
        )

    # Preserve order requested in application_ids
    app_map = {a.id: a for a in apps}
    ordered_apps = [app_map[aid] for aid in application_ids]

    # 3. Enforce distinct people (applicant_id, normalized email, normalized phone)
    seen_applicant_ids = set()
    seen_emails = set()
    seen_phones = set()

    for app in ordered_apps:
        # Check applicant_id if present
        app_uid = getattr(app, "applicant_id", None)
        if app_uid:
            if app_uid in seen_applicant_ids:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot compare multiple applications from the same applicant. Comparison is for choosing between different people."
                )
            seen_applicant_ids.add(app_uid)

        # Check normalized email
        norm_email = normalize_email(app.candidate_email)
        if norm_email:
            if norm_email in seen_emails:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot compare multiple applications from the same person (duplicate email: {norm_email}). Comparison is for choosing between different people."
                )
            seen_emails.add(norm_email)

        # Check normalized phone
        norm_phone = normalize_phone(app.phone)
        if norm_phone and len(norm_phone) >= 7:
            if norm_phone in seen_phones:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot compare multiple applications from the same person (duplicate phone number). Comparison is for choosing between different people."
                )
            seen_phones.add(norm_phone)

    # 4. Determine Reference Job
    ref_job = None
    if reference_job_id:
        j_res = await db.execute(select(JobDescription).where(JobDescription.id == reference_job_id))
        ref_job = j_res.scalar_one_or_none()
        if not ref_job:
            raise HTTPException(status_code=404, detail=f"Reference job {reference_job_id} not found.")
    else:
        # Default: position most candidates applied for, or the first one
        job_counts = Counter(a.job_id for a in ordered_apps if a.job_id)
        if job_counts:
            chosen_job_id = job_counts.most_common(1)[0][0]
            j_res = await db.execute(select(JobDescription).where(JobDescription.id == chosen_job_id))
            ref_job = j_res.scalar_one_or_none()

    if not ref_job:
        # Fallback to first available job if none found
        j_res = await db.execute(select(JobDescription).limit(1))
        ref_job = j_res.scalar_one_or_none()

    if not ref_job:
        raise HTTPException(status_code=400, detail="No reference job available to baseline candidate comparison.")

    # 5. Check if cross-job comparison
    applied_job_ids = {a.job_id for a in ordered_apps if a.job_id}
    is_cross_job = len(applied_job_ids) > 1 or any(a.job_id != ref_job.id for a in ordered_apps)

    note = (
        f"Candidates applied for different positions. Scores are based on {ref_job.job_title} and include transferable skills."
        if is_cross_job
        else None
    )

    # Cache of all job descriptions involved
    all_job_ids = applied_job_ids | {ref_job.id}
    jobs_res = await db.execute(select(JobDescription).where(JobDescription.id.in_(all_job_ids)))
    jobs_by_id = {j.id: j for j in jobs_res.scalars().all()}

    # 6. Score each candidate against the reference job
    candidates_result = []
    for app in ordered_apps:
        applied_job = jobs_by_id.get(app.job_id)
        applied_job_title = applied_job.job_title if applied_job else (app.job_title or "Position")

        # Convert app into resume_data dict for calculate_match_score
        years_exp = 0.0
        if app.total_experience_months:
            years_exp = round(app.total_experience_months / 12.0, 1)

        skills_str = ""
        skills_list = []
        if isinstance(app.skills, list):
            skills_list = [str(s) for s in app.skills]
            skills_str = ", ".join(skills_list)
        elif isinstance(app.skills, str):
            skills_str = app.skills
            skills_list = [s.strip() for s in app.skills.split(",") if s.strip()]

        resume_data = {
            "fullname": app.candidate_name,
            "email": app.candidate_email,
            "phone": app.phone,
            "location": app.location or "",
            "skills": skills_str,
            "skills_list": skills_list,
            "experience": app.relevance or f"{app.job_title or ''} at {app.company or ''}",
            "years_experience": years_exp,
            "highest_degree": app.highest_educational_attainment or app.degree or app.candidate_degree or "",
            "degree": app.degree or app.candidate_degree or "",
            "college": app.college or "",
            "certifications": app.certifications or app.candidate_certifications or "",
            "work_experiences": app.work_experiences or [],
            "education_entries": app.education_entries or [],
        }

        # Calculate scores against reference job
        score_res = calculate_match_score(resume_data, ref_job)

        candidates_result.append({
            "application_id": app.id,
            "applicant_id": getattr(app, "applicant_id", None) or app.id,
            "name": app.candidate_name,
            "email": app.candidate_email,
            "phone": app.phone,
            "location": app.location,
            "applied_job_id": app.job_id,
            "applied_job_title": applied_job_title,
            "match_score": round(score_res.get("match_percentage", 0)),
            "skills_score": round(score_res.get("skills_score", 0)),
            "experience_score": round(score_res.get("experience_score", 0)),
            "education_score": round(score_res.get("education_score", 0)),
            "certifications_score": round(score_res.get("certifications_score", 0)),
            "completeness_score": round(score_res.get("completeness_score", 100)),
            "matched_skills": score_res.get("matched_skills", []),
            "missing_skills": score_res.get("missing_skills", []),
            "transferable_skills": score_res.get("transferable_skills", []),
            "relevance": app.relevance,
            "experience_years": years_exp,
            "degree": app.degree or app.highest_educational_attainment,
            "college": app.college,
            "certifications": app.certifications or app.candidate_certifications,
            "ai_summary": score_res.get("ai_summary", app.ai_summary),
            "strengths": score_res.get("strengths", app.strengths or []),
            "weaknesses": score_res.get("weaknesses", app.weaknesses or []),
            "status": app.status,
            "resume_url": app.resume_url,
            "profile_image_url": app.profile_image_url,
        })

    # Return result
    return {
        "reference_job": {
            "id": ref_job.id,
            "job_title": ref_job.job_title,
            "department": getattr(ref_job, "department", "General"),
            "location": getattr(ref_job, "location", "Sto. Tomas, Batangas"),
            "skills_requirements": getattr(ref_job, "skills_requirements", ""),
            "experience_requirements": getattr(ref_job, "experience_requirements", ""),
        },
        "is_cross_job": is_cross_job,
        "note": note,
        "candidates": candidates_result,
    }
