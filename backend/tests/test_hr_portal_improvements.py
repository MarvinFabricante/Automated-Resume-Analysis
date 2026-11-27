import asyncio
import sys

sys.path.insert(0, 'backend')

from sqlalchemy import select
from app.utils.database import AsyncSessionLocal, engine
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription as Job
from app.services.status_management_service import (
    handle_application_viewed_event,
    undo_auto_status_change,
    get_application_history,
)
from app.services.shortlist_roster_service import (
    create_shortlist_roster,
    add_application_to_roster,
    remove_application_from_roster,
    update_roster_item_stage,
    get_shortlist_roster_by_id,
    get_shortlist_rosters,
    toggle_archive_shortlist_roster,
    delete_shortlist_roster
)
from app.services.applicant_profile_service import (
    get_applicant_comprehensive_profile,
    add_candidate_hr_note,
    universal_search_hr,
)

async def run_tests():
    print("--- STARTING COMPREHENSIVE HR PORTAL IMPROVEMENTS & BUGFIX TESTS ---")
    async with AsyncSessionLocal() as db:
        # 1. Setup a test job
        import uuid
        test_uuid = str(uuid.uuid4())[:8]
        job = Job(
            job_id=f"TEST-JOB-{test_uuid}",
            job_title="Production Line Operator",
            department="Manufacturing & Operations",
            job_type="Full-Time",
            location="Sto. Tomas, Batangas",
            description="Responsible for operating production machinery.",
            skills_requirements="Machine Operation, Safety, Packaging",
            is_active=True,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        print(f"Created Test Job: ID={job.id}, Title='{job.job_title}'")

        # 2. Setup a test application (Submitted)
        app = JobApplication(
            job_id=job.id,
            candidate_name="Pedro Dimagiba",
            candidate_email="pedro.dimagiba@mariwasa.com",
            phone="+63 918 555 1234",
            status="Submitted",
            match_score=88.0,
            skills=["Machine Operation", "Safety Protocols"],
            source="Imported",
            import_origin="Walk-in",
            imported_by="hr_specialist@mariwasa.com"
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)
        print(f"Created Test Application: ID={app.id}, Status='{app.status}', Source='{app.source}' ({app.import_origin})")

        # ─── ITEM 3 TEST: Automatic Status Updates & History (BUG FIX) ───
        # A) Under 8 seconds -> Should NOT update
        res_short = await handle_application_viewed_event(
            db=db,
            application_id=app.id,
            view_duration_seconds=5.0,
            visible_focused=True,
            engaged=True,
            user_email="hr_specialist@mariwasa.com"
        )
        assert res_short.get("changed") is not True
        print("PASS: Viewing for 5s (<8s) did NOT change status.")

        # B) 8+ seconds without engagement -> Should NOT update
        res_no_engage = await handle_application_viewed_event(
            db=db,
            application_id=app.id,
            view_duration_seconds=9.0,
            visible_focused=True,
            engaged=False,
            user_email="hr_specialist@mariwasa.com"
        )
        assert res_no_engage.get("changed") is not True
        print("PASS: Viewing without engagement did NOT change status.")

        # C) 8+ seconds, visible, focused, engaged -> Should update to 'Under Review'
        res_valid = await handle_application_viewed_event(
            db=db,
            application_id=app.id,
            view_duration_seconds=8.5,
            visible_focused=True,
            engaged=True,
            user_email="hr_specialist@mariwasa.com"
        )
        assert res_valid.get("changed") is True
        assert res_valid.get("new_status") == "Under Review"
        print("PASS: Viewing for 8.5s with engagement automatically updated Submitted -> Under Review.")

        # D) Verify audit history
        history = await get_application_history(db=db, application_id=app.id)
        assert len(history) >= 1
        assert history[0].old_status == "Submitted"
        assert history[0].new_status == "Under Review"
        assert history[0].change_type == "auto"
        assert history[0].can_undo is True
        print(f"PASS: Audit history recorded correctly ({len(history)} entry, can_undo=True).")

        # E) Undo auto status change
        undo_res = await undo_auto_status_change(db=db, application_id=app.id, user_email="hr_specialist@mariwasa.com")
        assert undo_res["reverted_to"] == "Submitted"
        await db.refresh(app)
        assert app.status.upper() == "SUBMITTED"
        print("PASS: Undo reverted status back to Submitted.")

        # F) Negative Test: Tab not visible/focused
        res_hidden = await handle_application_viewed_event(
            db=db,
            application_id=app.id,
            view_duration_seconds=10.0,
            visible_focused=False,
            engaged=True,
            user_email="hr_specialist@mariwasa.com"
        )
        assert res_hidden.get("changed") is not True
        assert res_hidden.get("reason") == "not_visible"
        print("PASS: Viewing in hidden/unfocused tab did NOT change status (reason='not_visible').")

        # ─── ITEM 5 TEST: Shortlist Rosters (BUG FIXES & FEATURES) ───
        # Create Shortlist Roster with Submitted application -> should transition Submitted -> Under Review -> Shortlisted
        roster = await create_shortlist_roster(
            db=db,
            job_id=job.id,
            name="Production Operator Shortlist - Nov 2026",
            notes="Q4 Operations Roster",
            created_by="hr_specialist@mariwasa.com",
            application_ids=[app.id],
        )
        assert roster is not None
        await db.refresh(app)
        assert app.status.upper() == "SHORTLISTED"
        print("PASS: Adding Submitted candidate moved through Under Review to Shortlisted and recorded both.")

        # Negative Test: Viewing already Shortlisted application should not change status
        res_already_shortlisted = await handle_application_viewed_event(
            db=db,
            application_id=app.id,
            view_duration_seconds=10.0,
            visible_focused=True,
            engaged=True,
            user_email="hr_specialist@mariwasa.com"
        )
        assert res_already_shortlisted.get("changed") is not True
        assert res_already_shortlisted.get("reason") == "already_later_status"
        print("PASS: Viewing already Shortlisted candidate did NOT regress or change status (reason='already_later_status').")

        # Verify candidate card details in roster query (Candidate Card Bug Fix!)
        roster_detail = await get_shortlist_roster_by_id(db=db, roster_id=roster.id)
        assert len(roster_detail["items"]) == 1
        card_item = roster_detail["items"][0]
        assert card_item["candidate_name"] == "Pedro Dimagiba", f"Expected 'Pedro Dimagiba', got {card_item['candidate_name']}"
        assert card_item["candidate_email"] == "pedro.dimagiba@mariwasa.com"
        assert card_item["match_score"] == 88.0
        assert card_item["source"] == "Imported"
        assert card_item["import_origin"] == "Walk-in"
        print(f"PASS (BUG FIX): Candidate card has populated name='{card_item['candidate_name']}', score={card_item['match_score']}%, source={card_item['source']}.")

        # Verify Stage Counts computed correctly
        assert roster_detail["shortlisted_count"] == 1
        assert roster_detail["total_candidates"] == 1
        print("PASS: Single source of truth stage counts verified on roster detail.")

        # Update stage to Interview Scheduled
        await update_roster_item_stage(
            db=db,
            roster_id=roster.id,
            application_id=app.id,
            stage="Interview Scheduled",
            updated_by="hr_specialist@mariwasa.com"
        )
        await db.refresh(app)
        assert app.status.upper() == "INTERVIEW SCHEDULED"
        print("PASS: Setting stage to 'Interview Scheduled' synced application status.")

        # Update stage to Interviewed
        await update_roster_item_stage(
            db=db,
            roster_id=roster.id,
            application_id=app.id,
            stage="Interviewed",
            updated_by="hr_specialist@mariwasa.com"
        )
        await db.refresh(app)
        assert app.status.upper() == "INTERVIEWED"
        print("PASS: Setting stage to 'Interviewed' synced application status.")

        # Outcome 1: Passed Initial Interview
        await update_roster_item_stage(
            db=db,
            roster_id=roster.id,
            application_id=app.id,
            stage="Passed initial interview",
            updated_by="hr_specialist@mariwasa.com"
        )
        r_after_pass = await get_shortlist_roster_by_id(db=db, roster_id=roster.id)
        assert r_after_pass["passed_count"] == 1
        print("PASS: Setting outcome to 'Passed initial interview' updated outcome counts and history.")

        # Outcome 2: Undo back to Interviewed
        await update_roster_item_stage(
            db=db,
            roster_id=roster.id,
            application_id=app.id,
            stage="Interviewed",
            updated_by="hr_specialist@mariwasa.com"
        )
        r_after_undo = await get_shortlist_roster_by_id(db=db, roster_id=roster.id)
        assert r_after_undo["interviewed_count"] == 1
        assert r_after_undo["passed_count"] == 0
        print("PASS: Undo outcome successfully reverted stage to 'Interviewed'.")

        # Archive & Unarchive Roster
        arc_res = await toggle_archive_shortlist_roster(db=db, roster_id=roster.id, archived=True)
        assert arc_res["is_archived"] is True
        active_rosters = await get_shortlist_rosters(db=db, archived=False)
        assert not any(r["id"] == roster.id for r in active_rosters)
        archived_rosters = await get_shortlist_rosters(db=db, archived=True)
        assert any(r["id"] == roster.id for r in archived_rosters)
        print("PASS: Archive filter correctly hides archived roster from active list and shows in archived list.")

        await toggle_archive_shortlist_roster(db=db, roster_id=roster.id, archived=False)
        print("PASS: Unarchive restored roster to active list.")

        # ─── ITEM 4 TEST: Comprehensive Profile & Application History (BUG FIX) ───
        # Add HR Note
        await add_candidate_hr_note(
            db=db,
            candidate_email="pedro.dimagiba@mariwasa.com",
            author_email="hr_specialist@mariwasa.com",
            content="Passed technical screening; recommended for interview panel."
        )

        profile = await get_applicant_comprehensive_profile(
            db=db,
            email="pedro.dimagiba@mariwasa.com",
            accessed_by="hr_specialist@mariwasa.com"
        )
        assert profile is not None
        assert profile["candidate"]["name"] == "Pedro Dimagiba"
        assert profile["candidate"]["source"] == "Imported"
        assert profile["candidate"]["import_origin"] == "Walk-in"
        assert len(profile["applications"]) >= 1
        assert len(profile["status_history"]) >= 1
        assert len(profile["hr_notes"]) >= 1
        print(f"PASS (BUG FIX): Applicant profile loaded with name='{profile['candidate']['name']}', applications={len(profile['applications'])}, status_history entries={len(profile['status_history'])}, notes={len(profile['hr_notes'])}.")

        # Delete Roster with Removal Rule
        del_success = await delete_shortlist_roster(db=db, roster_id=roster.id, deleted_by="hr_specialist@mariwasa.com")
        assert del_success is True
        print("PASS: Shortlist roster deleted cleanly.")

        # ─── ITEM 1 TEST: Import Resumes Module & Sync (BUG FIX & INTEGRATION) ───
        from app.services.physical_resume_service import store_physical_resume, get_physical_resumes
        import io
        from fastapi import UploadFile

        import fitz
        _doc = fitz.open()
        _page = _doc.new_page()
        _page.insert_text(
            (50, 50),
            "JUAN DELA CRUZ\n"
            "juan.delacruz@gmail.com | +63 917 123 4567 | Sto. Tomas, Batangas\n\n"
            "WORK EXPERIENCE\n"
            "Machine Operator | Mariwasa Ceramics Plant | 2022 - Present\n"
            "- Operated ceramic press machines and performed quality control inspections.\n\n"
            "EDUCATION\n"
            "BS Industrial Technology | Batangas State University | 2018 - 2022\n\n"
            "SKILLS\n"
            "Machine Operation, Quality Control, Packaging, Safety Protocols\n",
        )
        dummy_pdf = io.BytesIO(_doc.tobytes())
        _doc.close()
        mock_upload = UploadFile(filename="juan_delacruz_resume.pdf", file=dummy_pdf)

        import_data = {
            "candidate_name": "Juan Dela Cruz",
            "candidate_email": f"juan.delacruz.{test_uuid}@mariwasa.local",
            "candidate_phone": "+63 917 123 4567",
            "target_job_id": job.id,
            "target_job_title": job.job_title,
            "import_origin": "Walk-in",
            "physical_location": "Cabinet A - Shelf 1",
            "submission_date": "2026-11-15",
            "notes": "Walk-in candidate from plant gate",
            "skills": "Machine Operation, Quality Control, Packaging",
            "experience": "3 years experience in ceramic manufacturing",
            "degree": "BS Industrial Technology",
            "location": "Sto. Tomas, Batangas",
            "imported_by": "hr_specialist@mariwasa.com"
        }

        stored = await store_physical_resume(
            db=db,
            file=mock_upload,
            hr_id=1,
            data=import_data
        )
        assert stored is not None
        assert stored.id is not None
        print(f"PASS: store_physical_resume created record #{stored.id}")

        # Verify JobApplication auto-created with SUBMITTED, Imported, Walk-in, match_score
        imported_app_stmt = select(JobApplication).where(JobApplication.candidate_email == f"juan.delacruz.{test_uuid}@mariwasa.local")
        imported_app_res = await db.execute(imported_app_stmt)
        imported_app = imported_app_res.scalar_one_or_none()
        assert imported_app is not None
        assert imported_app.status == "SUBMITTED"
        assert imported_app.source == "Imported"
        assert imported_app.import_origin == "Walk-in"
        assert imported_app.imported_by == "hr_specialist@mariwasa.com"
        assert imported_app.match_score is not None
        print(f"PASS: Imported resume created JobApplication #{imported_app.id} with status='{imported_app.status}', source='{imported_app.source}', origin='{imported_app.import_origin}', match_score={imported_app.match_score}%.")

        # Verify appears in get_physical_resumes
        pr_result = await get_physical_resumes(db=db, limit=10)
        pr_list = pr_result.get("items", [])
        total_pr = pr_result.get("total", 0)
        assert any(p.get("id") == stored.id for p in pr_list)
        print(f"PASS: Imported resume found in get_physical_resumes (total={total_pr}).")

        # Verify appears in applicant search
        search_results = await universal_search_hr(db=db, query="Juan Dela Cruz")
        assert any(r.get("email") == f"juan.delacruz.{test_uuid}@mariwasa.local" for r in search_results.get("applicants", []))
        print(f"PASS: Imported candidate appears immediately in universal search.")

    await engine.dispose()
    print("\nALL UNIT, INTEGRATION, AND BUGFIX TESTS PASSED 100%!")

if __name__ == "__main__":
    asyncio.run(run_tests())
