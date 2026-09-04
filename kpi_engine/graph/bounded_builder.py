"""
Bounded Graph Construction: The Cage & The Brakes (§2.4, §4)
"""

from datetime import timedelta
from typing import List, Tuple, Dict, Any, Optional

from kpi_engine.data.models import AnchorNode, CandidateNode, CandidateNodeType
from kpi_engine.graph.dag_model import CausalDAG, DAGGraphPayload
from kpi_engine.config import CONFIG
from kpi_engine.memory.vector_store import PlaybookVectorStore


class BoundedGraphBuilder:
    """Stage 3: Graph Construction with deterministic bounding and Vector-RAG injection."""

    def __init__(self, config=CONFIG):
        self.config = config
        # The true JIT Graph-RAG Vector DB
        self.vector_store = PlaybookVectorStore()

    def apply_deterministic_pre_pruning(
        self,
        anchor: AnchorNode,
        nodes: List[CandidateNode],
    ) -> List[CandidateNode]:
        """The Cage: Temporal Bounding & Dimensional Intersection."""
        surviving_nodes: List[CandidateNode] = []

        # Dynamic Caging: Stretch window for slow systemic drifts
        if getattr(anchor, "trigger_rule", "") == "SYSTEMIC_DRIFT_ANOMALY":
            lookback_hours = getattr(self.config, "cage_pre_hours_drift", 720)
        else:
            lookback_hours = getattr(self.config, "cage_pre_hours", 48)

        window_start = anchor.timestamp - timedelta(hours=lookback_hours)
        window_end = anchor.timestamp + timedelta(hours=self.config.cage_post_hours)

        anchor_region = anchor.dimensions.get("region")
        anchor_platform = anchor.dimensions.get("platform")

        for node in nodes:
            # 1. Temporal Bounding: Strictly within [-48h, +12h]
            if not (window_start <= node.timestamp <= window_end):
                continue

            # 2. Dimensional Intersection:
            node_region = node.dimensions.get("region")
            node_platform = node.dimensions.get("platform")

            # Check Region match
            if anchor_region and node_region:
                if node_region.lower() not in ["all", "global", anchor_region.lower()]:
                    continue  # Prune mismatched region

            # Check Platform match
            if anchor_platform and node_platform:
                if node_platform.lower() not in ["all", "global", anchor_platform.lower()]:
                    continue  # Prune mismatched platform

            surviving_nodes.append(node)
            
        # --- JUST-IN-TIME GRAPH-RAG (Vector Injection) ---
        query = f"Anomaly in {anchor.metric_name}. Variance: {anchor.variance_pct:.2f}%."
        historical_incidents = self.vector_store.search_similar_incidents(query, k=2)
        
        for inc in historical_incidents:
            import uuid
            
            node_type = CandidateNodeType.HISTORICAL_PRECEDENT
            if inc.get("type") == "Noise":
                node_type = CandidateNodeType.HISTORICAL_NOISE
                
            inc_region = inc.get("region", "Global")
            is_cross_regional = False
            if anchor_region and inc_region not in ["Global", "All"]:
                if anchor_region.lower() != inc_region.lower():
                    is_cross_regional = True
                
            hist_node = CandidateNode(
                node_id=f"HIST-{str(uuid.uuid4())[:8]}",
                node_type=node_type,
                title=inc["title"],
                content=inc["content"],
                timestamp=anchor.timestamp, # Treat historical precedent as contemporaneous for graphing
                dimensions={"similarity": f"{inc['similarity_score']:.4f}"},
                security_tier="PUBLIC_UNRESTRICTED",
                clearance_required="PUBLIC",
                metadata={
                    "historical_id": inc["node_id"], 
                    "similarity_score": inc["similarity_score"],
                    "is_cross_regional": is_cross_regional,
                    "historical_region": inc_region
                }
            )
            surviving_nodes.append(hist_node)

        return surviving_nodes

    def build_bounded_dag(
        self,
        anchor: AnchorNode,
        scored_nodes: List[Tuple[CandidateNode, float, float, float, str]],
    ) -> Tuple[CausalDAG, DAGGraphPayload, List[CandidateNode], List[CandidateNode]]:
        """The Brakes: Enforce 2-Hop depth limit and Threshold Pruning (W >= 0.65).
        Input scored_nodes: List of (node, composite_W, contextual_relevance, causal_impact, tier)
        Returns:
            (dag, payload, surviving_evidence_nodes, discarded_noise_nodes)
        """
        dag = CausalDAG()

        # Add Anchor Node (Hop 0)
        anchor_id = anchor.kpi_id
        dag.add_node(
            anchor_id,
            title=anchor.metric_name,
            node_type="Anchor_Node",
            is_anchor=True,
            current_value=anchor.current_value,
            variance_pct=anchor.variance_pct,
            dimensions=anchor.dimensions,
        )

        surviving_evidence: List[CandidateNode] = []
        discarded_noise: List[CandidateNode] = []
        pruned_edges_count = 0

        # Sort scored nodes descending by composite weight W
        sorted_scored = sorted(scored_nodes, key=lambda x: x[1], reverse=True)

        for node, w, cr, ci, tier in sorted_scored:
            # Threshold Pruning: Sever edges with W < 0.65
            if w < self.config.edge_prune_weight_threshold:
                pruned_edges_count += 1
                discarded_noise.append(node)
                continue

            # Add surviving node to DAG (Hop 1 / Hop 2)
            dag.add_node(
                node.node_id,
                title=node.title,
                node_type=node.node_type.value,
                content=node.content,
                is_masked=node.is_masked,
                dimensions=node.dimensions,
            )

            # Direct causal edge from node -> anchor
            dag.add_edge(
                source=node.node_id,
                target=anchor_id,
                weight=w,
                contextual_relevance=cr,
                causal_impact=ci,
                tier=tier,
            )

            surviving_evidence.append(node)

        payload = dag.to_payload(anchor_id=anchor_id, pruned_count=pruned_edges_count)
        return dag, payload, surviving_evidence, discarded_noise
