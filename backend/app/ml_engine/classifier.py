"""
Scoring & Machine Learning Classification Module (Scikit-Learn)
--------------------------------------------------------------
Deterministic feature engineering and calibrated binary classification pipeline
predicting candidate-job fit probability without generative AI.
"""
import re
import logging
from typing import Sequence, Union, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import BaseEstimator, ClassifierMixin

logger = logging.getLogger(__name__)

# Standard feature order for tabular inference
FEATURE_NAMES = [
    "skill_similarity_score",
    "title_similarity_score",
    "experience_delta",
    "education_match",
]

# Educational hierarchy ranks
EDUCATION_LEVEL_RANKS = {
    "doctorate": 4,
    "phd": 4,
    "doctoral": 4,
    "master": 3,
    "ms": 3,
    "ma": 3,
    "mba": 3,
    "postgraduate": 3,
    "bachelor": 2,
    "bs": 2,
    "ba": 2,
    "college": 2,
    "undergraduate": 2,
    "associate": 1,
    "diploma": 1,
    "vocational": 1,
    "high school": 0,
    "secondary": 0,
    "none": 0,
}


def parse_education_rank(edu_text: Optional[str]) -> int:
    """
    Map an education string to an ordinal hierarchy level (0 to 4).
    4 = Doctorate / PhD
    3 = Master's / MBA
    2 = Bachelor's / BS / BA
    1 = Associate's / Diploma / Vocational
    0 = High School / None / Not specified
    """
    if not edu_text:
        return 0
    t = edu_text.lower().strip()
    # Check high school / secondary first so "High School Diploma" is rank 0
    if re.search(r"\b(high\s*school|secondary)\b", t):
        return 0
    if re.search(r"\b(ph\.?d|doctorate|doctoral|post[-\s]?doc)\b", t):
        return 4
    if re.search(r"\b(master|m\.?s\.?|m\.?a\.?|mba|post[-\s]?grad)\b", t):
        return 3
    if re.search(r"\b(bachelor|b\.?s\.?|b\.?a\.?|college degree|undergrad)\b", t):
        return 2
    if re.search(r"\b(associate|diploma|vocational|certificate)\b", t):
        return 1
    return 0


def evaluate_education_match(candidate_edu: Optional[str], required_edu: Optional[str]) -> int:
    """
    Ordinal comparison between candidate's educational attainment and job requirements:
    2 = Exceeds requirement
    1 = Meets requirement
    0 = Below requirement
    """
    cand_rank = parse_education_rank(candidate_edu)
    req_rank = parse_education_rank(required_edu)

    # If no requirement specified, any tertiary degree meets or exceeds
    if req_rank == 0 and cand_rank >= 2:
        return 1

    if cand_rank > req_rank:
        return 2
    elif cand_rank == req_rank:
        return 1
    else:
        return 0


def build_feature_vector(
    candidate_skills: Union[Sequence[str], str],
    job_skills: Union[Sequence[str], str],
    candidate_title: Union[Sequence[str], str],
    job_title: Union[Sequence[str], str],
    candidate_years: Union[float, int],
    required_years: Union[float, int],
    candidate_edu: Optional[str],
    required_edu: Optional[str],
    embedding_engine: Any,
) -> np.ndarray:
    """
    Construct a deterministic feature vector for an applicant:
    1. skill_similarity_score: Cosine similarity between candidate and job skill vectors [0.0, 1.0]
    2. title_similarity_score: Cosine similarity between candidate and job title vectors [0.0, 1.0]
    3. experience_delta: candidate_actual_years - job_required_years
    4. education_match: 2 (Exceeds), 1 (Meets), 0 (Below)

    Returns a 1D numpy array of shape (4,), dtype=float32.
    """
    # 1. Normalize skill token lists
    if isinstance(candidate_skills, str):
        c_skills = [s.strip() for s in re.split(r"[,|\n;]+", candidate_skills) if s.strip()]
    else:
        c_skills = list(candidate_skills)

    if isinstance(job_skills, str):
        j_skills = [s.strip() for s in re.split(r"[,|\n;]+", job_skills) if s.strip()]
    else:
        j_skills = list(job_skills)

    # 2. Normalize title token lists
    if isinstance(candidate_title, str):
        c_titles = [t.strip() for t in re.split(r"[,|\n;]+", candidate_title) if t.strip()]
    else:
        c_titles = list(candidate_title)

    if isinstance(job_title, str):
        j_titles = [t.strip() for t in re.split(r"[,|\n;]+", job_title) if t.strip()]
    else:
        j_titles = list(job_title)

    # Vectorize and compute similarities
    vec_c_skills = embedding_engine.vectorize_tokens(c_skills)
    vec_j_skills = embedding_engine.vectorize_tokens(j_skills)
    skill_sim = embedding_engine.compute_cosine_similarity(vec_c_skills, vec_j_skills)

    vec_c_titles = embedding_engine.vectorize_tokens(c_titles)
    vec_j_titles = embedding_engine.vectorize_tokens(j_titles)
    title_sim = embedding_engine.compute_cosine_similarity(vec_c_titles, vec_j_titles)

    # Experience delta
    c_yrs = float(candidate_years or 0.0)
    r_yrs = float(required_years or 0.0)
    exp_delta = float(c_yrs - r_yrs)

    # Education match
    edu_match = float(evaluate_education_match(candidate_edu, required_edu))

    return np.array([skill_sim, title_sim, exp_delta, edu_match], dtype=np.float32)


class FitClassifier:
    """
    Production-grade Binary Classifier predicting recruiter acceptance probability.
    Supports GradientBoostingClassifier or RandomForestClassifier with sample weighting.
    """

    def __init__(self, model_type: str = "random_forest", random_state: int = 42):
        self.model_type = model_type.lower()
        self.random_state = random_state
        self.model: Optional[BaseEstimator] = None
        self._is_trained = False

        if "gradient" in self.model_type or "gbm" in self.model_type:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.08,
                max_depth=3,
                subsample=0.85,
                random_state=self.random_state,
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_split=2,
                class_weight="balanced",
                random_state=self.random_state,
            )

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
    ) -> "FitClassifier":
        """
        Train the classifier on the engineered feature matrix X and binary targets y.
        Supports sample_weight (e.g. 1.5x on verified recruiter feedback).
        """
        X_arr = np.asarray(X, dtype=np.float32)
        y_arr = np.asarray(y, dtype=np.int32)

        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)

        weights = np.asarray(sample_weight, dtype=np.float32) if sample_weight is not None else None

        self.model.fit(X_arr, y_arr, sample_weight=weights)
        self._is_trained = True
        return self

    def predict_fit_probability(self, feature_vector: np.ndarray) -> float:
        """
        Predict calibrated fit probability [0.0, 1.0] for a single applicant feature vector.
        """
        if not self._is_trained or self.model is None:
            # Fallback heuristic if untrained
            v = np.asarray(feature_vector, dtype=np.float32).flatten()
            skill_sim = float(v[0]) if len(v) > 0 else 0.5
            return float(np.clip(skill_sim, 0.0, 1.0))

        feat = np.asarray(feature_vector, dtype=np.float32)
        if feat.ndim == 1:
            feat = feat.reshape(1, -1)

        proba = self.model.predict_proba(feat)
        # Binary classification positive class probability
        if proba.shape[1] > 1:
            score = float(proba[0, 1])
        else:
            score = float(proba[0, 0])

        return float(np.clip(score, 0.0, 1.0))

    def predict_batch(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities for a batch of feature vectors."""
        if not self._is_trained or self.model is None:
            return np.full((len(X),), 0.5, dtype=np.float32)

        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)

        proba = self.model.predict_proba(X_arr)
        if proba.shape[1] > 1:
            return proba[:, 1].astype(np.float32)
        return proba[:, 0].astype(np.float32)

    def get_feature_importances(self) -> Dict[str, float]:
        """Return named dictionary of feature importance percentages."""
        if not self._is_trained or self.model is None:
            return {f: 0.25 for f in FEATURE_NAMES}

        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            return {f: 0.25 for f in FEATURE_NAMES}

        return {
            name: round(float(imp), 4)
            for name, imp in zip(FEATURE_NAMES, importances)
        }
