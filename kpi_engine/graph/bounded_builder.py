"""
Bounded Graph Construction: The Cage & The Brakes (§2.4, §4)

The Cage   : temporal window [-cage_pre_hours, +cage_post_hours] around A* (stretched for systemic drift)
             plus dimensional intersection (region / platform), then just-in-time Graph-RAG retrieval
             of similar historical incidents (similarity-thresholded).
The Brakes : edges with W below `edge_prune_weight_threshold` are severed, causal paths are capped at
             `max_traversal_hops`, and path weights are attenuated per extra hop.
"""

import uuid
from datetime import timedelta
from typing import List, Tuple, Dict, Any, Optional

from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType
from kpi_engine.graph.dag_model import CausalDAG, DAGGraphPayload
from kpi_engine.config import CONFIG
from kpi_engine.memory.vector_store import PlaybookVectorStore

HISTORICAL_TYPES = (CandidateNodeType.HISTORICAL_PRECEDENT, CandidateNodeType.HISTORICAL_NOISE)


class BoundedGraphBuilder:
    """Stage 3: Graph Construction with deterministic bounding and Vector-RAG injection."""

    def __init__(self, config=CONFIG, vector_store: Optional[PlaybookVectorStore] = None):
        self.config = config
        self.vector_store = vector_store or PlaybookVectorStore(config)
        self.last_cage_report: Dict[str, Any] = {}

    # ------------------------------------------------------------------ The Cage
    def build_history_query(self, anchor: AnchorNode, nodes: List[CandidateNode]) -> str:
        dims = " ".join(str(v) for k, v in anchor.dimensions.items() if k not in ("clustered_kpis",))
        direction = "dropped" if anchor.variance_pct < 0 else "spiked"
        evidence = " ".join(f"{n.title}. {n.content}." for n in nodes[:5])
        return f"{anchor.metric_name} {direction} {abs(anchor.variance_pct):.0f}%. {dims}. {evidence}"

    def apply_deterministic_pre_pruning(self, anchor: AnchorNode, nodes: List[CandidateNode]) -> List[CandidateNode]:
        """Returns caged evidence + retrieved historical context nodes. Details in `last_cage_report`."""
        surviving_nodes: List[CandidateNode] = []
        rejected: List[Dict[str, str]] = []

        if anchor.trigger_rule == "SYSTEMIC_DRIFT_ANOMALY":
            lookback_hours = self.config.cage_pre_hours_drift
        else:
            lookback_hours = self.config.cage_pre_hours

        window_start = anchor.timestamp - timedelta(hours=lookback_hours)
        window_end = anchor.timestamp + timedelta(hours=self.config.cage_post_hours)
        anchor_region = anchor.dimensions.get("region")
        anchor_platform = anchor.dimensions.get("platform")

        for node in nodes:
            if not (window_start <= node.timestamp <= window_end):
                rejected.append({"node_id": node.node_id, "title": node.title, "reason": "Outside temporal cage"})
                continue
            node_region = node.dimensions.get("region")
            node_platform = node.dimensions.get("platform")
            if anchor_region and node_region and node_region.lower() not in ["all", "global", anchor_region.lower()]:
                rejected.append({"node_id": node.node_id, "title": node.title, "reason": f"Region mismatch ({node_region})"})
                continue
            if anchor_platform and node_platform and node_platform.lower() not in ["all", "global", anchor_platform.lower()]:
                rejected.append({"node_id": node.node_id, "title": node.title, "reason": f"Platform mismatch ({node_platform})"})
                continue
            surviving_nodes.append(node)

        # --- Just-in-time Graph-RAG: similar past incidents / noise signatures ---
        query = self.build_history_query(anchor, surviving_nodes)
        historical_incidents = self.vector_store.search_similar_incidents(query, k=self.config.history_top_k)
        hist_nodes = []
        for inc in historical_incidents:
            node_type = CandidateNodeType.HISTORICAL_NOISE if inc.get("type") == "Noise" else CandidateNodeType.HISTORICAL_PRECEDENT
            inc_region = inc.get("region", "Global")
            is_cross_regional = bool(
                anchor_region and inc_region not in ("Global", "All") and anchor_region.lower() != inc_region.lower()
            )
            hist_nodes.append(CandidateNode(
                node_id=f"MEM-{inc['node_id']}-{uuid.uuid4().hex[:4]}",
                node_type=node_type,
                title=inc["title"],
                content=inc["content"],
                timestamp=anchor.timestamp,
                dimensions={"region": inc_region},
                metadata={
                    "historical_id": inc["node_id"],
                    "similarity_score": inc["similarity_score"],
                    "is_cross_regional": is_cross_regional,
                    "historical_region": inc_region,
                    "is_historical": True,
                    "kpi_id": inc.get("kpi_id"),
                    "human_flagged": inc.get("human_flagged", False),
                },
            ))

        self.last_cage_report = {
            "window": [window_start.isoformat(), window_end.isoformat()],
            "rejected": rejected,
            "history_query": query,
            "history_hits": historical_incidents,
        }
        return surviving_nodes + hist_nodes

    # ------------------------------------------------------------------ The Brakes
    def build_bounded_dag(
        self,
        anchor: AnchorNode,
        scored_nodes: List[Tuple],
    ) -> Tuple[CausalDAG, DAGGraphPayload, List[CandidateNode], List[CandidateNode], List[CandidateNode]]:
        """Assemble the bounded causal DAG.

        Input: (node, W, CR, CI, tier[, details]) tuples.
        Returns: (dag, payload, surviving_evidence, discarded_noise, historical_context)
          surviving_evidence is ordered by path weight (strongest causal driver first).
        """
        thr = self.config.edge_prune_weight_threshold
        max_hops = self.config.max_traversal_hops
        dag = CausalDAG()
        anchor_id = anchor.kpi_id
        dag.add_node(anchor_id, title=anchor.metric_name, node_type="Anchor_Node", is_anchor=True,
                     current_value=anchor.current_value, variance_pct=anchor.variance_pct,
                     dimensions=anchor.dimensions, hop=0)

        rows = [(t[0], t[1], t[2], t[3], t[4], t[5] if len(t) > 5 else {}) for t in scored_nodes]
        real = [r for r in rows if r[0].node_type not in HISTORICAL_TYPES]
        hist = [r for r in rows if r[0].node_type in HISTORICAL_TYPES]

        discarded: List[CandidateNode] = []
        hop_of: Dict[str, int] = {}
        path_w: Dict[str, float] = {}
        pruned = 0

        def add(node, w, cr, ci, tier, details, target, hop, relation, pw):
            dag.add_node(node.node_id, title=node.title, node_type=node.node_type.value, content=node.content,
                         is_masked=node.is_masked, dimensions=node.dimensions, hop=hop)
            dag.add_edge(node.node_id, target, weight=w, contextual_relevance=cr, causal_impact=ci, tier=tier,
                         relation=relation, hop=hop, path_weight=pw)
            hop_of[node.node_id] = hop
            path_w[node.node_id] = pw

        # Pass 1: direct drivers (no declared parent) -> hop 1
        pending = []
        for node, w, cr, ci, tier, details in sorted(real, key=lambda r: -r[1]):
            if w < thr:
                pruned += 1
                discarded.append(node)
                continue
            if node.metadata.get("causes"):
                pending.append((node, w, cr, ci, tier, details))
            else:
                add(node, w, cr, ci, tier, details, anchor_id, 1, "causes", w)

        # Pass 2..max_hops: nodes that act through another surviving node
        for _ in range(max(0, max_hops - 1) + 1):
            still = []
            for node, w, cr, ci, tier, details in pending:
                parent = node.metadata.get("causes")
                if parent in hop_of:
                    hop = hop_of[parent] + 1
                    if hop > max_hops:
                        pruned += 1
                        discarded.append(node)
                        continue
                    pw = min(w, path_w[parent]) * (self.config.hop_attenuation ** (hop - 1))
                    add(node, w, cr, ci, tier, details, parent, hop, node.metadata.get("relation", "drives"), pw)
                else:
                    still.append((node, w, cr, ci, tier, details))
            pending = still
        # Parent never survived: the node still explains the anchor directly
        for node, w, cr, ci, tier, details in pending:
            add(node, w, cr, ci, tier, details, anchor_id, 1, "causes", w)

        # Historical context nodes (not causal drivers)
        historical_context: List[CandidateNode] = []
        for node, w, cr, ci, tier, details in hist:
            if details.get("is_cross_regional") and node.node_type == CandidateNodeType.HISTORICAL_NOISE:
                continue
            dag.add_node(node.node_id, title=node.title, node_type=node.node_type.value, content=node.content,
                         is_masked=False, dimensions=node.dimensions, hop=1)
            dag.add_edge(node.node_id, anchor_id, weight=w, contextual_relevance=cr, causal_impact=ci, tier=tier,
                         relation="historical_context", hop=1, path_weight=0.0)
            historical_context.append(node)

        by_id = {r[0].node_id: r[0] for r in real}
        surviving = [by_id[nid] for nid in sorted(path_w, key=lambda k: (hop_of[k], -path_w[k]))]

        payload = dag.to_payload(anchor_id=anchor_id, pruned_count=pruned, hop_limit=max_hops, weight_threshold=thr)
        return dag, payload, surviving, discarded, historical_context
