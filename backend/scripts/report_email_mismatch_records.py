"""
Safe, re-runnable diagnostic script to find and report applications and resumes
whose owner was matched by resume email or where the extracted resume email differs
from the linked user/candidate account email.

IMPORTANT:
- Read-only: This script does NOT modify any records, does NOT merge accounts
  automatically, and does NOT change any application statuses.
- Re-runnable: Can be executed multiple times before or after schema updates.

Usage:
    cd backend && python -m scripts.report_email_mismatch_records
    # or:
    python backend/scripts/report_email_mismatch_records.py [--json]
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure backend directory is on sys.path when invoked directly
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import AsyncSessionLocal


def _norm_email(val: Optional[str]) -> str:
    return (val or "").strip().lower()


def _extract_email_from_parsed_data(parsed_data: Any) -> Optional[str]:
    if not parsed_data:
        return None
    if isinstance(parsed_data, str):
        try:
            parsed_data = json.loads(parsed_data)
        except Exception:
            return None
    if not isinstance(parsed_data, dict):
        return None

    direct = (
        parsed_data.get("email")
        or parsed_data.get("candidate_email")
        or (parsed_data.get("personal_info") or {}).get("email")
        or (parsed_data.get("contact_info") or {}).get("email")
        or (parsed_data.get("personal") or {}).get("email")
    )
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    return None


async def generate_email_mismatch_report(db: AsyncSession) -> Dict[str, Any]:
    """
    Inspect users, candidates, resumes, and job_applications in a read-only manner
    to identify:
    1. Resumes where the extracted email in parsed_data differs from the owning
       candidate/user account email, or where the resume lacks a valid candidate_id.
    2. Job applications that were linked only by candidate_email (missing user_id),
       or whose candidate_email/resume_email differs from the owning user account's
       login email (matched via user_id, shared resume_url, or candidate fullname).
    """
    # 1. Fetch users & candidates
    users_res = await db.execute(
        text("SELECT id, email, fullname, role, phone, is_archived FROM users")
    )
    users_rows = [dict(r._mapping) for r in users_res.fetchall()]
    users_by_id: Dict[int, Dict[str, Any]] = {u["id"]: u for u in users_rows}
    users_by_email: Dict[str, Dict[str, Any]] = {
        _norm_email(u["email"]): u for u in users_rows if _norm_email(u["email"])
    }
    users_by_name: Dict[str, List[Dict[str, Any]]] = {}
    for u in users_rows:
        norm_name = (u.get("fullname") or "").strip().lower()
        if norm_name:
            users_by_name.setdefault(norm_name, []).append(u)

    candidates_by_id: Dict[int, Dict[str, Any]] = {}
    candidates_by_resume_url: Dict[str, List[Dict[str, Any]]] = {}
    try:
        cand_res = await db.execute(
            text("SELECT id, resume_url FROM candidates")
        )
        for r in cand_res.fetchall():
            c = dict(r._mapping)
            u = users_by_id.get(c["id"], {})
            c["email"] = u.get("email")
            c["fullname"] = u.get("fullname")
            candidates_by_id[c["id"]] = c
            r_url = (c.get("resume_url") or "").strip()
            if r_url:
                candidates_by_resume_url.setdefault(r_url, []).append(c)
    except Exception:
        pass

    # 2. Inspect Resumes
    resumes_mismatched: List[Dict[str, Any]] = []
    resumes_by_file_url: Dict[str, List[Dict[str, Any]]] = {}
    resumes_by_extracted_email: Dict[str, List[Dict[str, Any]]] = {}
    total_resumes = 0

    try:
        res_query = await db.execute(
            text("SELECT * FROM resumes")
        )
        resume_rows = [dict(r._mapping) for r in res_query.fetchall()]
        total_resumes = len(resume_rows)

        for r in resume_rows:
            cand_id = r.get("candidate_id")
            owner_user = users_by_id.get(cand_id) if cand_id is not None else None
            account_email = owner_user.get("email") if owner_user else None
            extracted_email = _extract_email_from_parsed_data(r.get("parsed_data"))
            file_name = r.get("filename") or r.get("file_name")
            created_at = r.get("created_at") or r.get("uploaded_at")

            r_info = {
                "resume_id": r["id"],
                "candidate_id": cand_id,
                "account_email": account_email,
                "extracted_resume_email": extracted_email,
                "filename": file_name,
                "file_url": r.get("file_url"),
                "created_at": str(created_at) if created_at else None,
            }

            if r.get("file_url"):
                resumes_by_file_url.setdefault(r["file_url"].strip(), []).append(r_info)
            if _norm_email(extracted_email):
                resumes_by_extracted_email.setdefault(_norm_email(extracted_email), []).append(r_info)

            norm_acc = _norm_email(account_email)
            norm_ext = _norm_email(extracted_email)

            reasons: List[str] = []
            if cand_id is None or owner_user is None:
                reasons.append("missing_owner_account")
            if norm_ext and norm_acc and norm_ext != norm_acc:
                reasons.append("resume_email_differs_from_account_email")
                other_user = users_by_email.get(norm_ext)
                if other_user and other_user["id"] != cand_id:
                    reasons.append(f"resume_email_matches_different_user_id_{other_user['id']}")

            if reasons:
                resumes_mismatched.append({**r_info, "reasons": reasons})
    except Exception:
        pass

    # 3. Inspect Job Applications
    applications_reported: List[Dict[str, Any]] = []
    total_applications = 0

    try:
        app_res = await db.execute(text("SELECT * FROM job_applications"))
        app_rows = [dict(r._mapping) for r in app_res.fetchall()]
        total_applications = len(app_rows)

        for app in app_rows:
            app_id = app.get("id")
            job_id = app.get("job_id")
            cand_name = (app.get("candidate_name") or "").strip()
            cand_email = (app.get("candidate_email") or "").strip()
            norm_cand_email = _norm_email(cand_email)
            app_user_id = app.get("user_id")
            app_resume_email = app.get("resume_email")
            app_contact_email = app.get("contact_email")
            resume_url = (app.get("resume_url") or "").strip()
            extracted_email = _extract_email_from_parsed_data(app.get("extracted_data"))
            effective_resume_email = app_resume_email or extracted_email

            reasons: List[str] = []
            inferred_owner_user_ids: List[int] = []

            # A. Check direct user_id linkage if column exists and is populated
            linked_user = users_by_id.get(app_user_id) if app_user_id is not None else None
            email_matched_user = users_by_email.get(norm_cand_email) if norm_cand_email else None

            if app_user_id is None:
                if email_matched_user:
                    reasons.append("matched_by_email_only_missing_user_id")
                    inferred_owner_user_ids.append(email_matched_user["id"])
                else:
                    reasons.append("unlinked_no_user_account_for_candidate_email")

            # B. Check if linked user's login email differs from candidate_email or resume_email
            if linked_user:
                norm_login_email = _norm_email(linked_user.get("email"))
                if norm_cand_email and norm_login_email and norm_cand_email != norm_login_email:
                    reasons.append("candidate_email_differs_from_linked_user_login_email")
                if _norm_email(effective_resume_email) and norm_login_email and _norm_email(effective_resume_email) != norm_login_email:
                    reasons.append("resume_email_differs_from_linked_user_login_email")

            # C. Check if extracted_data / resume_email differs from candidate_email
            if _norm_email(effective_resume_email) and norm_cand_email and _norm_email(effective_resume_email) != norm_cand_email:
                reasons.append("extracted_resume_email_differs_from_application_email")

            # D. Check if resume_url belongs to a Resume or Candidate record owned by a candidate with a different account email
            if resume_url:
                for r_match in resumes_by_file_url.get(resume_url, []):
                    r_cand_id = r_match.get("candidate_id")
                    r_acc_email = _norm_email(r_match.get("account_email"))
                    if r_cand_id is not None and r_cand_id not in inferred_owner_user_ids:
                        inferred_owner_user_ids.append(r_cand_id)
                    if r_acc_email and norm_cand_email and r_acc_email != norm_cand_email:
                        reasons.append("resume_url_owned_by_account_with_different_login_email")
                    if not effective_resume_email and r_match.get("extracted_resume_email"):
                        effective_resume_email = r_match.get("extracted_resume_email")

                for c_match in candidates_by_resume_url.get(resume_url, []):
                    c_id = c_match.get("id")
                    c_acc_email = _norm_email(c_match.get("email"))
                    if c_id is not None and c_id not in inferred_owner_user_ids:
                        inferred_owner_user_ids.append(c_id)
                    if c_acc_email and norm_cand_email and c_acc_email != norm_cand_email:
                        reasons.append("resume_url_owned_by_account_with_different_login_email")

            # E. Check if candidate_email matches extracted email on a Resume owned by a different account email
            if norm_cand_email and norm_cand_email in resumes_by_extracted_email:
                for r_match in resumes_by_extracted_email[norm_cand_email]:
                    r_cand_id = r_match.get("candidate_id")
                    r_acc_email = _norm_email(r_match.get("account_email"))
                    if r_acc_email and r_acc_email != norm_cand_email:
                        reasons.append("application_email_matches_extracted_resume_email_of_different_account")
                        if r_cand_id is not None and r_cand_id not in inferred_owner_user_ids:
                            inferred_owner_user_ids.append(r_cand_id)

            # F. Check if candidate_name matches a registered user whose login email differs
            norm_name = cand_name.lower()
            if norm_name and norm_name in users_by_name:
                for u_match in users_by_name[norm_name]:
                    u_email = _norm_email(u_match.get("email"))
                    if u_email and u_email != norm_cand_email:
                        reasons.append("candidate_name_matches_account_with_different_login_email")
                        if u_match["id"] not in inferred_owner_user_ids:
                            inferred_owner_user_ids.append(u_match["id"])

            if reasons:
                inferred_accounts = [
                    {
                        "user_id": uid,
                        "account_email": users_by_id[uid]["email"],
                    }
                    for uid in inferred_owner_user_ids
                    if uid in users_by_id
                ]
                applications_reported.append(
                    {
                        "application_id": app_id,
                        "job_id": job_id,
                        "user_id": app_user_id,
                        "linked_account_email": linked_user.get("email") if linked_user else None,
                        "candidate_name": cand_name,
                        "candidate_email": cand_email,
                        "contact_email": app_contact_email,
                        "extracted_resume_email": effective_resume_email,
                        "resume_url": resume_url or None,
                        "status": app.get("status") or app.get("application_status"),
                        "inferred_accounts": inferred_accounts,
                        "reasons": sorted(set(reasons)),
                    }
                )
    except Exception:
        pass

    return {
        "summary": {
            "total_users": len(users_rows),
            "total_resumes": total_resumes,
            "mismatched_resumes_count": len(resumes_mismatched),
            "total_applications": total_applications,
            "reported_applications_count": len(applications_reported),
        },
        "mismatched_resumes": resumes_mismatched,
        "reported_applications": applications_reported,
    }


def format_report_text(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "======================================================================",
        "EMAIL MISMATCH & OWNER LINKAGE DIAGNOSTIC REPORT (READ-ONLY)",
        "======================================================================",
        f"Total Users Inspected        : {summary['total_users']}",
        f"Total Resumes Inspected      : {summary['total_resumes']}",
        f"Mismatched Resumes Found     : {summary['mismatched_resumes_count']}",
        f"Total Applications Inspected : {summary['total_applications']}",
        f"Reported Applications Found  : {summary['reported_applications_count']}",
        "----------------------------------------------------------------------",
    ]

    if report["mismatched_resumes"]:
        lines.append("\n[1] RESUMES WITH EMAIL MISMATCH OR MISSING OWNER:")
        for item in report["mismatched_resumes"]:
            lines.append(
                f"  - Resume ID #{item['resume_id']} | candidate_id={item['candidate_id']} "
                f"| account_email={item['account_email']} "
                f"| extracted_resume_email={item['extracted_resume_email']} "
                f"| reasons={', '.join(item['reasons'])}"
            )
    else:
        lines.append("\n[1] RESUMES WITH EMAIL MISMATCH OR MISSING OWNER: None found.")

    if report["reported_applications"]:
        lines.append("\n[2] APPLICATIONS MATCHED BY RESUME EMAIL OR WITH EMAIL MISMATCH:")
        for app in report["reported_applications"]:
            inferred_str = ", ".join(
                f"user_id={acc['user_id']} ({acc['account_email']})"
                for acc in app["inferred_accounts"]
            ) or "none"
            lines.append(
                f"  - App ID #{app['application_id']} (Job #{app['job_id']}) "
                f"| user_id={app['user_id']} "
                f"| candidate_name='{app['candidate_name']}' "
                f"| candidate_email='{app['candidate_email']}' "
                f"| extracted_resume_email='{app['extracted_resume_email']}' "
                f"| status='{app['status']}' "
                f"| inferred_accounts=[{inferred_str}] "
                f"| reasons={', '.join(app['reasons'])}"
            )
    else:
        lines.append("\n[2] APPLICATIONS MATCHED BY RESUME EMAIL OR WITH EMAIL MISMATCH: None found.")

    lines.append("\nNOTE: No accounts were merged and no application statuses were modified.")
    lines.append("======================================================================")
    return "\n".join(lines)


async def _main_async(as_json: bool = False) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        report = await generate_email_mismatch_report(session)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report_text(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report applications and resumes matched by resume email or with email mismatches (read-only)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format.",
    )
    args = parser.parse_args()
    asyncio.run(_main_async(as_json=args.json))


if __name__ == "__main__":
    main()
