"""
Semantic Embedding & Featurization Module (Gensim FastText + spaCy + TF-IDF)
-----------------------------------------------------------------------------
Zero LLM / Zero Transformer implementation.
Provides sub-word resilient FastText embeddings with TF-IDF IDF weighting,
token normalization, spaCy extraction, and bounded [0.0, 1.0] cosine similarity.
"""
import os
import re
import logging
from typing import List, Sequence, Optional, Tuple, Set
import numpy as np
from gensim.models import FastText
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# Canonical token replacements for common technical synonyms & notations
CANONICAL_REPLACEMENTS = {
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "node.js": "nodejs",
    "next.js": "nextjs",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "c++": "cpp",
    "c#": "csharp",
    ".net": "dotnet",
    "golang": "go",
    "fast-api": "fastapi",
    "rest-api": "api",
    "restful": "api",
}


def normalize_token(token: str) -> str:
    """
    Normalize individual skill or job title token.
    Preserves specialized programming characters (e.g. c++, c#, .net)
    and maps common framework aliases to standard canonical forms.
    """
    if not token:
        return ""
    t = token.strip().lower()
    t = CANONICAL_REPLACEMENTS.get(t, t)
    # Replace separators with underscore if multi-word
    t = re.sub(r"[\s\-\/\.]+", "_", t)
    t = t.strip("_")
    return t


def normalize_token_list(tokens: Sequence[str]) -> List[str]:
    """Normalize a list of token strings, removing blanks and duplicates while preserving order."""
    res = []
    seen = set()
    for tok in tokens:
        if not tok:
            continue
        cleaned = normalize_token(str(tok))
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            res.append(cleaned)
    return res


class FastTextEmbeddingEngine:
    """
    Sub-word aware FastText Embedding Engine weighted by TF-IDF IDF scores.
    Handles out-of-vocabulary variations, typos, and captures semantic closeness
    between complementary technologies (e.g. React ~ Vue, FastAPI ~ Flask).
    """

    def __init__(
        self,
        vector_size: int = 64,
        window: int = 5,
        min_count: int = 1,
        min_n: int = 2,
        max_n: int = 6,
        bucket: int = 50000,
        epochs: int = 40,
        seed: int = 42,
    ):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.min_n = min_n
        self.max_n = max_n
        self.bucket = bucket
        self.epochs = epochs
        self.seed = seed

        self.model: Optional[FastText] = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.idf_dict_: dict[str, float] = {}
        self.default_idf_: float = 1.0

        # Lazy spaCy pipeline holder
        self._nlp = None
        self._skills_matcher = None
        self._job_title_matcher = None

    def _get_spacy(self):
        """Lazy loader for spaCy pipeline and matchers."""
        if self._nlp is None:
            try:
                from app.extractors.nlp.nlp_engine import (
                    get_nlp,
                    get_skills_matcher,
                    get_job_title_matcher,
                )
                self._nlp = get_nlp()
                self._skills_matcher = get_skills_matcher()
                self._job_title_matcher = get_job_title_matcher()
            except Exception as e:
                logger.warning(f"Could not load shared spaCy engine: {e}. Falling back to basic spaCy.")
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def extract_clean_skills(self, text: str) -> List[str]:
        """
        Extract clean skills from text using spaCy and existing extractors.
        Falls back to rule-based token splitting when NLP is unavailable.
        """
        if not text:
            return []
        try:
            self._get_spacy()
            if self._skills_matcher and self._nlp:
                doc = self._nlp(text)
                matches = self._skills_matcher(doc)
                raw_skills = [doc[start:end].text for _, start, end in matches]
                if raw_skills:
                    return normalize_token_list(raw_skills)
        except Exception as e:
            logger.debug(f"spaCy skill extraction fallback triggered: {e}")

        # Fallback heuristic: split on commas, pipes, newlines, semicolons
        parts = re.split(r"[,|\n;]+", text)
        return normalize_token_list(parts)

    def extract_clean_job_titles(self, text: str) -> List[str]:
        """
        Extract clean job titles from text using spaCy or pattern heuristics.
        """
        if not text:
            return []
        try:
            self._get_spacy()
            if self._job_title_matcher and self._nlp:
                doc = self._nlp(text)
                matches = self._job_title_matcher(doc)
                raw_titles = [doc[start:end].text for _, start, end in matches]
                if raw_titles:
                    return normalize_token_list(raw_titles)
        except Exception as e:
            logger.debug(f"spaCy job title extraction fallback triggered: {e}")

        # Fallback: clean and extract line or snippet
        parts = re.split(r"[,|\n;]+", text)
        cleaned = [re.sub(r"^(job title|title|role)[:\s]+", "", p, flags=re.IGNORECASE).strip() for p in parts]
        return normalize_token_list(cleaned)

    def train(self, corpus: List[List[str]]) -> "FastTextEmbeddingEngine":
        """
        Train FastText model and fit TF-IDF vectorizer over the domain corpus.
        Corpus is a list of token lists (sentences).
        """
        clean_corpus = []
        doc_strings = []
        for sent in corpus:
            norm_sent = [normalize_token(t) for t in sent if normalize_token(t)]
            if norm_sent:
                clean_corpus.append(norm_sent)
                doc_strings.append(" ".join(norm_sent))

        if not clean_corpus:
            raise ValueError("Corpus cannot be empty for FastText training.")

        logger.info(f"Training FastText with {len(clean_corpus)} sentences...")
        self.model = FastText(
            sentences=clean_corpus,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            min_n=self.min_n,
            max_n=self.max_n,
            bucket=self.bucket,
            epochs=self.epochs,
            seed=self.seed,
        )

        # Fit TF-IDF on token document strings to compute inverse document frequencies
        self.tfidf_vectorizer = TfidfVectorizer(
            lowercase=False,
            token_pattern=r"(?u)\b\w+\b",
            norm="l2",
            min_df=1,
        )
        self.tfidf_vectorizer.fit(doc_strings)
        vocab = self.tfidf_vectorizer.vocabulary_
        idf = self.tfidf_vectorizer.idf_
        self.idf_dict_ = {term: float(idf[idx]) for term, idx in vocab.items()}
        self.default_idf_ = float(np.median(idf)) if len(idf) > 0 else 1.0

        return self

    def update(self, new_corpus: List[List[str]]) -> "FastTextEmbeddingEngine":
        """
        Incrementally update FastText vocabulary and fine-tune on newly observed tokens.
        """
        if self.model is None:
            return self.train(new_corpus)

        clean_new = []
        new_doc_strings = []
        for sent in new_corpus:
            norm_sent = [normalize_token(t) for t in sent if normalize_token(t)]
            if norm_sent:
                clean_new.append(norm_sent)
                new_doc_strings.append(" ".join(norm_sent))

        if not clean_new:
            return self

        # Build vocabulary for new tokens and fine-tune
        self.model.build_vocab(clean_new, update=True)
        self.model.train(
            clean_new,
            total_examples=len(clean_new),
            epochs=max(15, self.epochs // 2),
        )

        # Update IDF dictionary
        for sent in clean_new:
            for tok in sent:
                if tok not in self.idf_dict_:
                    self.idf_dict_[tok] = self.default_idf_

        return self

    def get_token_vector(self, token: str) -> np.ndarray:
        """
        Get vector for single token. Returns L2-normalized 1D vector.
        FastText generates representations even for subwords/OOV.
        """
        norm_t = normalize_token(token)
        if not norm_t or self.model is None:
            return np.zeros(self.vector_size, dtype=np.float32)

        raw_vec = self.model.wv[norm_t]
        norm = np.linalg.norm(raw_vec)
        if norm > 1e-9:
            return (raw_vec / norm).astype(np.float32)
        return np.zeros(self.vector_size, dtype=np.float32)

    def vectorize_tokens(self, tokens: Sequence[str]) -> np.ndarray:
        """
        Convert extracted skills or job titles into an L2-normalized 1D numpy vector array.
        Weights each token by its TF-IDF IDF score.
        If tokens is empty or all vectors are zero, returns zero vector array of shape (vector_size,).
        """
        if not tokens or self.model is None:
            return np.zeros(self.vector_size, dtype=np.float32)

        norm_tokens = [normalize_token(t) for t in tokens if normalize_token(t)]
        if not norm_tokens:
            return np.zeros(self.vector_size, dtype=np.float32)

        weighted_vecs = []
        for t in norm_tokens:
            # Sub-word aware vector from FastText
            v = self.model.wv[t]
            weight = self.idf_dict_.get(t, self.default_idf_)
            weighted_vecs.append(v * weight)

        if not weighted_vecs:
            return np.zeros(self.vector_size, dtype=np.float32)

        aggregate = np.sum(weighted_vecs, axis=0)
        norm = np.linalg.norm(aggregate)
        if norm > 1e-9:
            return (aggregate / norm).astype(np.float32)
        return np.zeros(self.vector_size, dtype=np.float32)

    def compute_cosine_similarity(self, resume_vec: np.ndarray, job_vec: np.ndarray) -> float:
        """
        Compute bounded cosine similarity [0.0, 1.0] between two vectors.
        Since vectors are already L2-normalized, cosine similarity is np.dot.
        Returns 0.0 if either vector is all zeros.
        """
        if resume_vec is None or job_vec is None:
            return 0.0

        r_norm = np.linalg.norm(resume_vec)
        j_norm = np.linalg.norm(job_vec)
        if r_norm < 1e-9 or j_norm < 1e-9:
            return 0.0

        dot = float(np.dot(resume_vec, job_vec))
        # Ensure bounded [0.0, 1.0]
        return float(np.clip(dot, 0.0, 1.0))
