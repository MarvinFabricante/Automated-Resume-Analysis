"""
Production Model Bundle & Inference Interface
----------------------------------------------
Encapsulates FastText Embedding Engine, Scikit-Learn Classifier,
and metadata into a single atomic artifact with hot-swap support.
"""
import os
import time
import logging
from typing import Dict, Any, Optional, Union, Sequence
import numpy as np
import joblib

from app.ml_engine.embeddings import FastTextEmbeddingEngine
from app.ml_engine.classifier import FitClassifier, build_feature_vector, FEATURE_NAMES

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "production_model.pkl")


class ProductionModel:
    """
    Bundled production artifact containing:
    1. FastTextEmbeddingEngine (sub-word embeddings + TF-IDF weighting)
    2. FitClassifier (calibrated scikit-learn binary classifier)
    3. Metadata (version, timestamp, training counts, validation metrics)
    """

    def __init__(
        self,
        embedding_engine: FastTextEmbeddingEngine,
        classifier: FitClassifier,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.embedding_engine = embedding_engine
        self.classifier = classifier
        self.metadata = metadata or {
            "version": "1.0.0",
            "created_at": time.time(),
            "metrics": {},
        }

    def predict(
        self,
        candidate_skills: Union[Sequence[str], str],
        job_skills: Union[Sequence[str], str],
        candidate_title: Union[Sequence[str], str],
        job_title: Union[Sequence[str], str],
        candidate_years: Union[float, int],
        required_years: Union[float, int],
        candidate_edu: Optional[str] = None,
        required_edu: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute end-to-end deterministic featurization and ML fit probability prediction.
        Returns detailed scores and feature components.
        """
        fv = build_feature_vector(
            candidate_skills=candidate_skills,
            job_skills=job_skills,
            candidate_title=candidate_title,
            job_title=job_title,
            candidate_years=candidate_years,
            required_years=required_years,
            candidate_edu=candidate_edu,
            required_edu=required_edu,
            embedding_engine=self.embedding_engine,
        )

        fit_prob = self.classifier.predict_fit_probability(fv)
        fit_pct = round(fit_prob * 100.0, 1)

        return {
            "fit_probability": float(fit_prob),
            "fit_percentage": fit_pct,
            "feature_vector": fv,
            "features": {
                "skill_similarity_score": round(float(fv[0]), 4),
                "title_similarity_score": round(float(fv[1]), 4),
                "experience_delta": round(float(fv[2]), 2),
                "education_match": int(fv[3]),
            },
            "feature_importances": self.classifier.get_feature_importances(),
            "model_version": self.metadata.get("version", "1.0.0"),
            "trained_at": self.metadata.get("trained_at", None),
        }

    def save(self, model_path: Optional[str] = None) -> str:
        """
        Atomically save the model bundle to disk using staging file and os.replace().
        Prevents file corruption or race conditions with live inference processes.
        """
        target_path = os.path.abspath(model_path or DEFAULT_MODEL_PATH)
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        staging_path = f"{target_path}.tmp.{os.getpid()}.{int(time.time()*1000)}"

        try:
            # Bundle state into dictionary
            state = {
                "embedding_engine": self.embedding_engine,
                "classifier": self.classifier,
                "metadata": self.metadata,
            }
            joblib.dump(state, staging_path, compress=0)
            # Atomic swap on POSIX filesystems
            os.replace(staging_path, target_path)
            logger.info(f"Atomically saved production model to {target_path}")
            return target_path
        finally:
            if os.path.exists(staging_path):
                try:
                    os.remove(staging_path)
                except OSError:
                    pass

    @classmethod
    def load(cls, model_path: Optional[str] = None) -> "ProductionModel":
        """Load bundled production model artifact from disk."""
        target_path = os.path.abspath(model_path or DEFAULT_MODEL_PATH)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Model file not found at: {target_path}")

        state = joblib.load(target_path)
        return cls(
            embedding_engine=state["embedding_engine"],
            classifier=state["classifier"],
            metadata=state.get("metadata", {}),
        )


# Global cached singleton instance
_cached_production_model: Optional[ProductionModel] = None
_cached_model_mtime: float = 0.0


def get_production_model(model_path: Optional[str] = None) -> ProductionModel:
    """
    Get or reload the active production model.
    Checks file modification time to hot-reload automatically if model was retrained on disk.
    If no model exists on disk, bootstraps a baseline model on the fly.
    """
    global _cached_production_model, _cached_model_mtime
    target_path = os.path.abspath(model_path or DEFAULT_MODEL_PATH)

    if not os.path.exists(target_path):
        from app.ml_engine.retrain_pipeline import retrain_production_model
        logger.info(f"Production model not found at {target_path}. Bootstrapping initial model...")
        retrain_production_model(model_output_path=target_path, force=True)

    current_mtime = os.path.getmtime(target_path)
    if _cached_production_model is None or current_mtime > _cached_model_mtime:
        logger.info(f"Loading/Reloading production model from {target_path} (mtime={current_mtime})...")
        _cached_production_model = ProductionModel.load(target_path)
        _cached_model_mtime = current_mtime

    return _cached_production_model
