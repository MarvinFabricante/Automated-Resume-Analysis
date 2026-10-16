"""
Production Feedback Schema & Database Layer (SQLite Persistence)
---------------------------------------------------------------
Stores raw extracted tokens, engineered features, live model predictions,
and human recruiter decisions for continuous human-in-the-loop retraining.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Sequence

logger = logging.getLogger(__name__)

# Default path for persistent feedback database
DEFAULT_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "feedback.db")


class FeedbackDatabase:
    """
    Transactional SQLite persistence layer for application evaluations and recruiter feedback.
    Stores raw tokens to enable recalculating cosine similarity upon embedding updates.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("FEEDBACK_DB_PATH") or DEFAULT_DB_PATH
        self._memory_conn = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path == ":memory:" and self._memory_conn is not None:
            return self._memory_conn

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def init_db(self):
        """Create the application_evaluations table and required indexes."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS application_evaluations (
                    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id TEXT,
                    job_id TEXT,
                    resume_skills_json TEXT,
                    job_skills_json TEXT,
                    resume_titles_json TEXT,
                    job_titles_json TEXT,
                    candidate_years REAL,
                    required_years REAL,
                    candidate_edu TEXT,
                    required_edu TEXT,
                    skill_similarity_score REAL,
                    title_similarity_score REAL,
                    experience_delta REAL,
                    education_match INTEGER,
                    predicted_fit_score REAL,
                    recruiter_action INTEGER, -- 1 = Interviewed/Hired, 0 = Rejected/Passed over, NULL = Pending review
                    used_in_training INTEGER DEFAULT 0, -- 0 = Unprocessed, 1 = Assimilated
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_resume_job ON application_evaluations(resume_id, job_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_recruiter_action ON application_evaluations(recruiter_action);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_used_training ON application_evaluations(used_in_training);")
            conn.commit()

    def log_live_prediction(
        self,
        resume_id: Union[str, int],
        job_id: Union[str, int],
        resume_skills: Union[Sequence[str], str],
        job_skills: Union[Sequence[str], str],
        resume_titles: Union[Sequence[str], str],
        job_titles: Union[Sequence[str], str],
        candidate_years: Union[float, int],
        required_years: Union[float, int],
        candidate_edu: Optional[str],
        required_edu: Optional[str],
        feature_vector: Union[Sequence[float], Any],
        predicted_fit_score: float,
    ) -> int:
        """
        Log a live candidate evaluation with both raw extracted tokens and generated feature vector.
        Returns the created evaluation_id.
        """
        def to_json(val):
            if isinstance(val, (list, tuple, set)):
                return json.dumps(list(val))
            elif isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return val
                except Exception:
                    pass
                return json.dumps([v.strip() for v in val.split("|") if v.strip()])
            return json.dumps([])

        r_skills_json = to_json(resume_skills)
        j_skills_json = to_json(job_skills)
        r_titles_json = to_json(resume_titles)
        j_titles_json = to_json(job_titles)

        feat = [float(x) for x in feature_vector]
        skill_sim = feat[0] if len(feat) > 0 else 0.0
        title_sim = feat[1] if len(feat) > 1 else 0.0
        exp_delta = feat[2] if len(feat) > 2 else float((candidate_years or 0) - (required_years or 0))
        edu_match = int(feat[3]) if len(feat) > 3 else 0

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO application_evaluations (
                    resume_id, job_id,
                    resume_skills_json, job_skills_json,
                    resume_titles_json, job_titles_json,
                    candidate_years, required_years,
                    candidate_edu, required_edu,
                    skill_similarity_score, title_similarity_score,
                    experience_delta, education_match,
                    predicted_fit_score, recruiter_action,
                    used_in_training, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?)
                """,
                (
                    str(resume_id),
                    str(job_id),
                    r_skills_json,
                    j_skills_json,
                    r_titles_json,
                    j_titles_json,
                    float(candidate_years or 0.0),
                    float(required_years or 0.0),
                    str(candidate_edu or ""),
                    str(required_edu or ""),
                    float(skill_sim),
                    float(title_sim),
                    float(exp_delta),
                    int(edu_match),
                    float(predicted_fit_score),
                    now_str,
                    now_str,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def record_recruiter_feedback(
        self,
        evaluation_id: Optional[int] = None,
        resume_id: Optional[Union[str, int]] = None,
        job_id: Optional[Union[str, int]] = None,
        recruiter_action: Optional[int] = None,
    ) -> bool:
        """
        Record or update human HR recruiter action:
        1 = Interviewed / Hired
        0 = Rejected / Passed over
        """
        if recruiter_action not in (0, 1):
            raise ValueError("recruiter_action must be 0 (rejected) or 1 (interviewed/hired)")

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if evaluation_id is not None:
                cursor.execute(
                    """
                    UPDATE application_evaluations
                    SET recruiter_action = ?, used_in_training = 0, updated_at = ?
                    WHERE evaluation_id = ?
                    """,
                    (recruiter_action, now_str, evaluation_id),
                )
            elif resume_id is not None and job_id is not None:
                cursor.execute(
                    """
                    UPDATE application_evaluations
                    SET recruiter_action = ?, used_in_training = 0, updated_at = ?
                    WHERE resume_id = ? AND job_id = ?
                    """,
                    (recruiter_action, now_str, str(resume_id), str(job_id)),
                )
            elif resume_id is not None:
                cursor.execute(
                    """
                    UPDATE application_evaluations
                    SET recruiter_action = ?, used_in_training = 0, updated_at = ?
                    WHERE resume_id = ?
                    """,
                    (recruiter_action, now_str, str(resume_id)),
                )
            else:
                return False

            conn.commit()
            return cursor.rowcount > 0

    def get_verified_feedback(self, unused_only: bool = False) -> List[Dict[str, Any]]:
        """
        Query verified records where recruiter_action IS NOT NULL.
        Returns parsed dictionaries with JSON token fields unpacked.
        """
        query = """
            SELECT * FROM application_evaluations
            WHERE recruiter_action IS NOT NULL
        """
        if unused_only:
            query += " AND used_in_training = 0"
        query += " ORDER BY evaluation_id ASC"

        records = []
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            for row in rows:
                r_dict = dict(row)
                # Unpack JSON tokens
                r_dict["resume_skills"] = json.loads(r_dict.get("resume_skills_json") or "[]")
                r_dict["job_skills"] = json.loads(r_dict.get("job_skills_json") or "[]")
                r_dict["resume_titles"] = json.loads(r_dict.get("resume_titles_json") or "[]")
                r_dict["job_titles"] = json.loads(r_dict.get("job_titles_json") or "[]")
                records.append(r_dict)

        return records

    def mark_records_as_used(self, evaluation_ids: Sequence[int]) -> int:
        """Mark assimilated records with used_in_training = 1."""
        if not evaluation_ids:
            return 0

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            placeholders = ",".join("?" for _ in evaluation_ids)
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE application_evaluations
                SET used_in_training = 1, updated_at = ?
                WHERE evaluation_id IN ({placeholders})
                """,
                [now_str] + list(evaluation_ids),
            )
            conn.commit()
            return cursor.rowcount

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Return aggregate counts of total predictions, verified actions, and training usage."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM application_evaluations").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM application_evaluations WHERE recruiter_action IS NULL").fetchone()[0]
            hired = conn.execute("SELECT COUNT(*) FROM application_evaluations WHERE recruiter_action = 1").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM application_evaluations WHERE recruiter_action = 0").fetchone()[0]
            assimilated = conn.execute("SELECT COUNT(*) FROM application_evaluations WHERE used_in_training = 1").fetchone()[0]
            unassimilated_verified = conn.execute("SELECT COUNT(*) FROM application_evaluations WHERE recruiter_action IS NOT NULL AND used_in_training = 0").fetchone()[0]

            return {
                "total_evaluations": total,
                "pending_review": pending,
                "hired_or_interviewed": hired,
                "rejected": rejected,
                "assimilated_in_training": assimilated,
                "unassimilated_verified": unassimilated_verified,
            }


# Default singleton instance for application use
_default_db = None


def get_feedback_db(db_path: Optional[str] = None) -> FeedbackDatabase:
    """Return shared or customized FeedbackDatabase instance."""
    global _default_db
    if db_path is not None:
        return FeedbackDatabase(db_path)
    if _default_db is None:
        _default_db = FeedbackDatabase()
    return _default_db
