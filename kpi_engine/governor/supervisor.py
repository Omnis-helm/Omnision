"""
Supervisor Framework, AI Gateway & Execution Controls (§4.3, §11, §12.3)

Owns the governance services shared by every investigation of one engine instance:
  * the prescriptive layers store, the Critic and the LangGraph swarm orchestrator
  * the Actor Swarm trust weights (tuned by human feedback)
  * the semantic payload cache + invalidation cascade
  * the pre-inference token budget governor and cumulative token / cost telemetry
"""

import copy
from typing import Dict, List, Any, Tuple, Optional

from kpi_engine.data.models import CandidateNode
from kpi_engine.suggester.layers_data import PrescriptiveLayersStore
from kpi_engine.suggester.dual_channel import DualChannelSuggester
from kpi_engine.governor.critic import TheCritic
from kpi_engine.governor.actor_swarm import ActorSwarm
from kpi_engine.governor.langgraph_orchestrator import SwarmOrchestrator
from kpi_engine.config import CONFIG


class SupervisorFramework:
    """Central programmatic gateway enforcing schema integrity, cost controls and cascade invalidation."""

    def __init__(self, layers_store: Optional[PrescriptiveLayersStore] = None, config=CONFIG):
        self.config = config
        self.store = layers_store or PrescriptiveLayersStore()
        self.swarm = ActorSwarm()
        # The orchestrator / suggester read the *live* trust weights dict, so feedback applies immediately.
        self.suggester = DualChannelSuggester(self.store, self.swarm.model_weights)
        self.critic = TheCritic(self.store, config)
        self.orchestrator = SwarmOrchestrator(self.store, self.swarm.model_weights, config)

        self.semantic_cache: Dict[str, Dict[str, Any]] = {}
        self.cumulative_token_spend: int = 0
        self.cumulative_cost_usd: float = 0.0

    # ------------------------------------------------------------------ cost controls
    def check_token_budget_governor(self, nodes: List[CandidateNode]) -> Tuple[List[CandidateNode], bool]:
        """Pre-inference cost control: keep only the strongest evidence that fits the token budget."""
        per = self.config.tokens_per_evidence_node
        if len(nodes) * per > self.config.token_budget_limit:
            return nodes[: max(1, self.config.token_budget_limit // per)], True
        return nodes, False

    def record_spend(self, input_tokens: int, output_tokens: int) -> float:
        cost = (input_tokens / 1000.0) * self.config.cost_per_1k_input_tokens_usd + \
               (output_tokens / 1000.0) * self.config.cost_per_1k_output_tokens_usd
        self.cumulative_token_spend += input_tokens + output_tokens
        self.cumulative_cost_usd += cost
        return round(cost, 6)

    # ------------------------------------------------------------------ semantic cache
    def cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        hit = self.semantic_cache.get(key)
        return copy.deepcopy(hit) if hit is not None else None

    def cache_put(self, key: str, kpi_id: str, result: Dict[str, Any]):
        self.semantic_cache[key] = {"kpi_id": kpi_id, "result": copy.deepcopy(result)}

    def execute_invalidation_cascade(self, kpi_id: Optional[str] = None) -> int:
        """Purge cached payloads for one KPI (or all) after a human changes the ground truth."""
        keys = [k for k, v in self.semantic_cache.items() if kpi_id is None or v["kpi_id"] == kpi_id]
        for k in keys:
            del self.semantic_cache[k]
        return len(keys)
