# Mariwasa Recruitment Lifecycle & Privacy Rules — Manual QA Checklist

Use this checklist to verify all 7 recruitment lifecycle, data privacy, retention, reactivation, end-state, and multi-application rules end-to-end.

---

## 1. Not-Shortlisted Trigger
- [ ] **Shortlist Prompt Options**: In HR Screening Portal, shortlist a subset of applicants and open **Finalize Shortlist Roster**. Verify all 3 options appear:
  - *Keep them under review until the job is closed* (selected by default)
  - *Notify them as Not Selected when the shortlist is finalized*
  - *Decide later*
- [ ] **Affected Count & Message Preview**: Select *Notify them as Not Selected when the shortlist is finalized* and verify:
  - Exact count of non-shortlisted applicants (`Submitted` / `Under Review` not on a roster) is shown.
  - Rendered Not Selected email subject and body preview are displayed before submitting.
  - Submit stays disabled until the explicit confirmation checkbox is checked (never applied silently).
- [ ] **Change Policy Before Finalizing**: Uncheck *Finalize immediately*, save as draft, open the Roster Pipeline modal, change the Non-Shortlisted Policy dropdown, and then click **Preview & Finalize Shortlist**. Confirm the dropdown locks once finalized.
- [ ] **Editable Template Guard**: In Admin → System Settings → Notification Templates, edit the *Not Selected* template. Attempt to insert `{match_score}` or `"scoring weights"` and verify the server rejects it. Save clean plain text and confirm the shortlist preview reflects it.
- [ ] **Feedback Report Viewable**: Sign in as a Not Selected applicant and verify the feedback report remains viewable.

## 2. Job Opening Lifecycle (`DRAFT -> ACTIVE -> CLOSED -> ARCHIVED`)
- [ ] **Role Restriction**: Confirm only HR and Admin can change job status (applicant API calls return `403`).
- [ ] **Close Job Confirmation**: On Admin → Job Management, click **Close job** on an `ACTIVE` job. Verify the confirmation dialog displays the exact count of non-shortlisted applicants who will become `Not Selected` and how many shortlisted/interviewed applicants remain untouched.
- [ ] **Auto Not Selected (Once Only)**: Confirm non-shortlisted applicants become `Not Selected` with status history reason `"Position closed"` and receive one notification/email. Shortlisted, Interview Scheduled, and Interviewed applicants remain untouched.
- [ ] **Closed Rejects Applications**: Verify the Closed job disappears from Smart Matches and open jobs; opening it directly shows `"This position is closed"` and server `POST /applications/` rejects with `"This position is closed"`.
- [ ] **Reopen (`CLOSED -> ACTIVE`)**: Click **Reopen** on a Closed job and verify it becomes `ACTIVE` again. Closing it a second time does NOT re-notify already-Not-Selected applicants.
- [ ] **Archive (`ARCHIVED` Terminal)**: Click **Archive** on a job. Verify it disappears from the default list until **"Show archived"** is checked, has no Reopen button, rejects reopen via API (`400`), and remains included in reports/analytics.
- [ ] **Audit Log**: Confirm every status transition is logged in Audit Logs with actor, timestamp, old status, and new status.

## 3. Account Deletion & Withdrawal
- [ ] **Single Application Withdrawal**: As an applicant on Application Tracking, click **Withdraw Application** on an active application, confirm in the modal, and verify:
  - Status changes to `Withdrawn by applicant`.
  - Any scheduled interview is cancelled and removed from calendars/rosters.
  - Active slot count (`X / 3 active slots`) decreases immediately so the applicant can apply to another role.
  - HR receives an in-app notification.
- [ ] **Account Deletion (Password or OTP)**: In Candidate → Account Settings → Security → **Request Account Deletion**, verify both confirmation tabs (*Confirm with Password* and *Confirm with Email OTP*). Confirm deletion and verify:
  - Account is deactivated immediately and signed out everywhere (old JWT returns `401`).
  - All active applications become `Withdrawn by applicant` (reason `"Account deletion requested"`), scheduled interviews cancel, and HR receives a notification listing affected applications.
- [ ] **No Hard-Delete for Applicants**:
  - In Admin → Users, verify **Delete Permanently** is hidden for `CANDIDATE` rows and `DELETE /admins/users/{candidate_id}` returns `403`.
  - In HR Screening Portal & Physical Resumes, verify applicant applications and resumes cannot be hard-deleted (`403` on API).

## 4. Retention Period & Anonymization
- [ ] **System Configuration**: In Admin → System Settings, verify default **Data Retention Window** is `12` months and **Reapplication Cooldown** is `0` days (none), both configurable and persisted.
- [ ] **Dry Run**: Click **Run Dry Run** and verify a run log row appears with `Mode: Dry Run`, eligible counts, and `Active Skipped`, while no personal data or files are modified.
- [ ] **Live Anonymization**: Run live anonymization on an expired deactivated/resolved test record and verify:
  - Name, email, phone, extracted text, resume file on disk/storage, and personal message content are scrubbed.
  - Stable token (`Anonymized applicant #XXXXXX`), job, dates, status history, decision, and scores are preserved.
  - Any applicant with an active application is skipped and never purged.
  - Re-running the job is idempotent (0 duplicate changes).
- [ ] **Repeat-Applicant Flag**: Register a new account with the same email as an anonymized record, apply to a job, open HR Applicant Profile, and verify the amber banner `"Previous application on record (anonymized)"` appears without exposing any old personal data.

## 5. Reactivation & Re-Registration
- [ ] **Case-Insensitive Duplicate Blocking**: Try registering with an existing active email using different casing/spaces (e.g. `  User@Example.COM `) -> blocked with `409` clear message.
- [ ] **OTP Reactivation**: Attempt to register with a deactivated (not-yet-purged) email -> modal offers **Reactivate Account (Email OTP)** or **Start Fresh**. Choose Reactivate, verify 6-digit OTP (10-min expiry, max 5 attempts) -> profile & history restore, previously withdrawn applications remain withdrawn.
- [ ] **Fresh Start Before Purge**: Deactivate again, choose **Start Fresh (New Empty Account)** -> old account is immediately anonymized, new account starts completely empty with zero restored applications.

## 6. Clear End States & Messaging Closure
- [ ] **Passed End State**: Mark an applicant `Passed initial interview`. Verify applicant sees `"Passed Initial Interview – Endorsed for next stage"`, clear message that HR will contact them outside the system, read-only state (no Withdraw/Reschedule), and 1 active slot freed.
- [ ] **Not Selected End State**: Mark an applicant `Not Selected`. Verify `"Not selected"` status, feedback report stays viewable, account stays active, and 1 active slot freed.
- [ ] **Dashboard Groups**: On Candidate Dashboard, verify tabs **Active**, **Completed**, and **Withdrawn** with friendly empty states (never a blank screen).
- [ ] **Messaging Replies & 30-Day Closure**:
  - Verify applicant can reply to HR while application is active or within 30 days of resolution.
  - Verify withdrawn application thread is read-only immediately (`"This conversation is closed"`).
  - Verify finished application thread locks after the configured closure period (default 30 days) with `"This conversation is closed"`.

## 7. Shortlisted in One of Three Active Applications
- [ ] **Independent Applications**: Shortlist an applicant for 1 of 3 active roles; verify the other 2 remain untouched (never auto-withdrawn).
- [ ] **HR Multi-Application Flag**: Open HR Applicant Profile and verify `"This applicant has N other active applications"` with position and status chips.
- [ ] **Combined Interview Invite**: Shortlist the same applicant for 2 roles, open Schedule Interview modal (confirm AI Voice Language dropdown is removed), verify the **Combined Interview Available** checkboxes appear (secondary role untickable), schedule once -> single calendar event, single email listing both positions, single SMS; each role keeps its own independent pass/fail decision.
- [ ] **Post-Pass On Hold vs Continue**: Mark 1 role `Passed initial interview` in Roster Pipeline -> verify prompt to **Place Remaining On Hold** or **Continue Remaining**. Verify `On Hold` still counts toward the 3-active limit, notifies the applicant, and can be **Resumed** from Applicant Profile.
- [ ] **Switchable "Hired Elsewhere"**: Confirm **Withdraw – Hired Elsewhere** is hidden/403 by default; enable `"Allow 'Withdrawn – hired elsewhere in company'"` in System Settings -> HR can mark remaining applications `"Withdrawn – hired elsewhere in company"`.
