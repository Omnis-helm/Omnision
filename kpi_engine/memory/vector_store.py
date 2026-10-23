"""
Just-in-Time Graph-RAG Vector Store (Institutional Memory)

Stores historical incident post-mortems and known noise signatures. Retrieval returns a relevance
score in [0, 1] (higher = more similar) regardless of backend, so downstream thresholds are stable:
  * LocalVectorStore (default, zero-dependency TF-IDF cosine) when PREFER_LOCAL_TOOLS=True
  * LangChain FAISS + embeddings when PREFER_LOCAL_TOOLS=False and the packages are installed
"""
import os
from typing import List, Dict, Any, Optional

from kpi_engine.config import CONFIG
from kpi_engine.ml.local_ml_engine import LocalVectorStore, ThreadSafeModelLoader

try:
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    LANGCHAIN_FAISS_AVAILABLE = True
except ImportError:
    FAISS = None
    LANGCHAIN_FAISS_AVAILABLE = False

    class Document:  # minimal stand-in
        def __init__(self, page_content: str, metadata: dict):
            self.page_content = page_content
            self.metadata = metadata


SEED_INCIDENTS = [
    ("West Region Checkout Conversion Rate dropped by 12% due to Payment Gateway Latency Spike (Stripe API timeouts). "
     "Mitigation applied: rolled back the Stripe gateway integration and shifted traffic to the backup gateway.",
     {"id": "HIST-001", "type": "Incident", "impact": "High", "region": "West"}),
    ("Cart Abandonment spiked because of unexpected Shipping Cost Increase. Marketing tried a discount code, "
     "but root cause was 3rd party logistics API failure.",
     {"id": "HIST-002", "type": "Incident", "impact": "Medium", "region": "Global"}),
    ("West Region Daily Net Revenue dropped 11% when a competitor ran an electronics flash sale while we were discounting. "
     "Price-matching the top SKUs and a loyalty bundle recovered most of the order volume within two days.",
     {"id": "HIST-004", "type": "Incident", "impact": "High", "region": "West"}),
    ("Mobile checkout conversion fell after an iOS SDK release broke biometric FaceID authentication. "
     "Disabling the biometric step behind a feature flag and shipping an SDK hotfix restored conversion.",
     {"id": "HIST-005", "type": "Incident", "impact": "High", "region": "Global"}),
    ("Gross Margin dropped after a one-off non-recurring advisory fee was booked in the operating period. "
     "Finance reclassified it as a one-time charge against corporate reserve and reported adjusted margin.",
     {"id": "HIST-006", "type": "Incident", "impact": "Medium", "region": "Global"}),
    ("Cold Start Metric: Drone Delivery Volume dropped 50% due to regulatory flight bans in Zone A. No technical rollback "
     "possible. Executive override to shift fleet to Zone B.",
     {"id": "HIST-003", "type": "Incident", "impact": "High", "region": "Zone A"}),
    ("False Alarm: Ad Clicks dropped 20% on a weekend. Investigation proved this is natural stochastic variance (noise) "
     "caused by a public holiday. No action required.",
     {"id": "NOISE-001", "type": "Noise", "impact": "Zero", "region": "West"}),
    ("Data Pipeline Lag: Active Users dropped to 0 for 5 minutes. Root cause was Datadog telemetry scraping delay. "
     "This is a logging artifact, not a real business drop.",
     {"id": "NOISE-002", "type": "Noise", "impact": "Zero", "region": "Global"}),
]


class PlaybookVectorStore:
    def __init__(self, config=CONFIG):
        self.config = config
        self.embeddings = None
        self.vector_store = None
        self.backend = "local_tfidf"
        self._seed_store()

    # ------------------------------------------------------------------ backends
    def _load_embeddings(self):
        api_key = os.getenv("OPENAI_API_KEY", self.config.openai_api_key)
        if api_key and api_key != "your_openai_api_key_here":
            try:
                from langchain_openai import OpenAIEmbeddings
                return OpenAIEmbeddings(api_key=api_key)
            except Exception:
                pass
        from langchain_huggingface import HuggingFaceEmbeddings
        return ThreadSafeModelLoader().get_or_load_model(
            "hf_embeddings", lambda: HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        )

    def _seed_store(self):
        docs = [Document(page_content=t, metadata=dict(m)) for t, m in SEED_INCIDENTS]
        if not self.config.prefer_local_tools and LANGCHAIN_FAISS_AVAILABLE:
            try:
                self.embeddings = self._load_embeddings()
                self.vector_store = FAISS.from_documents(docs, self.embeddings)
                self.backend = "faiss"
                return
            except Exception:
                self.embeddings = None
        self.vector_store = LocalVectorStore(docs)
        self.backend = "local_tfidf"

    # ------------------------------------------------------------------ API
    def append_incident(self, text: str, metadata: dict):
        """Dynamically appends a new incident (or noise signature) to the vector DB."""
        self.vector_store.add_documents([Document(page_content=text, metadata=dict(metadata))])

    def search_similar_incidents(
        self, query: str, k: int = 3, min_similarity: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Top-k incidents with relevance in [0, 1], filtered by `min_similarity`."""
        if not self.vector_store:
            return []
        min_sim = self.config.history_min_similarity if min_similarity is None else min_similarity
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
        except Exception:
            results = []

        incidents = []
        for doc, score in results:
            score = float(max(0.0, min(1.0, score)))
            if score < min_sim:
                continue
            inc_type = doc.metadata.get("type", "Incident")
            incidents.append({
                "node_id": doc.metadata.get("id", "HIST-UNK"),
                "title": f"Historical {'False Alarm' if inc_type == 'Noise' else 'Precedent'} {doc.metadata.get('id', '')}".strip(),
                "content": doc.page_content,
                "type": inc_type,
                "region": doc.metadata.get("region", "Global"),
                "kpi_id": doc.metadata.get("kpi_id"),
                "human_flagged": bool(doc.metadata.get("human_flagged", False)),
                "similarity_score": round(score, 4),
            })
        return incidents
