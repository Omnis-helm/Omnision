"""
Local ML Engine & Thread-Safe Performance Tools
- ThreadSafeModelLoader: lazy loading with per-model mutex locks for heavy NLP/ML models
- Text utilities: tokenizer with light stemming + domain synonyms, lexical & dense similarity
- LocalSemanticSupervisor: fast local semantic alignment evaluator (root cause <-> proposed action)
- LocalVectorStore: zero-dependency TF-IDF / cosine similarity vector store
- LLMResponseCache: hash-keyed, size-bounded LRU response cache for LLM / swarm outputs
"""

import hashlib
import json
import math
import re
import threading
from collections import OrderedDict
from typing import Dict, Any, List, Optional, Tuple, Iterable


class ThreadSafeModelLoader:
    """Singleton registry with mutex locks for lazy-loading heavy NLP/ML models.

    Failed loads are remembered so a missing package/network does not re-trigger an expensive
    attempt on every call.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._models = {}
                cls._instance._model_locks = {}
                cls._instance._failures = {}
            return cls._instance

    def get_or_load_model(self, model_key: str, loader_fn):
        if model_key in self._failures:
            raise RuntimeError(f"Model '{model_key}' previously failed to load: {self._failures[model_key]}")
        with self._lock:
            lock = self._model_locks.setdefault(model_key, threading.Lock())
        if model_key not in self._models:
            with lock:
                if model_key not in self._models:
                    try:
                        self._models[model_key] = loader_fn()
                    except Exception as e:  # remember the failure
                        self._failures[model_key] = str(e)
                        raise
        return self._models[model_key]


# ----------------------------------------------------------------------------- text utilities
STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was", "this",
    "that", "be", "as", "it", "its", "from", "into", "via", "are", "were", "has", "have", "had", "than",
    "then", "but", "not", "no", "all", "across", "due", "after", "while", "when", "we", "our",
}

# Canonical forms for domain vocabulary (applied after light stemming)
SYNONYMS = {
    "declin": "drop", "decreas": "drop", "fall": "drop", "fell": "drop", "dropp": "drop", "contraction": "drop",
    "slump": "drop", "dip": "drop",
    "timeout": "latency", "slow": "latency", "lag": "latency",
    "discount": "promotion", "promo": "promotion", "sale": "promotion", "flash": "promotion", "markdown": "promotion",
    "revert": "rollback", "roll": "rollback", "downgrade": "rollback",
    "stripe": "payment", "adyen": "payment", "charge": "payment",
    "pricing": "price", "priced": "price",
    "advisory": "advisor", "advisers": "advisor", "adviser": "advisor",
    "faceid": "biometric", "touchid": "biometric",
    "authentication": "auth", "login": "auth",
    "acquisition": "m&a", "merger": "m&a",
    "conveyor": "warehouse",
    "tariffs": "tariff", "surcharge": "tariff",
    "3pl": "logistics", "carrier": "logistics", "shipping": "logistics",
    "penalty": "fee", "fine": "fee", "fees": "fee",
}


def _stem(word: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(word) > 4 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9&][a-z0-9_&\-\.]*[a-z0-9]|[a-z0-9]", (text or "").lower())
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        s = _stem(w)
        out.append(SYNONYMS.get(s, s))
    return out


def lexical_similarity(a: str, b: str) -> float:
    """Blend of Jaccard and overlap coefficient on canonical token sets, in [0, 1]."""
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    overlap = inter / min(len(ta), len(tb))
    return round(0.5 * jaccard + 0.5 * overlap, 4)


def dense_similarity(a: str, b: str) -> Optional[float]:
    """Cosine similarity with MiniLM embeddings if enabled and available, else None."""
    from kpi_engine.config import CONFIG
    if not CONFIG.enable_dense_embeddings:
        return None
    try:
        import numpy as np
        from langchain_huggingface import HuggingFaceEmbeddings
        emb = ThreadSafeModelLoader().get_or_load_model(
            "hf_embeddings", lambda: HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        )
        v1, v2 = np.array(emb.embed_query(a)), np.array(emb.embed_query(b))
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if not n1 or not n2:
            return 0.0
        return float(max(0.0, min(1.0, float(v1 @ v2) / (n1 * n2))))
    except Exception:
        return None


def semantic_similarity(a: str, b: str) -> float:
    dense = dense_similarity(a, b)
    return dense if dense is not None else lexical_similarity(a, b)


class LLMResponseCache:
    """Thread-safe bounded LRU response cache for LLM and swarm outputs."""
    _cache: "OrderedDict[str, Any]" = OrderedDict()
    _lock = threading.Lock()
    max_entries = 512

    @staticmethod
    def make_key(*parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        with cls._lock:
            if key in cls._cache:
                cls._cache.move_to_end(key)
                return json.loads(json.dumps(cls._cache[key]))  # defensive copy
            return None

    @classmethod
    def set(cls, key: str, value: Any):
        with cls._lock:
            cls._cache[key] = json.loads(json.dumps(value, default=str))
            cls._cache.move_to_end(key)
            while len(cls._cache) > cls.max_entries:
                cls._cache.popitem(last=False)

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache.clear()


class LocalSemanticSupervisor:
    """Fast local semantic alignment evaluator between proposed actions and causal drivers."""

    @staticmethod
    def tokenize(text: str) -> set:
        return set(tokenize(text))

    @classmethod
    def alignment_score(cls, causes: Iterable[str], proposed_action: str) -> float:
        """Best alignment of the action against the ranked causes (primary weighted 1.0, others 0.8)."""
        best = 0.0
        for rank, cause in enumerate(causes):
            if not cause:
                continue
            w = 1.0 if rank == 0 else 0.8
            best = max(best, w * semantic_similarity(cause, proposed_action))
        return round(best, 4)

    @classmethod
    def evaluate_alignment(
        cls, primary_cause, proposed_action: str, threshold: float = 0.15
    ) -> Tuple[str, str, float]:
        causes = [primary_cause] if isinstance(primary_cause, str) else list(primary_cause)
        if not proposed_action.strip():
            return "REJECTED", "Empty action.", 0.0
        score = cls.alignment_score(causes, proposed_action)
        if score >= threshold:
            return "APPROVED", f"Action aligns with the causal evidence (semantic score {score:.2f} >= {threshold:.2f}).", score
        return "REJECTED", f"Action does not address the identified root cause (semantic score {score:.2f} < {threshold:.2f}).", score


class LocalVectorStore:
    """Pure Python TF-IDF cosine similarity vector store."""

    def __init__(self, documents: Optional[List[Any]] = None):
        self.documents: List[Any] = []
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_vectors: List[Dict[int, float]] = []
        if documents:
            self.add_documents(documents)

    def _fit_transform(self):
        doc_tokens_list = [tokenize(doc.page_content) for doc in self.documents]
        vocab_set = sorted({t for tokens in doc_tokens_list for t in tokens})
        self._vocab = {term: idx for idx, term in enumerate(vocab_set)}
        num_docs = len(self.documents)
        df_counts = {term: 0 for term in self._vocab}
        for tokens in doc_tokens_list:
            for t in set(tokens):
                df_counts[t] += 1
        self._idf = {term: math.log((1 + num_docs) / (1 + c)) + 1.0 for term, c in df_counts.items()}
        self._doc_vectors = [self._vectorize_tokens(tokens) for tokens in doc_tokens_list]

    def _vectorize_tokens(self, tokens: List[str]) -> Dict[int, float]:
        if not tokens or not self._vocab:
            return {}
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec = {self._vocab[t]: (c / len(tokens)) * self._idf.get(t, 1.0) for t, c in tf.items() if t in self._vocab}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        return {k: v / norm for k, v in vec.items()} if norm > 0 else {}

    def add_documents(self, docs: List[Any]):
        self.documents.extend(docs)
        self._fit_transform()

    def similarity_search_with_relevance_scores(self, query: str, k: int = 3) -> List[Tuple[Any, float]]:
        """Returns (doc, cosine similarity in [0,1]) sorted by similarity descending."""
        if not self.documents:
            return []
        q_vec = self._vectorize_tokens(tokenize(query))
        scored = []
        for doc, d_vec in zip(self.documents, self._doc_vectors):
            sim = sum(v * d_vec.get(i, 0.0) for i, v in q_vec.items())
            scored.append((doc, max(0.0, min(1.0, sim))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def similarity_search_with_score(self, query: str, k: int = 3) -> List[Tuple[Any, float]]:
        """Distance-style API (lower = more similar), kept for LangChain compatibility."""
        return [(d, round(1.0 - s, 6)) for d, s in self.similarity_search_with_relevance_scores(query, k)]
