"""
Evidence Graph DAG Model using NetworkX (§2.4, §4)
"""

from typing import Dict, List, Any, Optional
import networkx as nx
from pydantic import BaseModel, Field


class DAGEdge(BaseModel):
    source: str
    target: str
    weight: float
    contextual_relevance: float
    causal_impact: float
    tier: str  # "Tier 1 Gold", "Tier 2 Silver", "Tier 3 Bronze"
    details: Dict[str, Any] = Field(default_factory=dict)


class DAGGraphPayload(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[DAGEdge]
    anchor_id: str
    hop_limit: int = 2
    is_acyclic: bool = True
    total_nodes: int = 0
    pruned_edges_count: int = 0


class CausalDAG:
    """Manages the NetworkX Directed Acyclic Graph for causal evidence."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, node_id: str, **attrs):
        self.graph.add_node(node_id, **attrs)

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float,
        contextual_relevance: float,
        causal_impact: float,
        tier: str,
        **extra_attrs
    ):
        self.graph.add_edge(
            source,
            target,
            weight=weight,
            contextual_relevance=contextual_relevance,
            causal_impact=causal_impact,
            tier=tier,
            **extra_attrs
        )

    def verify_acyclicity(self) -> bool:
        return nx.is_directed_acyclic_graph(self.graph)

    def to_payload(self, anchor_id: str, pruned_count: int = 0) -> DAGGraphPayload:
        nodes_data = []
        for node_id, data in self.graph.nodes(data=True):
            nodes_data.append({
                "id": node_id,
                "label": data.get("title", node_id),
                "type": data.get("node_type", "evidence"),
                "is_anchor": (node_id == anchor_id),
                "is_masked": data.get("is_masked", False),
                "content": data.get("content", ""),
                "dimensions": data.get("dimensions", {}),
            })

        edges_data = []
        for u, v, data in self.graph.edges(data=True):
            edges_data.append(DAGEdge(
                source=u,
                target=v,
                weight=round(data.get("weight", 0.0), 3),
                contextual_relevance=round(data.get("contextual_relevance", 0.0), 3),
                causal_impact=round(data.get("causal_impact", 0.0), 3),
                tier=data.get("tier", "Tier 1 Gold"),
                details=data,
            ))

        return DAGGraphPayload(
            nodes=nodes_data,
            edges=edges_data,
            anchor_id=anchor_id,
            is_acyclic=self.verify_acyclicity(),
            total_nodes=len(nodes_data),
            pruned_edges_count=pruned_count,
        )
