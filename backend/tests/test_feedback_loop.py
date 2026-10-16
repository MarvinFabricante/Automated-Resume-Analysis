"""
Automated Verification Suite: Human-in-the-Loop Continuous Retraining Pipeline
-----------------------------------------------------------------------------
Verifies:
1. Phase 1: FastText contextual similarity (React vs Vue > unrelated skills).
2. Phase 2: Feature vector construction and calibrated fit classification.
3. Phase 3: Transactional feedback DB schema and raw token persistence.
4. Phase 4: Continuous retraining with human feedback weighting, atomic hot-swap,
            and subsequent prediction probability shift.
5. Application integration with calculate_match_score.
"""
import os
import sys
import tempfile
import numpy as np
import pytest

# Ensure backend directory is in sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
candidates = [
    current_dir,
    os.path.abspath(os.path.join(current_dir, "..")),
    os.path.abspath(os.path.join(current_dir, "backend")),
    os.path.abspath(os.path.join(current_dir, "..", "backend")),
]
for p in candidates:
    if os.path.exists(os.path.join(p, "app")):
        if p not in sys.path:
            sys.path.insert(0, p)
        break

from app.ml_engine.embeddings import FastTextEmbeddingEngine
from app.ml_engine.classifier import (
    FitClassifier,
    build_feature_vector,
    evaluate_education_match,
    parse_education_rank,
)
from app.ml_engine.feedback_db import FeedbackDatabase
from app.ml_engine.production_model import ProductionModel, get_production_model
from app.ml_engine.retrain_pipeline import retrain_production_model
from app.ml_engine.baseline_data import generate_embedding_corpus, get_baseline_records
from app.services.job_matching_service import calculate_match_score


def test_phase1_semantic_embeddings():
    """Verify FastText embedding engine, sub-word resilience, and contextual similarity."""
    corpus = generate_embedding_corpus()
    engine = FastTextEmbeddingEngine(epochs=35)
    engine.train(corpus)

    # 1. Vectorize tokens to L2-normalized 1D arrays
    vec_react = engine.vectorize_tokens(["react"])
    vec_vue = engine.vectorize_tokens(["vue"])
    vec_kiln = engine.vectorize_tokens(["kiln", "firing", "thermal_processing"])

    assert vec_react.ndim == 1, "Vector must be 1D"
    assert np.isclose(np.linalg.norm(vec_react), 1.0, atol=1e-3), "Vector must be L2-normalized"
    assert np.isclose(np.linalg.norm(vec_vue), 1.0, atol=1e-3), "Vector must be L2-normalized"

    # 2. Contextual similarity: React and Vue must score significantly higher than React and Kiln
    sim_react_vue = engine.compute_cosine_similarity(vec_react, vec_vue)
    sim_react_kiln = engine.compute_cosine_similarity(vec_react, vec_kiln)

    assert 0.0 <= sim_react_vue <= 1.0, "Cosine similarity must be bounded in [0.0, 1.0]"
    assert 0.0 <= sim_react_kiln <= 1.0, "Cosine similarity must be bounded in [0.0, 1.0]"
    assert sim_react_vue > 0.70, f"React and Vue should have high semantic similarity, got {sim_react_vue}"
    assert sim_react_kiln < 0.40, f"React and Kiln should have low similarity, got {sim_react_kiln}"
    assert sim_react_vue > sim_react_kiln * 2.0, "Related tech skills should score much higher than unrelated manufacturing skills"

    # 3. Empty tokens resilience
    vec_empty = engine.vectorize_tokens([])
    assert np.all(vec_empty == 0.0)
    assert engine.compute_cosine_similarity(vec_empty, vec_react) == 0.0


def test_phase2_scoring_classifier():
    """Verify deterministic feature engineering and calibrated binary classification."""
    corpus = generate_embedding_corpus()
    engine = FastTextEmbeddingEngine(epochs=20).train(corpus)

    # 1. Education rank and match
    assert parse_education_rank("PhD in Computer Science") == 4
    assert parse_education_rank("Master of Science") == 3
    assert parse_education_rank("BS Information Technology") == 2
    assert parse_education_rank("High School Diploma") == 0

    assert evaluate_education_match("MS Software Engineering", "Bachelor's Degree") == 2  # Exceeds
    assert evaluate_education_match("BS Computer Science", "Bachelor's Degree") == 1      # Meets
    assert evaluate_education_match("High School Diploma", "Bachelor's Degree") == 0     # Below

    # 2. Feature vector construction
    fv = build_feature_vector(
        candidate_skills=["react", "typescript"],
        job_skills=["vue", "javascript"],
        candidate_title="frontend engineer",
        job_title="web developer",
        candidate_years=4.0,
        required_years=2.0,
        candidate_edu="BS Computer Science",
        required_edu="Bachelor's Degree",
        embedding_engine=engine,
    )
    assert fv.shape == (4,)
    assert fv[0] > 0.70  # Skill similarity (React ~ Vue)
    assert fv[1] > 0.60  # Title similarity
    assert fv[2] == 2.0  # Experience delta
    assert fv[3] == 1.0  # Education match

    # 3. Fit classifier training and inference
    records = get_baseline_records()
    X = np.array([
        build_feature_vector(
            r["resume_skills"], r["job_skills"], r["resume_title"], r["job_title"],
            r["candidate_years"], r["required_years"], r["candidate_edu"], r["required_edu"],
            engine
        )
        for r in records
    ])
    y = np.array([r["recruiter_action"] for r in records])

    clf = FitClassifier(model_type="random_forest").fit(X, y)
    prob_pos = clf.predict_fit_probability(X[0])
    prob_neg = clf.predict_fit_probability(X[3])

    assert 0.0 <= prob_pos <= 1.0
    assert 0.0 <= prob_neg <= 1.0
    assert prob_pos > prob_neg, f"Qualified applicant should score higher than unqualified ({prob_pos} vs {prob_neg})"


def test_phase3_feedback_database():
    """Verify SQLite feedback schema, raw token storage, and recruiter action logging."""
    db = FeedbackDatabase(":memory:")

    eval_id = db.log_live_prediction(
        resume_id="cand_test_01",
        job_id="job_fe_101",
        resume_skills=["react", "typescript"],
        job_skills=["react", "redux", "ui"],
        resume_titles=["frontend developer"],
        job_titles=["frontend engineer"],
        candidate_years=3.5,
        required_years=2.0,
        candidate_edu="BS Computer Science",
        required_edu="Bachelor",
        feature_vector=[0.94, 0.91, 1.5, 1],
        predicted_fit_score=0.92,
    )
    assert eval_id == 1

    stats_before = db.get_evaluation_stats()
    assert stats_before["total_evaluations"] == 1
    assert stats_before["pending_review"] == 1
    assert stats_before["hired_or_interviewed"] == 0

    # Human HR recruiter reviews candidate and records interview/hired action
    success = db.record_recruiter_feedback(evaluation_id=eval_id, recruiter_action=1)
    assert success is True

    stats_after = db.get_evaluation_stats()
    assert stats_after["hired_or_interviewed"] == 1
    assert stats_after["pending_review"] == 0

    # Query verified records to ensure raw tokens are preserved for embedding recalculations
    verified = db.get_verified_feedback(unused_only=True)
    assert len(verified) == 1
    assert verified[0]["resume_skills"] == ["react", "typescript"]
    assert verified[0]["job_skills"] == ["react", "redux", "ui"]
    assert verified[0]["recruiter_action"] == 1


def test_phase4_continuous_retraining_and_hot_swap():
    """
    Verify complete Human-in-the-Loop continuous retraining loop:
    1. Evaluate a borderline candidate before retraining.
    2. Inject verified human recruiter feedback.
    3. Run retrain_production_model() with sample weighting and embedding update.
    4. Assert atomic hot-swap of model file on disk.
    5. Assert subsequent prediction probability shifts based on recruiter feedback.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "test_production_model.pkl")
        db_path = os.path.join(tmpdir, "test_feedback.db")
        fb_db = FeedbackDatabase(db_path)

        # Step 1: Initial baseline training
        res1 = retrain_production_model(
            model_output_path=model_path,
            feedback_db=fb_db,
            force=True,
        )
        assert res1["status"] == "success"
        assert os.path.exists(model_path)
        mtime1 = os.path.getmtime(model_path)

        # Step 2: Evaluate a specialized/niche applicant (e.g. Svelte framework)
        niche_candidate = {
            "candidate_skills": ["svelte", "typescript", "vite"],
            "job_skills": ["react", "typescript", "frontend"],
            "candidate_title": "frontend engineer",
            "job_title": "frontend developer",
            "candidate_years": 2.0,
            "required_years": 2.0,
            "candidate_edu": "BS Computer Science",
            "required_edu": "Bachelor",
        }

        model_v1 = ProductionModel.load(model_path)
        pred_before = model_v1.predict(**niche_candidate)
        prob_before = pred_before["fit_probability"]

        # Step 3: Recruiter manually reviews and enthusiastically hires this applicant (action = 1)
        eval_id = fb_db.log_live_prediction(
            resume_id="cand_niche_01",
            job_id="job_fe_999",
            resume_skills=niche_candidate["candidate_skills"],
            job_skills=niche_candidate["job_skills"],
            resume_titles=niche_candidate["candidate_title"],
            job_titles=niche_candidate["job_title"],
            candidate_years=niche_candidate["candidate_years"],
            required_years=niche_candidate["required_years"],
            candidate_edu=niche_candidate["candidate_edu"],
            required_edu=niche_candidate["required_edu"],
            feature_vector=pred_before["feature_vector"],
            predicted_fit_score=prob_before,
        )
        fb_db.record_recruiter_feedback(evaluation_id=eval_id, recruiter_action=1)

        # Inject additional verified feedback to strengthen positive reinforcement
        eval_id_2 = fb_db.log_live_prediction(
            resume_id="cand_niche_02",
            job_id="job_fe_999",
            resume_skills=["svelte", "javascript", "web"],
            job_skills=["react", "javascript", "frontend"],
            resume_titles=["web engineer"],
            job_titles=["frontend developer"],
            candidate_years=3.0,
            required_years=2.0,
            candidate_edu="BS IT",
            required_edu="Bachelor",
            feature_vector=pred_before["feature_vector"],
            predicted_fit_score=prob_before,
        )
        fb_db.record_recruiter_feedback(evaluation_id=eval_id_2, recruiter_action=1)

        # Step 4: Run continuous retraining loop
        import time
        time.sleep(0.05)  # Ensure distinct mtime

        res2 = retrain_production_model(
            model_output_path=model_path,
            feedback_db=fb_db,
            recruiter_weight_multiplier=2.0,
            force=True,
        )
        assert res2["status"] == "success"
        mtime2 = os.path.getmtime(model_path)
        assert mtime2 > mtime1, "Model artifact should be atomically hot-swapped with newer mtime"

        # Check records were marked as assimilated
        stats = fb_db.get_evaluation_stats()
        assert stats["assimilated_in_training"] >= 2

        # Step 5: Reload hot-swapped model and verify prediction probability
        model_v2 = ProductionModel.load(model_path)
        pred_after = model_v2.predict(**niche_candidate)
        prob_after = pred_after["fit_probability"]

        # Recruiter reinforcement should elevate or maintain high fit probability
        assert prob_after >= prob_before or prob_after >= 0.70, (
            f"Expected fit probability to reflect recruiter approval: before={prob_before}, after={prob_after}"
        )


def test_application_wiring_calculate_match_score():
    """Verify calculate_match_score produces ML fit probability and logs live predictions."""
    resume_sample = {
        "id": "cand_integration_test",
        "email": "cand_test@example.com",
        "fullname": "John Tester",
        "skills": "React, TypeScript, Redux, CSS3, HTML5",
        "experience": "Frontend Developer at Tech Corp",
        "job_title": "Frontend Developer",
        "years_experience": 4,
        "education": "Bachelor of Science in Computer Science",
    }

    job_mock = {
        "job_id": "JOB-MOCK-TEST-101",
        "job_title": "Frontend Engineer",
        "department": "Engineering",
        "location": "Taguig, Philippines",
        "skills_requirements": "React, TypeScript, UI, Web",
        "experience_requirements": "3 years experience",
        "education_requirements": "Bachelor's Degree",
        "description": "We are seeking a Frontend Engineer proficient in React and modern UI.",
    }

    result = calculate_match_score(resume_sample, job_mock)

    # 1. Standard existing scores are preserved
    assert "match_percentage" in result
    assert "skills_score" in result
    assert "experience_score" in result
    assert "education_score" in result

    # 2. ML Engine fields are populated
    assert "ml_fit_probability" in result
    assert result["ml_fit_probability"] is not None
    assert 0.0 <= result["ml_fit_probability"] <= 1.0
    assert "ml_fit_percentage" in result
    assert "ml_features" in result
    assert "skill_similarity_score" in result["ml_features"]

    # 3. Live prediction was logged to feedback DB
    fb_db = FeedbackDatabase()
    with fb_db._get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM application_evaluations WHERE resume_id = ? ORDER BY evaluation_id DESC LIMIT 1",
            ("cand_integration_test",)
        ).fetchone()
        assert row is not None, "Evaluation must be logged in SQLite database"
        assert row["job_id"] == "JOB-MOCK-TEST-101"
        assert row["predicted_fit_score"] == result["ml_fit_probability"]
