"""
Self-Improving ML Engine Package
--------------------------------
Provides FastText embeddings, calibrated scoring classification,
feedback persistence, and continuous retraining for Automated Resume Analysis.
"""
from app.ml_engine.embeddings import (
    FastTextEmbeddingEngine,
    normalize_token,
    normalize_token_list,
)
from app.ml_engine.classifier import (
    FitClassifier,
    build_feature_vector,
    evaluate_education_match,
    FEATURE_NAMES,
)
from app.ml_engine.feedback_db import (
    FeedbackDatabase,
    get_feedback_db,
)
from app.ml_engine.production_model import (
    ProductionModel,
    get_production_model,
    DEFAULT_MODEL_PATH,
)
from app.ml_engine.retrain_pipeline import (
    retrain_production_model,
)

__all__ = [
    "FastTextEmbeddingEngine",
    "normalize_token",
    "normalize_token_list",
    "FitClassifier",
    "build_feature_vector",
    "evaluate_education_match",
    "FEATURE_NAMES",
    "FeedbackDatabase",
    "get_feedback_db",
    "ProductionModel",
    "get_production_model",
    "DEFAULT_MODEL_PATH",
    "retrain_production_model",
]
