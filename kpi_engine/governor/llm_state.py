"""
TypedDict representing the State of the LangGraph execution.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class AgentState(TypedDict):
    anchor_context: Dict[str, Any]
    causal_evidence: List[Dict[str, Any]]
    context: Dict[str, Any]
    
    # Swarm outputs
    proposals: List[Dict[str, Any]]
    
    # Governance loop
    supervisor_feedback: Optional[str]
    iteration_count: int
    final_status: str # "PENDING", "APPROVED", "REJECTED", "MAX_ITERATIONS_REACHED"
    
    # Telemetry
    tokens_consumed: int
