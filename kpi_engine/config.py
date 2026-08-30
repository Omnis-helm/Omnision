"""
KPI Storytelling Engine - System Configuration (v3.0 / Extended Edition v2.0)
"""

from typing import Dict, Any
from pydantic import BaseModel


class SystemConfig(BaseModel):
    # Detection & Cold-Start parameters (Â§2.2, Â§5.5)
    mature_history_days: int = 30
    z_score_alert_threshold: float = 3.0
    z_score_shock_threshold: float = 5.0
    cold_start_static_tripwire: float = 0.05  # 5% flat deviation
    cold_start_ewma_alpha: float = 0.3
    graduation_threshold_samples: int = 30

    # Bounded Graph Construction (Â§2.4, Â§4)
    cage_pre_hours: int = 48
    cage_post_hours: int = 12
    max_traversal_hops: int = 2
    edge_prune_weight_threshold: float = 0.50

    # Causal Weighting parameters (Â§2.5, Â§5)
    # Contextual Relevance weights: W = alpha*Wt + beta*We + gamma*Ws
    alpha_wt: float = 0.35  # Temporal Proximity
    beta_we: float = 0.35   # Entity Overlap
    gamma_ws: float = 0.30  # Semantic Distance

    # Causal Impact weights: CI = delta*Wsnr + epsilon*Wcf
    delta_wsnr: float = 0.40  # Signal-to-Noise Ratio
    epsilon_wcf: float = 0.60  # Counterfactual Impact

    # Governance & RACI Authority Thresholds (Â§4.2, Â§10, Â§11)
    auto_approve_cost_ceiling_usd: float = 10000.0
    vp_approval_required_cost_usd: float = 100000.0

    # Continuous Learning Loop (Â§4.1.2, Â§13)
    model_penalty_decay_rate: float = 0.15  # eta in W_m^(t+1) = W_m^(t) * (1 - eta)
    model_reward_boost_rate: float = 0.10
    semantic_recalibration_step: float = 0.05

    # Telemetry & LLM Economics (Â§4.3.1, Â§12.3)
    token_budget_limit: int = 4000
    cost_per_1k_input_tokens_usd: float = 0.0025
    cost_per_1k_output_tokens_usd: float = 0.0100
    
        # LangGraph & Swarm Settings
    llm_provider: str = "mock"  # options: 'openai', 'anthropic', 'gemini', 'ollama', 'mock'
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    swarm_max_iterations: int = 3


# Global configuration instance
CONFIG = SystemConfig()

