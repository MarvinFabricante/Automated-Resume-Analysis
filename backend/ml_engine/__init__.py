"""
Root alias for app.ml_engine to support top-level imports:
e.g. from ml_engine.embeddings import ...
"""
import sys
from app.ml_engine import *
from app.ml_engine import embeddings, classifier, feedback_db, production_model, retrain_pipeline, baseline_data

# Register submodule aliases in sys.modules
sys.modules["ml_engine.embeddings"] = embeddings
sys.modules["ml_engine.classifier"] = classifier
sys.modules["ml_engine.feedback_db"] = feedback_db
sys.modules["ml_engine.production_model"] = production_model
sys.modules["ml_engine.retrain_pipeline"] = retrain_pipeline
sys.modules["ml_engine.baseline_data"] = baseline_data
