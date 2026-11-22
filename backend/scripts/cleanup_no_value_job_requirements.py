"""
Optional one-time cleanup script to convert existing no-value strings
('None', 'N/A', 'Wala', '-', 'No requirement', whitespace, etc.) in
JobDescription requirement columns to SQL NULL.

Usage (from backend/ directory):
  ./venv/bin/python scripts/cleanup_no_value_job_requirements.py          # Dry run
  ./venv/bin/python scripts/cleanup_no_value_job_requirements.py --apply  # Apply changes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend/ is importable when run directly as a script
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.job_description import JobDescription  # noqa: E402
from app.services.requirement_rules import is_no_value  # noqa: E402

REQUIREMENT_COLUMNS = (
    "skills_requirements",
    "education_requirements",
    "experience_requirements",
    "certifications_requirements",
)


async def cleanup_no_value_job_requirements(
    db: AsyncSession,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Scan JobDescription requirement columns and convert standalone no-value
    strings to None (SQL NULL). Leaves real requirements intact (including
    phrases like 'None of the above, but must know Excel'). Never modifies
    application statuses or shortlist rosters.
    """
    result = await db.execute(select(JobDescription))
    jobs = result.scalars().all()

    changes: list[dict[str, Any]] = []
    fields_cleaned = 0

    for job in jobs:
        job_cleaned_fields: dict[str, str] = {}
        for col in REQUIREMENT_COLUMNS:
            raw_val = getattr(job, col, None)
            if raw_val is not None and is_no_value(raw_val):
                job_cleaned_fields[col] = raw_val
                fields_cleaned += 1
                if not dry_run:
                    setattr(job, col, None)

        if job_cleaned_fields:
            changes.append(
                {
                    "id": job.id,
                    "job_id": job.job_id,
                    "job_title": job.job_title,
                    "cleaned_fields": job_cleaned_fields,
                }
            )

    if not dry_run and changes:
        await db.commit()

    return {
        "dry_run": dry_run,
        "scanned_jobs": len(jobs),
        "jobs_updated": len(changes),
        "fields_cleaned": fields_cleaned,
        "changes": changes,
    }


async def _main(apply_changes: bool) -> int:
    from app.utils.database import async_session

    async with async_session() as db:
        summary = await cleanup_no_value_job_requirements(db, dry_run=not apply_changes)

    mode = "APPLY" if apply_changes else "DRY-RUN"
    print(
        f"[{mode}] Scanned {summary['scanned_jobs']} job(s); "
        f"matched {summary['jobs_updated']} job(s) / {summary['fields_cleaned']} field(s)."
    )
    for item in summary["changes"]:
        print(f"  - {item['job_id']} ({item['job_title']}): {item['cleaned_fields']}")

    if not apply_changes and summary["fields_cleaned"] > 0:
        print("Re-run with --apply to persist NULL cleanup.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean up legacy 'None'/no-value requirement strings in JobDescription."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes to the database (default is dry-run).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args.apply)))
