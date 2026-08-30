"""
Just-in-Time Graph-RAG Vector Store (Memory Module)
Uses FAISS to embed and retrieve historical incidents.
"""
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from kpi_engine.config import CONFIG

class PlaybookVectorStore:
    def __init__(self):
        self._init_embeddings()
        self.vector_store = None
        self._seed_store_if_empty()

    def _init_embeddings(self):
        api_key = os.getenv("OPENAI_API_KEY", CONFIG.openai_api_key)
        if api_key and api_key != "your_openai_api_key_here":
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(api_key=api_key)
        else:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            except ImportError:
                from langchain_core.embeddings import Embeddings
                class MockEmbeddings(Embeddings):
                    def embed_documents(self, texts):
                        return [[0.1]*384 for _ in texts]
                    def embed_query(self, text):
                        return [0.1]*384
                self.embeddings = MockEmbeddings()

    def _seed_store_if_empty(self):
        """Pre-seeds the vector store with historical playbook incidents and known noise."""
        historical_docs = [
            Document(
                page_content="West Region Checkout Conversion Rate dropped by 12% due to Payment Gateway Latency Spike. Mitigation applied: Rolled back Stripe integration to v2.1. Critic initially rejected, human override approved.",
                metadata={"id": "HIST-001", "type": "Incident", "impact": "High", "region": "West"}
            ),
            Document(
                page_content="Cart Abandonment spiked because of unexpected Shipping Cost Increase. Marketing tried a discount code, but root cause was 3rd party logistics API failure.",
                metadata={"id": "HIST-002", "type": "Incident", "impact": "Medium", "region": "Global"}
            ),
            Document(
                page_content="Cold Start Metric: Drone Delivery Volume dropped 50% due to regulatory flight bans in Zone A. No technical rollback possible. Executive override to shift fleet to Zone B.",
                metadata={"id": "HIST-003", "type": "Incident", "impact": "High", "region": "Zone A"}
            ),
            Document(
                page_content="False Alarm: Ad Clicks dropped 20% on a weekend. Investigation proved this is natural stochastic variance (noise) caused by a public holiday. No action required.",
                metadata={"id": "NOISE-001", "type": "Noise", "impact": "Zero", "region": "West"}
            ),
            Document(
                page_content="Data Pipeline Lag: Active Users dropped to 0 for 5 minutes. Root cause was Datadog telemetry scraping delay. This is a logging artifact, not a real business drop.",
                metadata={"id": "NOISE-002", "type": "Noise", "impact": "Zero", "region": "Global"}
            )
        ]
        
        # Ingest into FAISS
        self.vector_store = FAISS.from_documents(historical_docs, self.embeddings)

    def append_incident(self, text: str, metadata: dict):
        """Dynamically appends a new incident (or noise signature) to the Vector DB."""
        doc = Document(page_content=text, metadata=metadata)
        if self.vector_store:
            self.vector_store.add_documents([doc])
        else:
            self.vector_store = FAISS.from_documents([doc], self.embeddings)

    def search_similar_incidents(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """Retrieves top K similar historical incidents or noise profiles."""
        if not self.vector_store:
            return []
            
        results = self.vector_store.similarity_search_with_score(query, k=k)
        
        incidents = []
        for doc, score in results:
            inc_type = doc.metadata.get('type', 'Incident')
            incidents.append({
                "node_id": doc.metadata.get("id", "HIST-UNK"),
                "title": f"Historical {'False Alarm' if inc_type == 'Noise' else 'RCA'}: {doc.metadata.get('type', 'Unknown')} Profile",
                "content": doc.page_content,
                "type": inc_type,
                "region": doc.metadata.get("region", "Global"),
                "similarity_score": float(score)
            })
            
        return incidents
