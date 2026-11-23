import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job_application import JobApplication
from app.schemas.job_application_schema import JobApplicationCreate
from app.services.notification_service import create_notification
from app.repositories.job_application_repository import JobApplicationRepository

logger = logging.getLogger(__name__)


def _resolve_application_years(
    explicit_years=None,
    total_months=0,
    work_experiences=None,
    relevance: str = "",
    relevant_experience: str = "",
) -> int:
    if explicit_years is not None:
        try:
            return max(0, int(explicit_years))
        except (TypeError, ValueError):
            pass
    if total_months:
        try:
            if int(total_months) > 0:
                return max(1, (int(total_months) + 6) // 12)
        except (TypeError, ValueError):
            pass
    if isinstance(work_experiences, list) and work_experiences:
        from app.extractors.content.experience_extractor import _compute_merged_experience_months
        merged_months = _compute_merged_experience_months(
            [we for we in work_experiences if isinstance(we, dict)]
        )
        if merged_months > 0:
            return max(1, (merged_months + 6) // 12)
        summed_months = sum(
            int(we.get("duration_months") or 0)
            for we in work_experiences
            if isinstance(we, dict)
        )
        if summed_months > 0:
            return max(1, (summed_months + 6) // 12)
    try:
        import re
        combined = f"{relevance or ''} | {relevant_experience or ''}"
        matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)", combined, re.IGNORECASE)
        if matches:
            return max(int(match) for match in matches)
    except Exception:
        pass
    return 0


def _apply_experience_gap_evaluation(data: dict, job_desc) -> None:
    """Ensure minimum experience gaps are computed and flagged on submitted applications."""
    if job_desc:
        from app.services.requirement_confirmation import evaluate_requirements, apply_confirmations
        from app.services.job_matching_service import _normalize_skill
        rows = evaluate_requirements(data, job_desc, _normalize_skill)
        data["requirement_evaluations"] = rows
        resolved = apply_confirmations(data, rows)
        from app.services.requirement_rules import clean_list_items
        data["skills"] = clean_list_items(resolved.get("skills"))
        data["certifications"] = resolved.get("certifications") or None
        confirmed_exp_items = [
            part for r in rows if r["field"] == "experience" and r.get("answer") in ("yes", "some")
            for part in (r.get("requirement"), r.get("details")) if part
        ]
        if confirmed_exp_items:
            existing_rel = str(data.get("relevance") or "").strip()
            rel_parts = [existing_rel] if existing_rel else []
            for part in confirmed_exp_items:
                if str(part).strip() not in rel_parts:
                    rel_parts.append(str(part).strip())
            data["relevance"] = " | ".join(rel_parts)
        data["years_experience"] = resolved.get("years_experience", data.get("years_experience"))
    explicit_years = data.pop("years_experience", None)
    cand_years = _resolve_application_years(
        explicit_years=explicit_years,
        total_months=data.get("total_experience_months") or 0,
        work_experiences=data.get("work_experiences"),
        relevance=data.get("relevance") or "",
        relevant_experience=data.get("relevant_experience") or "",
    )
    if cand_years > 0 and not data.get("total_experience_months"):
        data["total_experience_months"] = cand_years * 12

    if not job_desc:
        return

    from app.services.job_matching_service import calculate_experience_match

    pending_exp = [r for r in data.get("requirement_evaluations", []) if r["field"] == "experience" and r["status"] in ("Not confirmed", "Possible match")]
    if pending_exp:
        data["experience_reason"] = "Not confirmed: Awaiting applicant confirmation of experience requirements."
        data["experience_gaps"] = None
        data["weaknesses"] = [w for w in data.get("weaknesses", []) or [] if "below minimum" not in str(w).lower()]
        return

    job_context = f"{getattr(job_desc, 'description', '') or ''} {getattr(job_desc, 'skills_requirements', '') or ''}"
    exp_res = calculate_experience_match(
        cand_years,
        job_context,
        getattr(job_desc, "experience_requirements", None),
    )
    req_yrs = exp_res.get("required_years", 0) or 0
    if exp_res.get("below_minimum") and req_yrs > 0:
        gap_yrs = exp_res.get("gap_years", max(0, req_yrs - cand_years))
        gap_msg = (
            f"Gap reported: experience below minimum — Required: {req_yrs} yrs | "
            f"Candidate: {cand_years} yr{'s' if cand_years != 1 else ''} "
            f"({gap_yrs} yr{'s' if gap_yrs != 1 else ''} short)"
        )
        data["experience_gaps"] = gap_msg
        if not data.get("experience_reason") or "below minimum" not in str(data.get("experience_reason")).lower():
            data["experience_reason"] = exp_res["reason"]

        weaknesses = list(data.get("weaknesses") or [])
        short_note = (
            f"Gap reported: experience below minimum ({cand_years} yr{'s' if cand_years != 1 else ''} "
            f"vs {req_yrs} yr{'s' if req_yrs != 1 else ''} required)."
        )
        if not any("below minimum" in str(w).lower() for w in weaknesses):
            data["weaknesses"] = [short_note] + weaknesses
    elif data.get("experience_gaps") == "":
        data["experience_gaps"] = None


def _sanitize_application_payload(data: dict) -> None:
    """
    Strip standalone no-value markers ('None', 'N/A', 'wala', '-', etc.) from
    applicant-supplied resume/profile fields before persistence and gap checks.
    """
    from app.services.requirement_rules import clean_list_items, normalize_requirement_text

    if "skills" in data:
        if isinstance(data["skills"], list):
            data["skills"] = clean_list_items(data["skills"])
        elif isinstance(data["skills"], str):
            cleaned_skills = clean_list_items(data["skills"])
            data["skills"] = cleaned_skills

    for text_field in (
        "company",
        "job_title",
        "relevance",
        "degree",
        "college",
        "highest_educational_attainment",
        "certifications",
        "candidate_certifications",
    ):
        if text_field in data and data[text_field] is not None:
            data[text_field] = normalize_requirement_text(data[text_field])


def _resume_data_from_application(app: JobApplication) -> dict:
    from app.services.requirement_rules import clean_list_items, normalize_requirement_text

    cleaned_skills = clean_list_items(app.skills or [])
    skills_text = " | ".join(cleaned_skills)

    exp_parts = []
    app_title = normalize_requirement_text(app.job_title)
    app_company = normalize_requirement_text(app.company)
    if app_title or app_company:
        exp_parts.append(f"{app_title} at {app_company}" if (app_title and app_company) else (app_title or app_company))
    cleaned_work_exps = []
    if getattr(app, "work_experiences", None) and isinstance(app.work_experiences, list):
        for we in app.work_experiences:
            if isinstance(we, dict):
                r_title = normalize_requirement_text(we.get("job_title") or we.get("role") or we.get("title")) or ""
                r_comp = normalize_requirement_text(we.get("company_name") or we.get("company")) or ""
                if r_title or r_comp:
                    cleaned_work_exps.append(we)
                    entry_str = f"{r_title} at {r_comp}" if (r_title and r_comp) else (r_title or r_comp)
                    if entry_str not in exp_parts:
                        exp_parts.append(entry_str)
                elif we.get("responsibilities") or we.get("description"):
                    cleaned_work_exps.append(we)
    rel_exp = normalize_requirement_text(app.relevant_experience)
    if rel_exp and rel_exp not in exp_parts:
        exp_parts.append(rel_exp)

    experience_text = " | ".join(part for part in exp_parts if part)

    years_experience = _resolve_application_years(
        explicit_years=getattr(app, "years_experience", None),
        total_months=getattr(app, "total_experience_months", 0) or 0,
        work_experiences=cleaned_work_exps or getattr(app, "work_experiences", None),
        relevance=normalize_requirement_text(app.relevance) or "",
        relevant_experience=rel_exp or "",
    )

    degree = normalize_requirement_text(app.degree) or normalize_requirement_text(getattr(app, "candidate_degree", None)) or ""
    college = normalize_requirement_text(app.college) or ""
    highest_edu = normalize_requirement_text(getattr(app, "highest_educational_attainment", None)) or degree
    certs = normalize_requirement_text(getattr(app, "certifications", None)) or normalize_requirement_text(getattr(app, "candidate_certifications", None)) or ""

    return {
        "id": app.id,
        "application_id": app.id,
        "fullname": app.candidate_name,
        "email": app.candidate_email,
        "phone": app.phone or "",
        "location": app.location or "",
        "job_title": app_title or "",
        "skills": skills_text,
        "skills_list": cleaned_skills,
        "clarification_responses": getattr(app, "clarification_responses", None) or [],
        "experience": experience_text,
        "work_experiences": cleaned_work_exps,
        "total_experience_months": getattr(app, "total_experience_months", 0) or 0,
        "years_experience": years_experience,
        "education": " - ".join(part for part in [degree, college] if part),
        "degree": degree,
        "college": college,
        "highest_degree": degree,
        "highest_educational_attainment": highest_edu,
        "education_entries": getattr(app, "education_entries", []) or [],
        "certifications": certs,
        "candidate_certifications": certs,
        "completeness_score": getattr(app, "completeness_score", None),
    }


def _needs_analysis_enrichment(app: JobApplication) -> bool:
    return any([
        app.skills_score is None,
        app.experience_score is None,
        app.education_score is None,
        not app.skills_reason,
        not app.experience_reason,
        not app.education_reason,
        not app.matched_skills and not app.missing_skills,
        not app.recommendations,
    ])


_pending_analyses = set()
_supabase_file_cache = {"files": [], "timestamp": 0.0}
_local_file_cache = {"files": [], "timestamp": 0.0}

def _apply_transient_analysis(app: JobApplication):
    """
    Check if analysis fields are missing for older records.
    Instead of calculating synchronously, dispatch a background task to process it.
    Deduplicates tasks to avoid queue flooding.
    """
    if not app.job or not _needs_analysis_enrichment(app):
        return

    if app.id in _pending_analyses:
        return

    _pending_analyses.add(app.id)
    try:
        from app.tasks import analyze_application_task
        analyze_application_task.delay(app.id)
    except Exception as e:
        _pending_analyses.discard(app.id)
        print(f"WARNING: Failed to dispatch background analysis for {app.id}: {e}")


def _get_cached_supabase_files(allow_network: bool = True):
    import time
    now = time.time()
    if (now - _supabase_file_cache["timestamp"]) < 60:
        return _supabase_file_cache["files"]
    if not allow_network:
        return _supabase_file_cache["files"]

    _supabase_file_cache["timestamp"] = now
    try:
        from app.utils.supabase_storage import _get_client, SUPABASE_BUCKET
        client = _get_client()
        files = client.storage.from_(SUPABASE_BUCKET).list("resumes")

        all_files = []
        for item in files:
            if item.get("id") is None:
                folder_name = item.get("name", "")
                try:
                    sub_files = client.storage.from_(SUPABASE_BUCKET).list(f"resumes/{folder_name}")
                    for sf in sub_files:
                        if sf.get("id"):
                            all_files.append((f"resumes/{folder_name}/{sf['name']}", sf["name"].lower()))
                except Exception:
                    pass
            else:
                all_files.append((f"resumes/{item['name']}", item["name"].lower()))

        _supabase_file_cache["files"] = all_files
        return all_files
    except Exception:
        return _supabase_file_cache["files"]


def _get_cached_local_files():
    import os
    import re
    import time

    now = time.time()
    if (now - _local_file_cache["timestamp"]) < 60:
        return _local_file_cache["files"]

    _local_file_cache["timestamp"] = now
    upload_dir = "uploads/resumes"
    if not os.path.exists(upload_dir):
        _local_file_cache["files"] = []
        return []

    parsed = []
    try:
        for filename in os.listdir(upload_dir):
            match = re.match(r'^(\d+)_', filename)
            ts = int(match.group(1)) if match else -1
            parsed.append((filename, filename.lower(), ts))
    except Exception as e:
        print(f"WARNING: Error while listing local resumes: {e}")

    _local_file_cache["files"] = parsed
    return parsed


def _enrich_resume_url(app: JobApplication, allow_network: bool = True):
    if app.resume_url:
        return

    import re

    name_parts = [p.lower() for p in re.split(r'\W+', app.candidate_name or "") if p]
    if not name_parts:
        return

    # 1. Try cached Supabase Storage files without per-row network storms
    all_files = _get_cached_supabase_files(allow_network=allow_network)
    if all_files:
        try:
            best_match = None
            best_time = -1

            for storage_path, filename_lower in all_files:
                if all(part in filename_lower for part in name_parts):
                    base_name = filename_lower.rsplit("/", 1)[-1]
                    match = re.match(r'^(\d+)_', base_name)
                    if match:
                        ts = int(match.group(1))
                        if ts > best_time:
                            best_time = ts
                            best_match = storage_path
                    elif not best_match:
                        best_match = storage_path

            if best_match:
                from app.utils.supabase_storage import _get_client, SUPABASE_BUCKET
                client = _get_client()
                public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(best_match)
                app.resume_url = public_url
                return
        except Exception as e:
            print(f"WARNING: Supabase resume lookup failed, trying local: {e}")

    # 2. Fallback: cached local filesystem entries
    local_files = _get_cached_local_files()
    best_match = None
    best_time = -1
    for filename, filename_lower, ts in local_files:
        if all(part in filename_lower for part in name_parts):
            if ts > best_time:
                best_time = ts
                best_match = filename
            elif not best_match:
                best_match = filename

    if best_match:
        app.resume_url = f"/uploads/resumes/{best_match}"


def _enrich_applications(apps: list[JobApplication], bulk_mode: bool = False) -> list[JobApplication]:
    # Never block bulk HR Dashboard list fetches with per-row Supabase/local scans,
    # mass Celery task queueing, or synchronous spaCy/regex extraction across 500+ rows.
    is_heavy_batch = bulk_mode or len(apps) > 25
    if is_heavy_batch:
        return apps

    for app in apps:
        _apply_transient_analysis(app)
        _enrich_resume_url(app, allow_network=True)
        if not getattr(app, "work_experiences", None):
            exp_source = app.relevant_experience or app.relevance or ""
            if exp_source and len(exp_source.strip()) > 5:
                try:
                    from app.extractors.content.experience_extractor import extract_structured_experience
                    structured = extract_structured_experience(exp_source)
                    if structured.get("work_experiences"):
                        app.work_experiences = structured["work_experiences"]
                        app.total_experience_months = structured.get("total_experience_months", 0)
                except Exception:
                    pass

        if not getattr(app, "education_entries", None):
            edu_source = " \n ".join(part for part in [app.candidate_degree, app.degree, app.college] if part)
            if edu_source and len(edu_source.strip()) > 3:
                try:
                    from app.extractors.content.education_extractor import extract_structured_education
                    structured_edu = extract_structured_education(edu_source)
                    if structured_edu.get("education_entries"):
                        app.education_entries = structured_edu["education_entries"]
                        app.highest_educational_attainment = structured_edu.get("highest_educational_attainment")
                except Exception:
                    pass
    return apps

async def resolve_application_notification_email(
    db: AsyncSession,
    application: JobApplication,
) -> Optional[str]:
    """
    Resolve the notification email for an application.
    The login email of the linked user account (user_id) is always the account identity
    and notification target. Falls back to candidate_email only when unlinked.
    """
    app_uid = getattr(application, "user_id", None)
    if app_uid:
        try:
            from sqlalchemy import select
            from app.models.user import User
            res = await db.execute(select(User.email).where(User.id == app_uid))
            account_email = res.scalar_one_or_none()
            if account_email:
                return account_email.strip()
        except Exception as e:
            logger.debug(f"Could not resolve account email for user_id={app_uid}: {e}")
    return getattr(application, "candidate_email", None)


async def check_duplicate(
    db: AsyncSession,
    db_job_id: int,
    candidate_email: str,
    user_id: Optional[int] = None,
) -> Optional[JobApplication]:
    """Check if an applicant has already applied for a specific job (by user_id first, then email)."""
    if not db_job_id:
        return None
    if user_id:
        return await JobApplicationRepository.get_by_job_and_user_id(
            db, db_job_id, user_id, fallback_email=candidate_email
        )
    if not candidate_email:
        return None
    return await JobApplicationRepository.get_by_job_and_email(db, db_job_id, candidate_email)


async def create_job_application(
    db: AsyncSession, 
    application_in: JobApplicationCreate, 
    db_job_id: int,
    duplicate_policy: Optional[str] = None,
    current_user: Optional[dict] = None,
):
    """Create a new job application or handle duplicates according to policy (block or version)."""
    # Resolve authenticated candidate user_id and login email
    is_imported = (getattr(application_in, "source", None) or "Online").strip().lower() == "imported"
    auth_user_id: Optional[int] = None
    account_email: Optional[str] = None

    if not is_imported:
        if current_user and (current_user.get("role") or "CANDIDATE").upper() == "CANDIDATE":
            auth_user_id = current_user.get("id")
            account_email = (current_user.get("sub") or current_user.get("email") or "").strip() or None
        if not auth_user_id:
            auth_user_id = getattr(application_in, "user_id", None) or getattr(application_in, "applicant_id", None)

        if auth_user_id and not account_email:
            try:
                from sqlalchemy import select
                from app.models.user import User
                u_res = await db.execute(select(User.email).where(User.id == auth_user_id))
                account_email = u_res.scalar_one_or_none()
            except Exception:
                account_email = None

    # ── Duplicate Detection (REQ: Limit / TC-RES-016) ───────────────────────────
    if auth_user_id:
        existing_app = await JobApplicationRepository.get_by_job_and_user_id(
            db, db_job_id, auth_user_id, fallback_email=account_email
        )
    else:
        existing_app = await JobApplicationRepository.get_by_job_and_email(
            db, db_job_id, application_in.candidate_email
        )
    job_desc = None
    try:
        from app.repositories.job_description_repository import JobDescriptionRepository
        job_desc = await JobDescriptionRepository.get_by_id(db, db_job_id)
    except Exception:
        job_desc = None

    if existing_app:
        policy = (duplicate_policy or "block").lower().strip()
        if policy == "block":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate application: An application for this role has already been submitted by {account_email or application_in.candidate_email}."
            )
        elif policy == "version":
            # Update/version existing record without creating double records
            from datetime import datetime
            data = application_in.model_dump()
            if 'job_id' in data:
                del data['job_id']
            if auth_user_id:
                data['user_id'] = auth_user_id
            _sanitize_application_payload(data)
            _apply_experience_gap_evaluation(data, job_desc)
            valid_cols = set(JobApplication.__table__.columns.keys())
            for k, v in data.items():
                if v is not None and k in valid_cols:
                    setattr(existing_app, k, v)
            existing_app.updated_at = datetime.utcnow()
            updated_app = await JobApplicationRepository.update(db, existing_app)
            try:
                from app.tasks import analyze_application_task
                analyze_application_task.delay(updated_app.id)
            except Exception as task_err:
                logger.warning(f"Failed to dispatch background task for versioned app: {task_err}")
            return updated_app
        else:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate application: An application for this role has already been submitted by {account_email or application_in.candidate_email}."
            )

    # ── Active Applications Limit Check (REQ081 & REQ082) ───────────────────
    try:
        from app.services.system_config_service import system_config_service
        max_active = await system_config_service.get_max_active_applications(db)
        if auth_user_id:
            candidate_apps = await JobApplicationRepository.get_by_user_id(
                db, auth_user_id, fallback_email=account_email
            )
        else:
            candidate_apps = await JobApplicationRepository.get_by_email(db, application_in.candidate_email)
        inactive_statuses = {
            "NOT SELECTED", "NOT_SELECTED", "REJECTED", "WITHDRAWN",
            "HIRED", "ACCEPTED", "OFFER_ACCEPTED", "CLOSED"
        }
        active_apps = [
            a for a in candidate_apps 
            if (getattr(a, 'status', '') or '').upper() not in inactive_statuses
        ]
        if len(active_apps) >= max_active:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Active application limit reached: You currently have {len(active_apps)} active applications (maximum allowed: {max_active}). You cannot submit a new application until one of your active applications is closed or withdrawn."
            )
    except HTTPException:
        raise
    except Exception as limit_err:
        logger.warning(f"Error checking active applications limit: {limit_err}")

    data = application_in.model_dump()

    # Remove job_id and virtual applicant_id from data as we'll pass the internal ID
    if 'job_id' in data:
        del data['job_id']
    if 'applicant_id' in data:
        del data['applicant_id']

    submitted_email = (application_in.candidate_email or "").strip()
    explicit_contact = (getattr(application_in, "contact_email", None) or "").strip() or None
    explicit_resume_email = (getattr(application_in, "resume_email", None) or "").strip() or None

    if auth_user_id:
        data["user_id"] = auth_user_id
        if not explicit_resume_email and account_email and submitted_email and submitted_email.lower() != account_email.lower():
            explicit_resume_email = submitted_email
        data["resume_email"] = explicit_resume_email
        chosen_contact = explicit_contact or submitted_email or account_email
        data["contact_email"] = chosen_contact
        data["candidate_email"] = chosen_contact or account_email or submitted_email
    else:
        data["contact_email"] = explicit_contact or submitted_email
        data["resume_email"] = explicit_resume_email

    _sanitize_application_payload(data)
    _apply_experience_gap_evaluation(data, job_desc)

    # Create the application via repository
    new_application = await JobApplicationRepository.create(db, {
        "job_id": db_job_id,
        **data
    })

    # Trigger notifications (always send candidate notifications to account login email!)
    notification_target_email = account_email or application_in.candidate_email
    try:
        # Resolve the exact job title of the position applied for
        applied_job_title = getattr(job_desc, "job_title", None) if job_desc else None
        if not applied_job_title:
            try:
                app_dict = getattr(new_application, "__dict__", {})
                if "job" in app_dict and app_dict["job"] and getattr(app_dict["job"], "job_title", None):
                    applied_job_title = app_dict["job"].job_title
            except Exception:
                pass

        if not applied_job_title:
            applied_job_title = getattr(application_in, "job_title", None) or "the position"

        # 1. Alert HR team
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {applied_job_title}.",
            type="application",
            target_role="HR",
            sender_role="CANDIDATE"
        )
        # 2. Alert Admin team
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {applied_job_title}.",
            type="application",
            target_role="ADMIN",
            sender_role="CANDIDATE"
        )
        # 3. Personal confirmation for Candidate (to login/account email)
        if notification_target_email:
            await create_notification(
                db=db,
                title="Application Submitted",
                message=f"You successfully applied for {applied_job_title}.",
                type="application",
                target_role="CANDIDATE",
                target_email=notification_target_email,
                sender_role="SYSTEM"
            )
    except Exception as notif_err:
        print(f"WARNING: Notification failed but application saved: {notif_err}")
    # Trigger background AI analysis
    try:
        import asyncio
        from app.tasks import analyze_application_task
        analyze_application_task.delay(new_application.id)
        print(f"DEBUG: Dispatched background AI analysis task for application {new_application.id}")
    except Exception as task_err:
        print(f"WARNING: Failed to dispatch background task: {task_err}")

    return new_application


def serialize_application_summary(app: JobApplication) -> dict:
    """Project a JobApplication ORM instance into a lightweight JSON dict for large dashboard lists."""
    job_obj = getattr(app, "job", None)
    return {
        "id": app.id,
        "job_id": app.job_id,
        "user_id": getattr(app, "user_id", None),
        "applicant_id": getattr(app, "user_id", None),
        "candidate_name": app.candidate_name,
        "candidate_email": app.candidate_email,
        "resume_email": getattr(app, "resume_email", None),
        "contact_email": getattr(app, "contact_email", None) or app.candidate_email,
        "phone": app.phone,
        "location": app.location,
        "job_title": app.job_title,
        "company": app.company,
        "skills": app.skills or [],
        "match_score": app.match_score,
        "skills_score": app.skills_score,
        "experience_score": app.experience_score,
        "education_score": app.education_score,
        "certifications_score": app.certifications_score,
        "completeness_score": getattr(app, "completeness_score", None),
        "applied_weights": getattr(app, "applied_weights", None),
        "profile_image_url": app.profile_image_url,
        "resume_url": app.resume_url,
        "matched_skills": app.matched_skills or [],
        "missing_skills": app.missing_skills or [],
        "clarification_responses": getattr(app, "clarification_responses", None) or [],
        "requirement_evaluations": getattr(app, "requirement_evaluations", None) or [],
        "total_experience_months": app.total_experience_months,
        "highest_educational_attainment": app.highest_educational_attainment,
        "experience_gaps": app.experience_gaps,
        "ai_powered": bool(app.ai_powered),
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "job": (
            {
                "id": job_obj.id,
                "job_title": job_obj.job_title,
                "location": job_obj.location,
                "department": job_obj.department,
            }
            if job_obj
            else None
        ),
    }


async def _build_recommended_positions(
    db: AsyncSession,
    app: JobApplication,
    other_apps: list[dict],
    limit: int = 5,
) -> list[dict]:
    """
    Evaluate the candidate's profile against other active job postings and return
    top-matching positions based on the automated ATS analysis.
    """
    from app.repositories.job_description_repository import JobDescriptionRepository
    from app.services.job_matching_service import calculate_match_score, get_current_matching_config

    active_jobs = await JobDescriptionRepository.get_all_active(db, include_inactive=False)
    if not active_jobs:
        return []

    matching_config = None
    try:
        from app.services.system_config_service import get_matching_parameters
        matching_config = await get_matching_parameters(db)
    except Exception:
        matching_config = get_current_matching_config()

    resume_data = _resume_data_from_application(app)
    other_by_job_id = {oa["job_id"]: oa for oa in other_apps if oa.get("job_id") is not None}

    recommendations: list[dict] = []
    for job in active_jobs:
        if job.id == app.job_id:
            continue

        match_res = calculate_match_score(
            resume_data,
            job,
            use_ai=False,
            matching_config=matching_config,
            log_prediction=False,
        )
        match_pct = float(match_res.get("match_percentage") or 0.0)
        skills_sc = float(match_res.get("skills_score") or 0.0)
        exp_sc = float(match_res.get("experience_score") or 0.0)

        if not match_res.get("meets_threshold") or (skills_sc <= 0 and exp_sc <= 10.0):
            continue

        matched_skills = match_res.get("matched_skills") or []
        strengths = match_res.get("strengths") or []
        rel_summary = match_res.get("experience_relevance_summary") or ""
        reason_parts = []
        if matched_skills:
            reason_parts.append(f"Matched skills: {', '.join(matched_skills[:4])}")
        if exp_sc >= 50.0 and rel_summary:
            reason_parts.append(rel_summary)
        elif strengths:
            reason_parts.append(strengths[0])

        existing = other_by_job_id.get(job.id)
        recommendations.append({
            "id": job.id,
            "job_id": str(getattr(job, "job_id", None) or job.id),
            "job_title": job.job_title,
            "department": getattr(job, "department", "") or "",
            "location": getattr(job, "location", "") or "",
            "match_percentage": round(match_pct, 1),
            "match_level": match_res.get("match_level"),
            "skills_score": round(skills_sc, 1),
            "experience_score": round(exp_sc, 1),
            "education_score": round(float(match_res.get("education_score") or 0.0), 1),
            "certifications_score": round(float(match_res.get("certifications_score") or 0.0), 1),
            "matched_skills": matched_skills[:6],
            "missing_skills": (match_res.get("missing_skills") or [])[:5],
            "strengths": strengths[:3],
            "reason": " • ".join(reason_parts) if reason_parts else (match_res.get("ai_summary") or ""),
            "already_applied": existing is not None,
            "existing_application_id": existing.get("id") if existing else None,
            "existing_application_status": existing.get("status") if existing else None,
        })

    recommendations.sort(
        key=lambda item: (item["match_percentage"], item["skills_score"] or 0.0, item["experience_score"] or 0.0),
        reverse=True,
    )
    return recommendations[:limit]


async def get_application_by_id(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    """Get a single job application by ID with full detail enrichment."""
    app = await JobApplicationRepository.get_by_id(db, application_id)
    if not app:
        return None
    _enrich_applications([app], bulk_mode=False)

    other_apps: list[dict] = []
    # REQ083: Enrich with other active applications summary for this candidate (by user_id first, then email)
    try:
        if getattr(app, "user_id", None):
            cand_apps = await JobApplicationRepository.get_by_user_id(
                db, app.user_id, fallback_email=app.candidate_email
            )
        elif app.candidate_email:
            cand_apps = await JobApplicationRepository.get_by_email(db, app.candidate_email)
        else:
            cand_apps = []
        if cand_apps:
            inactive_statuses = {
                "NOT SELECTED", "NOT_SELECTED", "REJECTED", "WITHDRAWN",
                "HIRED", "ACCEPTED", "OFFER_ACCEPTED", "CLOSED"
            }
            active_count = 0
            for ca in cand_apps:
                is_act = (getattr(ca, "status", "") or "").upper() not in inactive_statuses
                if is_act:
                    active_count += 1
                if ca.id != app.id:
                    j_title = None
                    if getattr(ca, "job", None) and getattr(ca.job, "job_title", None):
                        j_title = ca.job.job_title
                    else:
                        j_title = getattr(ca, "job_title", None) or "Unknown Role"
                    other_apps.append({
                        "id": ca.id,
                        "job_id": ca.job_id,
                        "job_title": j_title,
                        "status": ca.status or "PENDING",
                        "match_score": ca.match_score,
                        "created_at": ca.created_at,
                        "is_active": is_act
                    })
            setattr(app, "active_applications_count", active_count)
            setattr(app, "has_other_active_applications", any(o["is_active"] for o in other_apps))
            setattr(app, "other_applications", other_apps)
    except Exception as multi_err:
        logger.warning(f"Error enriching multi-application summary: {multi_err}")

    recommended_positions: list[dict] = []
    try:
        recommended_positions = await _build_recommended_positions(db, app, other_apps)
        setattr(app, "recommended_positions", recommended_positions)
    except Exception as rec_err:
        logger.warning(f"Error computing recommended positions for application {application_id}: {rec_err}")
        setattr(app, "recommended_positions", [])

    # Upgrade empty or legacy applicant-facing recommendations into HR screening & interview insights
    try:
        from app.services.job_matching_service import calculate_match_score, is_legacy_applicant_recommendation

        existing_recs = getattr(app, "recommendations", None) or []
        needs_hr_recs = (not existing_recs) or any(
            is_legacy_applicant_recommendation(r) for r in existing_recs
        )
        if needs_hr_recs:
            target_job = getattr(app, "job", None)
            if target_job is None and getattr(app, "job_id", None) is not None:
                from app.repositories.job_description_repository import JobDescriptionRepository
                target_job = await JobDescriptionRepository.get_by_id(db, app.job_id)

            if target_job is not None:
                fresh = calculate_match_score(
                    _resume_data_from_application(app),
                    target_job,
                    use_ai=False,
                    log_prediction=False,
                )
                hr_recs = list(fresh.get("recommendations") or [])
            else:
                hr_recs = []

            if recommended_positions:
                top_alt = recommended_positions[0]
                current_pct = float(getattr(app, "match_score", 0) or 0)
                if top_alt.get("match_percentage", 0) >= max(50.0, current_pct + 10.0):
                    alt_tip = (
                        f"Alternative placement: candidate scored {round(top_alt['match_percentage'])}% for "
                        f"{top_alt['job_title']} — consider routing to this role if {getattr(app, 'job_title', 'the applied role')} is not a fit."
                    )
                    if alt_tip not in hr_recs:
                        hr_recs = [alt_tip, *hr_recs][:4]

            if hr_recs:
                setattr(app, "recommendations", hr_recs)
    except Exception as hr_rec_err:
        logger.warning(f"Error refreshing HR recommendations for application {application_id}: {hr_rec_err}")

    return app


async def get_applications_by_job(db: AsyncSession, job_id: int):
    """Get all applications for a specific job."""
    applications = await JobApplicationRepository.get_by_job_id(db, job_id)
    return _enrich_applications(applications, bulk_mode=len(applications) > 25)


async def get_applications_by_email(db: AsyncSession, email: str):
    """Get all applications for a specific candidate email (or user_id)."""
    applications = await JobApplicationRepository.get_by_email(db, email)
    return _enrich_applications(applications, bulk_mode=False)


async def get_applications_for_user(
    db: AsyncSession,
    user_id: int,
    fallback_email: Optional[str] = None,
):
    """Get all applications linked to an authenticated user_id."""
    applications = await JobApplicationRepository.get_by_user_id(
        db, user_id, fallback_email=fallback_email
    )
    return _enrich_applications(applications, bulk_mode=False)


def _get_item_attr(item, key: str, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _filter_sort_slice_applications(
    items: list,
    position: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list:
    """Filter by position, sort deterministically by score or date, and slice for pagination."""
    from datetime import datetime

    filtered = items
    if position and position.strip() and position.strip().lower() not in ("all", "all jobs"):
        pos_q = position.strip().lower()
        filtered = [
            item for item in filtered
            if (
                (
                    _get_item_attr(_get_item_attr(item, "job") or {}, "job_title")
                    or _get_item_attr(item, "job_title")
                    or ""
                )
                .strip()
                .lower()
                == pos_q
            )
        ]

    if sort_by:
        sb = sort_by.strip().lower()

        def _created_ts(app_obj) -> float:
            dt = _get_item_attr(app_obj, "created_at")
            if not dt:
                return 0.0
            if isinstance(dt, str):
                try:
                    return datetime.fromisoformat(dt.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    return 0.0
            return dt.timestamp()

        def _score_val(app_obj) -> float:
            return float(_get_item_attr(app_obj, "match_score", 0.0) or 0.0)

        def _id_val(app_obj) -> int:
            return int(_get_item_attr(app_obj, "id", 0) or 0)

        if sb == "match_desc":
            filtered = sorted(filtered, key=lambda a: (_score_val(a), _created_ts(a), _id_val(a)), reverse=True)
        elif sb == "match_asc":
            filtered = sorted(filtered, key=lambda a: (_score_val(a), -_created_ts(a), -_id_val(a)))
        elif sb == "date_desc":
            filtered = sorted(filtered, key=lambda a: (_created_ts(a), _score_val(a), _id_val(a)), reverse=True)
        elif sb == "date_asc":
            filtered = sorted(filtered, key=lambda a: (_created_ts(a), -_score_val(a), _id_val(a)))

    if offset > 0 or limit is not None:
        end = (offset + limit) if (limit is not None and limit >= 0) else None
        filtered = filtered[max(0, offset) : end]

    return filtered


async def get_all_applications(
    db: AsyncSession,
    position: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """Get all job applications, with optional position filter, score/date sorting, and pagination."""
    applications = await JobApplicationRepository.get_all(db)
    enriched = _enrich_applications(applications, bulk_mode=True)
    return _filter_sort_slice_applications(
        enriched, position=position, sort_by=sort_by, limit=limit, offset=offset
    )


async def get_all_applications_summary(
    db: AsyncSession,
    position: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[dict]:
    """Return fast column-projected summary dictionaries for large HR Dashboard loads."""
    summaries = await JobApplicationRepository.get_all_summaries(db)
    return _filter_sort_slice_applications(
        summaries, position=position, sort_by=sort_by, limit=limit, offset=offset
    )


async def update_application_status(
    db: AsyncSession, 
    application_id: int, 
    new_status: str,
    notes: Optional[str] = None,
    custom_email_subject: Optional[str] = None,
    custom_email_message: Optional[str] = None,
) -> Optional[JobApplication]:
    """Update application status, record in-app notifications, and dispatch professional email to candidate."""
    db_application = await JobApplicationRepository.get_by_id(db, application_id)

    if not db_application:
        return None

    status_upper = new_status.upper()
    previous_status = db_application.status
    db_application.status = status_upper
    if notes:
        db_application.hr_shortlist_notes = notes
    db_application = await JobApplicationRepository.update(db, db_application)

    # Send notifications about status change
    try:
        # Notify HR
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="HR",
            sender_role="HR"
        )
        # Notify ADMIN
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="ADMIN",
            sender_role="HR"
        )

        # Resolve Job Title
        job_title = None
        try:
            app_dict = getattr(db_application, "__dict__", {})
            if "job" in app_dict and app_dict["job"] and getattr(app_dict["job"], "job_title", None):
                job_title = app_dict["job"].job_title
        except Exception:
            pass

        if not job_title and getattr(db_application, "job_id", None):
            from app.repositories.job_description_repository import JobDescriptionRepository
            try:
                job_desc = await JobDescriptionRepository.get_by_id(db, db_application.job_id)
                if job_desc and getattr(job_desc, "job_title", None):
                    job_title = job_desc.job_title
            except Exception:
                pass

        if not job_title:
            job_title = getattr(db_application, "job_title", None) or "Position"

        if status_upper == "ACCEPTED":
            title = "Application Accepted 🎉"
            message = f"Congratulations! Your application for the position of {job_title} has been accepted."
        elif status_upper in ("REJECTED", "ARCHIVED", "PASSED_OVER"):
            title = "Application Update"
            message = f"Thank you for your interest. Unfortunately, your application for the position of {job_title} was not selected."
        elif status_upper in ("TECHNICAL INTERVIEW", "INTERVIEW"):
            title = "Technical Interview Scheduled 💻"
            message = f"You have advanced to the Technical Interview stage for the {job_title} position!"
        elif status_upper == "FINAL INTERVIEW":
            title = "Final Interview Scheduled 🤝"
            message = f"Great news! You have reached the Final Interview stage for the {job_title} position!"
        elif status_upper in ("REVIEWED", "SCREENED"):
            title = "Application Under Review"
            message = f"Great news! Your application for the position of {job_title} has been reviewed."
        elif status_upper in ("HIRED", "OFFER"):
            title = "Selection & Job Offer 🎉"
            message = f"Congratulations! You have been selected for hire for the {job_title} position!"
        else:
            title = "Application Status Update"
            message = f"Your application for the position of {job_title} is currently marked as {status_upper}."

        # Resolve account notification email (login email takes priority over resume/contact email)
        notif_email = await resolve_application_notification_email(db, db_application)

        # In-app notification
        if notif_email:
            await create_notification(
                db=db,
                title=title,
                message=message,
                type="application_update",
                target_role="CANDIDATE",
                target_email=notif_email,
                sender_role="HR"
            )

        # Dispatch professional email to candidate's account email
        if notif_email:
            try:
                from app.services.email_service import send_application_status_update_email
                await send_application_status_update_email(
                    to_email=notif_email,
                    candidate_name=db_application.candidate_name or "Candidate",
                    job_title=job_title or "Position",
                    new_status=status_upper,
                    previous_status=previous_status,
                    notes=notes,
                    custom_subject=custom_email_subject,
                    custom_message=custom_email_message,
                    db=db,
                )
                logger.info(f"Dispatched status update email ({status_upper}) to candidate {notif_email}")
            except Exception as email_err:
                logger.error(f"Error dispatching status update email to candidate {notif_email}: {email_err}")

        # ── REQ086: Flag other active applications when candidate is hired/accepted ──
        if status_upper in ("ACCEPTED", "HIRED", "OFFER", "OFFER_ACCEPTED") and (getattr(db_application, "user_id", None) or db_application.candidate_email):
            try:
                if getattr(db_application, "user_id", None):
                    candidate_all_apps = await JobApplicationRepository.get_by_user_id(
                        db, db_application.user_id, fallback_email=db_application.candidate_email
                    )
                else:
                    candidate_all_apps = await JobApplicationRepository.get_by_email(db, db_application.candidate_email)
                inactive_statuses = {
                    "NOT SELECTED", "NOT_SELECTED", "REJECTED", "WITHDRAWN",
                    "HIRED", "ACCEPTED", "OFFER_ACCEPTED", "CLOSED"
                }
                flagged_count = 0
                for other_app in candidate_all_apps:
                    if other_app.id != db_application.id and (getattr(other_app, "status", "") or "").upper() not in inactive_statuses:
                        other_app.is_flagged_for_review = True
                        other_app.review_flag_reason = f"Candidate was marked as {status_upper} for {job_title}."
                        await JobApplicationRepository.update(db, other_app)
                        flagged_count += 1
                if flagged_count > 0:
                    await create_notification(
                        db=db,
                        title="Candidate Active Applications Flagged for Review",
                        message=f"{db_application.candidate_name} was marked as {status_upper} for {job_title}. {flagged_count} other active application(s) have been flagged for HR review.",
                        type="application_flagged",
                        target_role="HR",
                        sender_role="SYSTEM"
                    )
            except Exception as flag_err:
                logger.warning(f"Error flagging other applications for hired candidate: {flag_err}")

        # ── REQ085: Combined Initial Interview Suggestion when candidate is shortlisted for 2+ positions ──
        if status_upper in ("SHORTLISTED", "SHORTLIST") and (getattr(db_application, "user_id", None) or db_application.candidate_email):
            try:
                if getattr(db_application, "user_id", None):
                    candidate_all_apps = await JobApplicationRepository.get_by_user_id(
                        db, db_application.user_id, fallback_email=db_application.candidate_email
                    )
                else:
                    candidate_all_apps = await JobApplicationRepository.get_by_email(db, db_application.candidate_email)
                shortlisted_apps = [
                    a for a in candidate_all_apps 
                    if (getattr(a, "status", "") or "").upper() in ("SHORTLISTED", "SHORTLIST")
                ]
                if len(shortlisted_apps) >= 2:
                    await create_notification(
                        db=db,
                        title="Combined Initial Interview Suggestion",
                        message=f"Candidate {db_application.candidate_name} is currently shortlisted for {len(shortlisted_apps)} positions. You may consider scheduling a combined initial interview.",
                        type="combined_interview_suggestion",
                        target_role="HR",
                        sender_role="SYSTEM"
                    )
            except Exception as comb_err:
                logger.warning(f"Error checking combined interview suggestion: {comb_err}")

    except Exception as e:
        logger.error(f"Error creating status update notifications: {e}")

    return db_application


async def update_application_notes(
    db: AsyncSession,
    application_id: int,
    notes: str
) -> Optional[JobApplication]:
    """Update HR shortlisting notes for a job application (REQ056)."""
    db_application = await JobApplicationRepository.get_by_id(db, application_id)
    if not db_application:
        return None
    db_application.hr_shortlist_notes = notes
    return await JobApplicationRepository.update(db, db_application)


async def delete_application(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    """Delete a job application."""
    db_application = await JobApplicationRepository.get_by_id(db, application_id)
    if not db_application:
        return None

    await JobApplicationRepository.delete(db, db_application)
    return db_application


async def get_and_validate_job(db: AsyncSession, job_id: str):
    """Get and validate a job by job_id, with fallback to numeric ID lookup."""
    from app.repositories.job_description_repository import JobDescriptionRepository

    # Try to get by job_id first
    job = await JobDescriptionRepository.get_by_job_id(db, job_id)

    if not job:
        # Fallback for static jobs or numeric IDs
        try:
            numeric_id = int(job_id)
            job = await JobDescriptionRepository.get_by_id(db, numeric_id)
        except (ValueError, TypeError):
            pass

    return job


import sys
job_application_service = sys.modules[__name__]
