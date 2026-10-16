"""
Automated Continuous Retraining Pipeline (Human-in-the-Loop)
------------------------------------------------------------
Implements retrain_production_model() with:
1. Data cycling and embedding drift prevention (re-projecting baseline + verified tokens).
2. Human-weighted classifier retraining (1.5x sample weight on recruiter actions).
3. Validation metrics (ROC-AUC, F1).
4. Atomic hot-swapping of production_model.pkl via staging and os.replace().
5. Database synchronization (marking records as assimilated).
"""
import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split

from app.ml_engine.embeddings import FastTextEmbeddingEngine
from app.ml_engine.classifier import FitClassifier, build_feature_vector
from app.ml_engine.feedback_db import FeedbackDatabase, get_feedback_db
from app.ml_engine.production_model import ProductionModel, DEFAULT_MODEL_PATH
from app.ml_engine.baseline_data import generate_embedding_corpus, get_baseline_records

logger = logging.getLogger(__name__)


def retrain_production_model(
    baseline_data_path: Optional[str] = None,
    model_output_path: Optional[str] = None,
    feedback_db: Optional[FeedbackDatabase] = None,
    min_new_samples: int = 1,
    recruiter_weight_multiplier: float = 1.5,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Execute full Human-in-the-Loop continuous retraining loop:
    1. Collect verified recruiter decisions from SQLite feedback database.
    2. Check if retraining threshold is met (unless force=True).
    3. Update FastText semantic embeddings on combined corpus to prevent drift.
    4. Re-calculate feature vectors across baseline and production records in updated embedding space.
    5. Train classifier with higher sample_weight (1.5x) on verified human recruiter decisions.
    6. Evaluate validation metrics (ROC-AUC, F1).
    7. Atomically hot-swap production_model.pkl.
    8. Mark assimilated records in feedback DB (used_in_training = 1).
    """
    start_time = time.time()
    target_model_path = model_output_path or DEFAULT_MODEL_PATH
    db = feedback_db or get_feedback_db()

    # 1. Query verified human feedback
    verified_records = db.get_verified_feedback(unused_only=False)
    unassimilated = [r for r in verified_records if not r.get("used_in_training")]

    if not force and len(unassimilated) < min_new_samples and os.path.exists(target_model_path):
        logger.info(
            f"Retraining skipped: only {len(unassimilated)} unassimilated samples "
            f"(minimum required: {min_new_samples})."
        )
        return {
            "status": "skipped",
            "message": f"Insufficient new verified samples ({len(unassimilated)} < {min_new_samples})",
            "unassimilated_count": len(unassimilated),
            "model_path": target_model_path,
        }

    # 2. Load baseline records
    baseline_records: List[Dict[str, Any]] = []
    if baseline_data_path and os.path.exists(baseline_data_path):
        try:
            with open(baseline_data_path, "r", encoding="utf-8") as f:
                baseline_records = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load baseline dataset from {baseline_data_path}: {e}")

    if not baseline_records:
        baseline_records = get_baseline_records()

    # 3. Build unified token corpus for FastText embedding update
    embedding_corpus = generate_embedding_corpus()

    # Add tokens from baseline records
    for r in baseline_records:
        r_skills = r.get("resume_skills") or []
        j_skills = r.get("job_skills") or []
        r_title = r.get("resume_title") or ""
        j_title = r.get("job_title") or ""
        if r_skills:
            embedding_corpus.append(r_skills)
        if j_skills:
            embedding_corpus.append(j_skills)
        if r_title:
            embedding_corpus.append(r_title.split())
        if j_title:
            embedding_corpus.append(j_title.split())

    # Add newly verified production tokens
    for vr in verified_records:
        r_skills = vr.get("resume_skills") or []
        j_skills = vr.get("job_skills") or []
        r_titles = vr.get("resume_titles") or []
        j_titles = vr.get("job_titles") or []
        if r_skills:
            embedding_corpus.append(r_skills)
        if j_skills:
            embedding_corpus.append(j_skills)
        if r_titles:
            embedding_corpus.append(r_titles)
        if j_titles:
            embedding_corpus.append(j_titles)

    # 4. Retrain / Fine-tune FastText Embeddings
    logger.info("Retraining FastText embeddings on unified corpus...")
    embedding_engine = FastTextEmbeddingEngine(epochs=50)
    embedding_engine.train(embedding_corpus)

    # 5. Re-project ALL records in updated embedding space to prevent drift
    logger.info("Re-calculating feature vectors in updated embedding space...")
    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    weights_list: List[float] = []

    # Process baseline records (weight = 1.0)
    for r in baseline_records:
        fv = build_feature_vector(
            candidate_skills=r.get("resume_skills", []),
            job_skills=r.get("job_skills", []),
            candidate_title=r.get("resume_title", ""),
            job_title=r.get("job_title", ""),
            candidate_years=r.get("candidate_years", 0.0),
            required_years=r.get("required_years", 0.0),
            candidate_edu=r.get("candidate_edu", ""),
            required_edu=r.get("required_edu", ""),
            embedding_engine=embedding_engine,
        )
        X_list.append(fv)
        y_list.append(int(r.get("recruiter_action", 0)))
        weights_list.append(1.0)

    # Process production verified records (weight = 1.5x)
    for vr in verified_records:
        fv = build_feature_vector(
            candidate_skills=vr.get("resume_skills", []),
            job_skills=vr.get("job_skills", []),
            candidate_title=vr.get("resume_titles", []),
            job_title=vr.get("job_titles", []),
            candidate_years=vr.get("candidate_years", 0.0),
            required_years=vr.get("required_years", 0.0),
            candidate_edu=vr.get("candidate_edu", ""),
            required_edu=vr.get("required_edu", ""),
            embedding_engine=embedding_engine,
        )
        X_list.append(fv)
        y_list.append(int(vr["recruiter_action"]))
        weights_list.append(float(recruiter_weight_multiplier))

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    sample_weights = np.array(weights_list, dtype=np.float32)

    # 6. Train-Validation Split and Model Evaluation
    # Stratify if both classes have sufficient samples
    can_stratify = (np.bincount(y) >= 2).all() if len(np.unique(y)) > 1 else False
    if len(X) >= 8 and can_stratify:
        X_train, X_val, y_train, y_val, w_train, _ = train_test_split(
            X, y, sample_weights, test_size=0.25, random_state=42, stratify=y
        )
    else:
        # Evaluate on full dataset when total sample size is small
        X_train, X_val, y_train, y_val, w_train = X, X, y, y, sample_weights

    classifier = FitClassifier(model_type="random_forest", random_state=42)
    classifier.fit(X_train, y_train, sample_weight=w_train)

    # Validation metrics
    y_pred = (classifier.predict_batch(X_val) >= 0.5).astype(int)
    y_proba = classifier.predict_batch(X_val)

    acc = float(accuracy_score(y_val, y_pred))
    f1 = float(f1_score(y_val, y_pred, zero_division=1.0))
    if len(np.unique(y_val)) > 1:
        roc_auc = float(roc_auc_score(y_val, y_proba))
    else:
        roc_auc = 1.0

    metrics = {
        "accuracy": round(acc, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "num_baseline_samples": len(baseline_records),
        "num_feedback_samples": len(verified_records),
        "num_total_samples": len(X),
        "feature_importances": classifier.get_feature_importances(),
    }

    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    version_id = f"prod-{now_utc.strftime('%Y%m%d-%H%M%S')}"
    metadata = {
        "version": version_id,
        "trained_at": now_utc.isoformat(),
        "metrics": metrics,
        "recruiter_weight_multiplier": recruiter_weight_multiplier,
    }

    production_bundle = ProductionModel(
        embedding_engine=embedding_engine,
        classifier=classifier,
        metadata=metadata,
    )
    saved_path = production_bundle.save(target_model_path)

    # 8. Mark assimilated records in database
    assimilated_ids = [vr["evaluation_id"] for vr in verified_records if "evaluation_id" in vr]
    assimilated_count = db.mark_records_as_used(assimilated_ids)

    elapsed = round(time.time() - start_time, 2)
    logger.info(
        f"Continuous retraining complete in {elapsed}s. "
        f"Version: {version_id}, ROC-AUC: {roc_auc:.4f}, F1: {f1:.4f}, "
        f"Assimilated: {assimilated_count} records."
    )

    return {
        "status": "success",
        "version": version_id,
        "metrics": metrics,
        "model_path": saved_path,
        "assimilated_records": assimilated_count,
        "duration_seconds": elapsed,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Executing standalone continuous retraining pipeline...")
    res = retrain_production_model(force=True)
    print("Retraining Result:")
    print(json.dumps(res, indent=2))
