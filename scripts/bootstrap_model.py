#!/usr/bin/env python3
"""
Bootstrap Script for Self-Improving ML Engine
---------------------------------------------
Initializes the recruitment corpus, seeds baseline candidate evaluation records,
creates the initial production_model.pkl, and initializes the feedback database.
"""
import os
import sys
import json
import logging

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml_engine.baseline_data import get_baseline_records
from app.ml_engine.feedback_db import get_feedback_db
from app.ml_engine.retrain_pipeline import retrain_production_model
from app.ml_engine.production_model import get_production_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap_model")


def bootstrap():
    logger.info("Starting ML Engine Bootstrap process...")

    data_dir = os.path.join(backend_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 1. Save baseline dataset to data/baseline_dataset.json
    baseline_records = get_baseline_records()
    baseline_json_path = os.path.join(data_dir, "baseline_dataset.json")
    with open(baseline_json_path, "w", encoding="utf-8") as f:
        json.dump(baseline_records, f, indent=2)
    logger.info(f"Wrote {len(baseline_records)} baseline records to {baseline_json_path}")

    # 2. Initialize and seed SQLite Feedback DB
    db_path = os.path.join(data_dir, "feedback.db")
    fb_db = get_feedback_db(db_path)
    logger.info(f"Initialized Feedback Database at {db_path}")

    # Seed sample historical live evaluations into feedback DB
    sample_candidates = [
        {
            "resume_id": "seed_cand_01",
            "job_id": "JOB-FE-001",
            "resume_skills": ["react", "typescript", "redux", "html5", "css3"],
            "job_skills": ["react", "typescript", "frontend", "ui"],
            "resume_titles": ["frontend developer"],
            "job_titles": ["frontend engineer"],
            "candidate_years": 4.0,
            "required_years": 3.0,
            "candidate_edu": "BS Computer Science",
            "required_edu": "Bachelor",
            "feature_vector": [0.95, 0.90, 1.0, 1],
            "predicted_fit_score": 0.94,
            "action": 1,
        },
        {
            "resume_id": "seed_cand_02",
            "job_id": "JOB-BE-002",
            "resume_skills": ["python", "fastapi", "postgresql", "docker", "redis"],
            "job_skills": ["python", "django", "postgresql", "api"],
            "resume_titles": ["python backend engineer"],
            "job_titles": ["backend developer"],
            "candidate_years": 5.0,
            "required_years": 3.0,
            "candidate_edu": "MS Software Engineering",
            "required_edu": "Bachelor",
            "feature_vector": [0.92, 0.88, 2.0, 2],
            "predicted_fit_score": 0.96,
            "action": 1,
        },
        {
            "resume_id": "seed_cand_03",
            "job_id": "JOB-FE-001",
            "resume_skills": ["kiln", "firing", "glaze", "ceramics"],
            "job_skills": ["react", "typescript", "frontend"],
            "resume_titles": ["kiln operator"],
            "job_titles": ["frontend engineer"],
            "candidate_years": 5.0,
            "required_years": 3.0,
            "candidate_edu": "High School",
            "required_edu": "Bachelor",
            "feature_vector": [0.20, 0.15, 2.0, 0],
            "predicted_fit_score": 0.05,
            "action": 0,
        },
        {
            "resume_id": "seed_cand_04",
            "job_id": "JOB-CER-003",
            "resume_skills": ["kiln", "firing", "glaze", "slip_casting", "quality_inspection"],
            "job_skills": ["kiln", "firing", "ceramics", "safety"],
            "resume_titles": ["ceramics technician"],
            "job_titles": ["kiln operator"],
            "candidate_years": 4.0,
            "required_years": 2.0,
            "candidate_edu": "Vocational Diploma in Ceramic Technology",
            "required_edu": "Vocational / High School",
            "feature_vector": [0.94, 0.89, 2.0, 1],
            "predicted_fit_score": 0.93,
            "action": 1,
        },
    ]

    for cand in sample_candidates:
        eval_id = fb_db.log_live_prediction(
            resume_id=cand["resume_id"],
            job_id=cand["job_id"],
            resume_skills=cand["resume_skills"],
            job_skills=cand["job_skills"],
            resume_titles=cand["resume_titles"],
            job_titles=cand["job_titles"],
            candidate_years=cand["candidate_years"],
            required_years=cand["required_years"],
            candidate_edu=cand["candidate_edu"],
            required_edu=cand["required_edu"],
            feature_vector=cand["feature_vector"],
            predicted_fit_score=cand["predicted_fit_score"],
        )
        if cand.get("action") is not None:
            fb_db.record_recruiter_feedback(evaluation_id=eval_id, recruiter_action=cand["action"])

    stats = fb_db.get_evaluation_stats()
    logger.info(f"Seeded feedback DB. Current stats: {stats}")

    # 3. Train and bundle initial production_model.pkl
    model_path = os.path.join(data_dir, "production_model.pkl")
    logger.info("Training initial production model bundle...")
    result = retrain_production_model(
        baseline_data_path=baseline_json_path,
        model_output_path=model_path,
        feedback_db=fb_db,
        force=True,
    )
    logger.info(f"Initial model successfully trained and hot-swapped: {result['version']}")
    logger.info(f"Model Metrics: {json.dumps(result['metrics'], indent=2)}")

    # 4. Verification test of inference
    model = get_production_model(model_path)
    test_eval = model.predict(
        candidate_skills=["vue", "javascript", "typescript", "tailwind"],
        job_skills=["react", "typescript", "redux", "ui"],
        candidate_title="web developer",
        job_title="frontend engineer",
        candidate_years=3.5,
        required_years=2.0,
        candidate_edu="BS Information Technology",
        required_edu="Bachelor's Degree",
    )
    logger.info(f"Inference sanity check (Vue candidate for Frontend role):")
    logger.info(f"Fit Probability: {test_eval['fit_probability']:.4f} ({test_eval['fit_percentage']}%)")
    logger.info(f"Skill Similarity: {test_eval['features']['skill_similarity_score']}")
    logger.info(f"Title Similarity: {test_eval['features']['title_similarity_score']}")
    logger.info("Bootstrap complete and verified successfully!")


if __name__ == "__main__":
    bootstrap()
