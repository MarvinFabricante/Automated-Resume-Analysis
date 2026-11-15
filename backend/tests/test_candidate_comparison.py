import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath('backend'))

from fastapi import HTTPException
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.candidate_comparison_service import (
    compare_candidates_service,
    normalize_email,
    normalize_phone,
)

def run_coro(coro):
    """Drive an async coroutine synchronously without event loop IOCP conflicts."""
    g = coro.__await__()
    v = None
    while True:
        try:
            nxt = g.send(v)
            if hasattr(nxt, '__await__'):
                v = run_coro(nxt)
            else:
                v = nxt
        except StopIteration as e:
            return e.value


class MockDB:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.idx = 0

    async def execute(self, stmt):
        if self.idx < len(self.results):
            res = self.results[self.idx]
            self.idx += 1
            return res
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        res.scalar_one_or_none.return_value = None
        return res


class TestCandidateComparison(unittest.TestCase):

    def test_1_same_applicant_twice_rejected_422(self):
        """1. Comparing the same application/applicant twice is rejected with 422."""
        async def _test():
            mock_db = MockDB()
            await compare_candidates_service(
                db=mock_db,
                application_ids=[101, 101],
                reference_job_id=1
            )

        with self.assertRaises(HTTPException) as ctx:
            run_coro(_test())
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("cannot compare the same application", ctx.exception.detail.lower())

    def test_2_same_person_duplicate_email_or_phone_rejected_422(self):
        """2. Comparing two applications from the same person (same email or phone) is rejected with 422."""
        app1 = JobApplication(
            id=101,
            job_id=1,
            candidate_name="Maria Santos",
            candidate_email="maria.santos@example.com",
            phone="0918-111-2233",
            skills=["Machine operation"],
            status="SUBMITTED"
        )
        app2 = JobApplication(
            id=102,
            job_id=2,
            candidate_name="Maria C. Santos",
            candidate_email="  MARIA.SANTOS@EXAMPLE.COM  ",
            phone="09181112233",
            skills=["Quality inspection"],
            status="SUBMITTED"
        )

        res_apps = MagicMock()
        res_apps.scalars.return_value.all.return_value = [app1, app2]
        mock_db = MockDB([res_apps])

        async def _test():
            await compare_candidates_service(
                db=mock_db,
                application_ids=[101, 102]
            )

        with self.assertRaises(HTTPException) as ctx:
            run_coro(_test())
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("duplicate email", ctx.exception.detail.lower())

    def test_3_two_different_applicants_accepted_200(self):
        """3. Comparing two different applicants is accepted (200)."""
        job = JobDescription(
            id=1,
            job_title="Maintenance Technician",
            department="Engineering",
            skills_requirements="Hydraulics, Pneumatics, PLC",
            description="Machinery maintenance"
        )
        app1 = JobApplication(
            id=101,
            job_id=1,
            candidate_name="Candidate Alpha",
            candidate_email="alpha@example.com",
            phone="09190000001",
            skills=["Hydraulics", "Pneumatics"],
            status="SUBMITTED"
        )
        app2 = JobApplication(
            id=102,
            job_id=1,
            candidate_name="Candidate Beta",
            candidate_email="beta@example.com",
            phone="09190000002",
            skills=["PLC", "Electrical"],
            status="SUBMITTED"
        )

        res_apps = MagicMock()
        res_apps.scalars.return_value.all.return_value = [app1, app2]
        res_job = MagicMock()
        res_job.scalar_one_or_none.return_value = job
        res_all_jobs = MagicMock()
        res_all_jobs.scalars.return_value.all.return_value = [job]

        mock_db = MockDB([res_apps, res_job, res_all_jobs])

        async def _test():
            return await compare_candidates_service(
                db=mock_db,
                application_ids=[101, 102],
                reference_job_id=1
            )

        result = run_coro(_test())
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["reference_job"]["job_title"], "Maintenance Technician")
        self.assertFalse(result["is_cross_job"])
        self.assertIsNone(result["note"])

    def test_4_cross_job_comparison_calculates_against_reference_job(self):
        """4. Cross-job comparison calculates scores against the reference job."""
        job_target = JobDescription(
            id=1,
            job_title="Ceramic Kiln Supervisor",
            department="Production",
            skills_requirements="Kiln Operation, Team Leadership, Safety",
            description="Kiln supervisory role"
        )
        job_other = JobDescription(
            id=2,
            job_title="Forklift Operator",
            department="Logistics",
            skills_requirements="Forklift operation, Inventory",
            description="Logistics operation"
        )
        app1 = JobApplication(
            id=101,
            job_id=1,
            candidate_name="Kiln Lead",
            candidate_email="kiln.lead@example.com",
            phone="09191110001",
            skills=["Kiln Operation", "Safety"],
            relevance="5 years kiln experience",
            status="SUBMITTED"
        )
        app2 = JobApplication(
            id=102,
            job_id=2,
            candidate_name="Forklift Lead",
            candidate_email="forklift.lead@example.com",
            phone="09191110002",
            skills=["Forklift operation", "Team Leadership"],
            relevance="Warehouse team leader",
            status="SUBMITTED"
        )

        res_apps = MagicMock()
        res_apps.scalars.return_value.all.return_value = [app1, app2]
        res_job = MagicMock()
        res_job.scalar_one_or_none.return_value = job_target
        res_all_jobs = MagicMock()
        res_all_jobs.scalars.return_value.all.return_value = [job_target, job_other]

        mock_db = MockDB([res_apps, res_job, res_all_jobs])

        async def _test():
            return await compare_candidates_service(
                db=mock_db,
                application_ids=[101, 102],
                reference_job_id=1
            )

        result = run_coro(_test())
        self.assertTrue(result["is_cross_job"])
        self.assertIn("Ceramic Kiln Supervisor", result["note"])
        self.assertIn("transferable skills", result["note"])
        self.assertEqual(result["reference_job"]["id"], 1)

        c1 = next(c for c in result["candidates"] if c["application_id"] == 101)
        c2 = next(c for c in result["candidates"] if c["application_id"] == 102)
        self.assertEqual(c1["applied_job_title"], "Ceramic Kiln Supervisor")
        self.assertEqual(c2["applied_job_title"], "Forklift Operator")

    def test_5_cross_job_comparison_includes_transferable_skills(self):
        """5. Cross-job comparison includes transferable skills in the result."""
        job_ref = JobDescription(
            id=1,
            job_title="Operations Supervisor",
            department="Operations",
            skills_requirements="Team Leadership, Safety Compliance, Lean Manufacturing",
            description="Shift supervisor in tile plant"
        )
        job_pack = JobDescription(
            id=2,
            job_title="Packaging Line Lead",
            department="Packaging",
            skills_requirements="Packaging machinery, Team Leadership",
            description="Packing supervisor"
        )
        app1 = JobApplication(
            id=101,
            job_id=1,
            candidate_name="Operations Lead",
            candidate_email="ops.lead@example.com",
            phone="09192220001",
            skills=["Team Leadership", "Safety Compliance"],
            relevance="Plant supervisor",
            status="SUBMITTED"
        )
        app2 = JobApplication(
            id=102,
            job_id=2,
            candidate_name="Packaging Lead",
            candidate_email="pack.lead@example.com",
            phone="09192220002",
            skills=["Packaging machinery", "Team Leadership"],
            relevance="Packaging line supervisor",
            status="SUBMITTED"
        )

        res_apps = MagicMock()
        res_apps.scalars.return_value.all.return_value = [app1, app2]
        res_job = MagicMock()
        res_job.scalar_one_or_none.return_value = job_ref
        res_all_jobs = MagicMock()
        res_all_jobs.scalars.return_value.all.return_value = [job_ref, job_pack]

        mock_db = MockDB([res_apps, res_job, res_all_jobs])

        async def _test():
            return await compare_candidates_service(
                db=mock_db,
                application_ids=[101, 102],
                reference_job_id=1
            )

        result = run_coro(_test())
        c2 = next(c for c in result["candidates"] if c["application_id"] == 102)
        self.assertIn("transferable_skills", c2)
        self.assertIsInstance(c2["transferable_skills"], list)
        self.assertIn("matched_skills", c2)
        self.assertIsInstance(c2["matched_skills"], list)


if __name__ == "__main__":
    unittest.main()
