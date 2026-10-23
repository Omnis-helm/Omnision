"""
TypedDict representing the shared state of the LangGraph swarm execution.
Keys annotated with `operator.add` are reducers: nodes return deltas that are summed / concatenated,
which makes the parallel primary and Blue-Sky branches safe to run in the same super-step.
"""

import operator
from typing import TypedDict, Annotated, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    # Inputs
    anchor_context: Dict[str, Any]
    causal_evidence: List[Dict[str, Any]]
    historical_context: List[Dict[str, Any]]
    context: Dict[str, Any]
    user_role: str
    primary_llm_provider: str
    bluesky_llm_provider: str

    # Primary channel
    candidate_pool: List[Dict[str, Any]]        # batch produced by the current RCA iteration
    pending_review: List[Dict[str, Any]]        # passed the Critic, awaiting the Supervisor
    proposals: List[Dict[str, Any]]             # every proposal evaluated so far
    approved_proposals: List[Dict[str, Any]]
    rejected_proposals: List[Dict[str, Any]]
    narrative: str
    narrative_source: str

    # Blue-Sky channel (sandbox)
    blue_sky_proposals: List[Dict[str, Any]]
    blue_sky_critique: str
    blue_sky_iteration: int

    # Governance loop
    supervisor_feedback: Optional[str]
    iteration_count: int
    final_status: str  # PENDING | PENDING_LLM_REVIEW | APPROVED | REJECTED | MAX_ITERATIONS_REACHED

    # Telemetry (reducers)
    tokens_input: Annotated[int, operator.add]
    tokens_output: Annotated[int, operator.add]
    cache_hits: Annotated[int, operator.add]
    llm_errors: Annotated[List[str], operator.add]


ADDITIVE_KEYS = {"tokens_input", "tokens_output", "cache_hits", "llm_errors"}


def merge_state(state: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a node update the same way LangGraph would (used by the sequential fallback)."""
    for k, v in (update or {}).items():
        if k in ADDITIVE_KEYS:
            state[k] = state.get(k, [] if isinstance(v, list) else 0) + v
        else:
            state[k] = v
    return state
