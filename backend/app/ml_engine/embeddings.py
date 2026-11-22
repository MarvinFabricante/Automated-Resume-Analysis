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
from typing import List, Sequence, Optional, Tuple, Set, Any
import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
except ImportError:
    TfidfVectorizer = None
    TruncatedSVD = None

try:
    from gensim.models import FastText
except ImportError:
    FastText = None

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
    "ml": "machine learning",
    "ai/ml": "machine learning",
    "qc": "quality control",
    "qa/qc": "quality control",
    "nlp": "natural language processing",
    "js": "javascript",
    "ts": "typescript",
}


def normalize_token(token: str) -> str:
    """
    Normalize individual skill or job title token.
    Preserves specialized programming characters (e.g. c++, c#, .net)
    and maps common framework aliases to standard canonical forms.
    Strips no-value markers (e.g. 'none', 'n/a', 'wala').
    """
    if not token:
        return ""
    from app.services.requirement_rules import is_no_value

    if is_no_value(token):
        return ""
    t = token.strip().lower()
    t = CANONICAL_REPLACEMENTS.get(t, t)
    if is_no_value(t):
        return ""
    # Replace separators with underscore if multi-word
    t = re.sub(r"[\s\-\/\.]+", "_", t)
    t = t.strip("_")
    return "" if is_no_value(t) else t


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

        self.model: Optional[Any] = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.idf_dict_: dict[str, float] = {}
        self.default_idf_: float = 1.0
        self.token_vectors_: dict[str, np.ndarray] = {}
        self.subword_vectorizer_: Optional[TfidfVectorizer] = None
        self.subword_svd_: Optional[TruncatedSVD] = None
        self._corpus_history: List[List[str]] = []

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

    def _fit_contextual_svd(self, clean_corpus: List[List[str]]) -> None:
        """
        Build contextual co-occurrence + sub-word character n-gram embeddings using
        scikit-learn TF-IDF + TruncatedSVD. Ensures strong intra-domain similarity
        and low cross-domain similarity even when gensim is unavailable.
        """
        vocab_list: List[str] = []
        vocab_idx: dict[str, int] = {}
        for sent in clean_corpus:
            for tok in sent:
                if tok not in vocab_idx:
                    vocab_idx[tok] = len(vocab_list)
                    vocab_list.append(tok)

        n_vocab = len(vocab_list)
        if n_vocab == 0:
            return

        # 1. Contextual co-occurrence matrix with PMI-like log weighting
        cooc = np.zeros((n_vocab, n_vocab), dtype=np.float32)
        for sent in clean_corpus:
            indices = [vocab_idx[t] for t in sent if t in vocab_idx]
            for i_pos, idx_a in enumerate(indices):
                cooc[idx_a, idx_a] += 2.0
                win_start = max(0, i_pos - self.window)
                win_end = min(len(indices), i_pos + self.window + 1)
                for j_pos in range(win_start, win_end):
                    if i_pos != j_pos:
                        idx_b = indices[j_pos]
                        cooc[idx_a, idx_b] += 1.0

        cooc_log = np.log1p(cooc)
        n_comp = max(2, min(self.vector_size, n_vocab - 1))
        if TruncatedSVD is not None:
            svd = TruncatedSVD(n_components=n_comp, random_state=self.seed)
            dense_vecs = svd.fit_transform(cooc_log)
        else:
            u, s, _ = np.linalg.svd(cooc_log, full_matrices=False)
            dense_vecs = u[:, :n_comp] * s[:n_comp]

        # Pad to self.vector_size if vocabulary is smaller than vector_size
        if dense_vecs.shape[1] < self.vector_size:
            pad = np.zeros((n_vocab, self.vector_size - dense_vecs.shape[1]), dtype=np.float32)
            dense_vecs = np.hstack([dense_vecs, pad])

        self.token_vectors_ = {}
        for tok, idx in vocab_idx.items():
            vec = np.maximum(0.0, dense_vecs[idx]).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 1e-9:
                vec = (vec / norm).astype(np.float32)
            self.token_vectors_[tok] = vec

        # 2. Sub-word character n-gram model for out-of-vocabulary resilience
        if TfidfVectorizer is not None and TruncatedSVD is not None:
            try:
                sub_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(self.min_n, min(4, self.max_n)))
                X_sub = sub_vec.fit_transform(vocab_list)
                sub_comp = max(2, min(self.vector_size, X_sub.shape[0] - 1, X_sub.shape[1] - 1))
                sub_svd = TruncatedSVD(n_components=sub_comp, random_state=self.seed)
                sub_svd.fit(X_sub)
                self.subword_vectorizer_ = sub_vec
                self.subword_svd_ = sub_svd
            except Exception:
                self.subword_vectorizer_ = None
                self.subword_svd_ = None
        else:
            self.subword_vectorizer_ = None
            self.subword_svd_ = None

    def train(self, corpus: List[List[str]]) -> "FastTextEmbeddingEngine":
        """
        Train FastText model (or contextual SVD + sub-word embeddings fallback)
        and fit TF-IDF vectorizer over the domain corpus.
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

        self._corpus_history = list(clean_corpus)
        self._fit_contextual_svd(clean_corpus)

        if FastText is not None:
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
        else:
            logger.info(f"Trained contextual sub-word embedding engine with {len(clean_corpus)} sentences.")
            self.model = self.token_vectors_

        # Fit TF-IDF on token document strings to compute inverse document frequencies
        if TfidfVectorizer is not None:
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
        else:
            n_docs = len(clean_corpus)
            df_counts: dict[str, int] = {}
            for sent in clean_corpus:
                for tok in set(sent):
                    df_counts[tok] = df_counts.get(tok, 0) + 1
            self.idf_dict_ = {
                tok: float(np.log((1.0 + n_docs) / (1.0 + df)) + 1.0)
                for tok, df in df_counts.items()
            }
            self.default_idf_ = float(np.median(list(self.idf_dict_.values()))) if self.idf_dict_ else 1.0

        return self

    def update(self, new_corpus: List[List[str]]) -> "FastTextEmbeddingEngine":
        """
        Incrementally update vocabulary and fine-tune on newly observed tokens.
        """
        if self.model is None and not getattr(self, "token_vectors_", None):
            return self.train(new_corpus)

        clean_new = []
        for sent in new_corpus:
            norm_sent = [normalize_token(t) for t in sent if normalize_token(t)]
            if norm_sent:
                clean_new.append(norm_sent)

        if not clean_new:
            return self

        history = list(getattr(self, "_corpus_history", [])) + clean_new
        self._corpus_history = history
        self._fit_contextual_svd(history)

        if FastText is not None and hasattr(self.model, "build_vocab"):
            self.model.build_vocab(clean_new, update=True)
            self.model.train(
                clean_new,
                total_examples=len(clean_new),
                epochs=max(15, self.epochs // 2),
            )
        else:
            self.model = self.token_vectors_

        # Update IDF dictionary
        for sent in clean_new:
            for tok in sent:
                if tok not in self.idf_dict_:
                    self.idf_dict_[tok] = self.default_idf_

        return self

    def get_token_vector(self, token: str) -> np.ndarray:
        """
        Get vector for single token. Returns L2-normalized 1D vector.
        Generates representations even for subwords/OOV.
        """
        norm_t = normalize_token(token)
        token_vecs = getattr(self, "token_vectors_", None) or {}
        if not norm_t or (self.model is None and not token_vecs):
            return np.zeros(self.vector_size, dtype=np.float32)

        # 1. Contextual co-occurrence vector if token is in known vocabulary
        if norm_t in token_vecs:
            return token_vecs[norm_t].copy()

        # Check constituent words of multi-word token (e.g. "frontend_engineer" -> "frontend", "engineer")
        sub_parts = [p for p in norm_t.split("_") if p in token_vecs]
        if sub_parts:
            agg = np.sum([token_vecs[p] for p in sub_parts], axis=0)
            norm = np.linalg.norm(agg)
            if norm > 1e-9:
                return (agg / norm).astype(np.float32)

        # 2. Gensim FastText subword lookup if available
        if FastText is not None and hasattr(self.model, "wv"):
            raw_vec = self.model.wv[norm_t]
            norm = np.linalg.norm(raw_vec)
            if norm > 1e-9:
                return (raw_vec / norm).astype(np.float32)

        # 3. Sub-word character n-gram fallback
        sub_vec = getattr(self, "subword_vectorizer_", None)
        sub_svd = getattr(self, "subword_svd_", None)
        if sub_vec is not None and sub_svd is not None:
            try:
                x_s = sub_vec.transform([norm_t])
                proj = np.maximum(0.0, sub_svd.transform(x_s)[0]).astype(np.float32)
                if len(proj) < self.vector_size:
                    proj = np.pad(proj, (0, self.vector_size - len(proj)))
                norm = np.linalg.norm(proj)
                if norm > 1e-9:
                    return (proj / norm).astype(np.float32)
            except Exception:
                pass

        return np.zeros(self.vector_size, dtype=np.float32)

    def vectorize_tokens(self, tokens: Sequence[str]) -> np.ndarray:
        """
        Convert extracted skills or job titles into an L2-normalized 1D numpy vector array.
        Weights each token by its TF-IDF IDF score.
        If tokens is empty or all vectors are zero, returns zero vector array of shape (vector_size,).
        """
        token_vecs = getattr(self, "token_vectors_", None) or {}
        if not tokens or (self.model is None and not token_vecs):
            return np.zeros(self.vector_size, dtype=np.float32)

        norm_tokens = [normalize_token(t) for t in tokens if normalize_token(t)]
        if not norm_tokens:
            return np.zeros(self.vector_size, dtype=np.float32)

        weighted_vecs = []
        for t in norm_tokens:
            v = self.get_token_vector(t)
            if np.linalg.norm(v) > 1e-9:
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
