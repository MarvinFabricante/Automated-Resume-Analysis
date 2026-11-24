# Mariwasa recruitment beta verification

Use a test applicant and job. Record an existing application's status before testing; extraction, confirmation and rescoring must leave that status unchanged. Run the applicant checks in both public application and signed-in candidate flows.

## Requirement confirmations

- [ ] Create a job requiring `Communication, Billing, Reporting, Research, Scheduling, CRM software, Data Entry, Problem-Solving`, plus two certification and two experience requirements. Upload a resume that lacks them. Every unresolved item appears in a grouped question, including CRM software and Data Entry beyond the fifth item.
- [ ] Repeat with `Kustomer` and `Excel` in the resume. CRM software and Data Entry show **Possible match** and still request confirmation. Also check Zendesk, Shopify admin, order creation and invoicing. Related terms are configured in `backend/app/services/requirement_related_terms.json`; callers can override entries with `matching_config.related_terms`.
- [ ] Leave the groups unanswered. HR requirement evidence and criterion statuses show **Not confirmed** or **Possible match**; unanswered skills do not appear as failed requirements.
- [ ] Answer CRM software **Yes with experience** and Data Entry **Some experience**, add years/details, and submit. Both contribute the same skill credit as explicitly listing those skills on the resume. HR sees **Confirmed by applicant**, the answers, and the details.
- [ ] Change an answer to **No**, then clear it. No removes its credit; clearing restores the neutral state. Repeat with BOSH while the resume lists `BOSH Certified` to check that aliases cannot override No.
- [ ] Refresh the preview, return to the form, and allow background analysis to finish. Saved answers and HR evidence survive. Application status stays unchanged.
- [ ] Resume an older draft with only a text follow-up question or an incomplete grouped response. Missing requirements are added without duplicating existing items or losing existing answers.
- [ ] A job title without work dates or duration still prompts for experience confirmation.

## Skills extraction

- [ ] Upload a text/PDF resume containing the following. Problem-Solving stays a single skill and matches `Problem-Solving` on the job; neither `Problem` nor `Solving` appears alone.

```text
Core Skills: Communication, attention to detail, time management, problem-
solving, adaptability
```

- [ ] Check `Multi-tasking, Self-motivated, Wi-Fi, E-commerce, Back-end, Point-of-Sale`. Commas, semicolons, bullets, pipes, newlines and spaced slashes separate skills; internal hyphens remain intact.

## Education extraction and attainment

- [ ] Upload Basagre_Resume_Updated.pdf when available, or a test document containing this supplied education block:

```text
EDUCATION
STI Colleges Ortigas-Cainta, June 2023 - Expected 2027
Bachelor of Science in Computer Science
4th Year College Student
```

- [ ] Exactly one education card appears: institution `STI Colleges Ortigas-Cainta`, status **Undergraduate / In progress**, start 2023, expected graduation 2027. No `Degree / Course` card or invented graduation appears.
- [ ] The matching display reads **Bachelor's degree in Computer Science (4th year, expected 2027)**. The underlying education ranking still treats the degree as in progress.
- [ ] Repeat with `BS Computer Science`, `B.S. in Computer Science`, and degree/course on separate lines. A completed degree displays **Bachelor's degree in Computer Science** without repeated words.
- [ ] A degree with `Started June 2023` does not become Graduated. An institution with dates but no degree keeps its degree fields empty. Repeated blocks merge to one entry.
- [ ] Repeat the sample in a pipe-delimited row; the expected year and year level remain in the display.

## Existing applications and interviews

- [ ] Open existing applications with null clarification fields. Candidate details, HR comparisons and interview lists load without errors.
- [ ] Open an existing interview's details and calendar view, including older interviews with empty logs. Dates, participants and messages remain usable.
- [ ] In test data, schedule and reschedule an interview, verify calendar details, and open it again. Confirm application statuses changed only through an explicit existing user action, never extraction or rescoring.

## Automated checks

From the repository root, use an isolated feedback database for matching tests:

```bash
FEEDBACK_DB_PATH=/tmp/mariwasa-beta-regression-feedback.db .venv/bin/python -m pytest backend/tests/services/test_beta_requirement_fixes.py backend/tests/extractors backend/tests/services/test_job_matching_service.py backend/tests/services/test_matching_hierarchy_and_novalue.py backend/tests/services/test_interview_service.py backend/tests/repositories/test_interview_repository.py backend/tests/controllers/test_interview_controller.py backend/tests/controllers/test_job_matching_controller.py -q
cd frontend
node --test tests/*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
```

The automated sample uses the supplied text; the original PDF and the browser checklist require separate manual verification. The existing startup migration `add_requirement_confirmations` supplies the two nullable JSON columns when absent. This patch adds no new API fields or migrations and performs no bulk updates to applications.

## Deactivated account recovery

- Register using a deactivated email with different capitalization/spaces: both recovery choices appear. Repeat via password login and Google registration.
- With an active email, registration shows the usual already-registered message and sign-in link. Wrong login passwords do not show recovery choices.
- Reactivate: paste a six-digit code; test a wrong code, expired code, five wrong attempts, and resend countdown. A valid code signs in to the original profile; withdrawn applications remain withdrawn.
- Start fresh from login: the registration form retains the email and asks for new name/password. Both recovery choices remain available after submitting.
- Start fresh: before verification and before clicking **Yes, start fresh**, the old data remains. Cancel at either step without deleting anything.
- Confirm fresh start: old resume files, extracted text, contact details and personal history are removed; the new account is empty. HR sees only **Previous application on record (anonymized)** when the new applicant applies.
- Check keyboard focus, code paste/autofill, loading/error/success states, and the dialog on a narrow mobile screen.
- Deployment: from `backend`, run `python -m migrations.add_active_email_uniqueness` after the lifecycle migration. Roll back this index with `--downgrade` before rolling back lifecycle columns. Existing active emails that collide after trimming/lowercasing must be resolved before the index can be created; the migration never merges or deletes accounts.
- API compatibility: existing registration success bodies and error-code aliases remain supported. Purging through `/auth/fresh-start` or `/auth/register` with `fresh_start: true` now requires `verification_token` from `/auth/fresh-start/verify` and `confirm_fresh_start: true`. Request the code through `/auth/fresh-start/request-otp`; unverified legacy purge requests are intentionally rejected.
