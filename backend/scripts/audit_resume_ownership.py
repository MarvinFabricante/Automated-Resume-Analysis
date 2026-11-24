"""Read-only ownership audit. Run from backend: python -m scripts.audit_resume_ownership.

Outputs JSON to stdout; redirect to a protected file for manual review. Email equality
is evidence for review, never proof of ownership. Historical upload identity cannot
be reconstructed from extracted email alone. This script has no apply/merge mode.
"""
import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import engine
from app.models.user import User
from app.models.job_application import JobApplication
from app.models.resume import Resume


def normalized(value):
    return (value or '').strip().lower()


async def audit(db):
    users = {u.id: normalized(u.email) for u in (await db.execute(select(User))).scalars()}
    by_email = {email: uid for uid, email in users.items()}
    findings = []
    apps = list((await db.execute(select(JobApplication))).scalars())
    for app in apps:
        extracted = normalized(app.resume_email)
        contact = normalized(app.candidate_email)
        reasons = []
        if not app.user_id:
            reasons.append('unlinked_application')
        elif app.user_id not in users:
            reasons.append('missing_account')
        elif extracted and users[app.user_id] != extracted:
            reasons.append('resume_account_email_mismatch')
        if extracted and extracted in by_email:
            reasons.append('resume_email_matches_account_requires_provenance_review')
        if contact and contact != users.get(app.user_id):
            reasons.append('contact_account_email_mismatch')
        if reasons:
            findings.append({'record': 'application', 'id': app.id, 'owner_id': app.user_id,
                             'resume_email_account_id': by_email.get(extracted), 'reasons': reasons})
    for resume in (await db.execute(select(Resume))).scalars():
        payload = resume.parsed_data if isinstance(resume.parsed_data, dict) else {}
        extracted = normalized(payload.get('email') or (payload.get('personal') or {}).get('email'))
        reasons = []
        if resume.candidate_id not in users:
            reasons.append('missing_account')
        if extracted and extracted != users.get(resume.candidate_id):
            reasons.append('resume_account_email_mismatch')
        if extracted in by_email:
            reasons.append('resume_email_matches_account_requires_provenance_review')
        linked_owners = {a.user_id for a in apps if a.resume_url and a.resume_url == resume.file_url and a.user_id}
        if linked_owners and linked_owners != {resume.candidate_id}:
            reasons.append('resume_application_owner_conflict')
        if reasons:
            findings.append({'record': 'resume', 'id': resume.id, 'owner_id': resume.candidate_id,
                             'resume_email_account_id': by_email.get(extracted), 'reasons': reasons})
    return {'mode': 'report_only', 'findings': findings,
            'note': 'Verify upload/authentication provenance before any manual ownership correction. Do not merge accounts.'}


async def main():
    async with AsyncSession(engine) as db:
        print(json.dumps(await audit(db), indent=2))
        await db.rollback()


if __name__ == '__main__':
    asyncio.run(main())
