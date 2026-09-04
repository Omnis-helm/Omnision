import os
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel


def _load_env_file():
    """Simple parser to load .env variables into os.environ if present."""
    env_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v

_load_env_file()


class SystemConfig(BaseModel):
    # Detection & Cold-Start parameters (§2.2, §5.5)
    mature_history_days: int = 30
    z_score_alert_threshold: float = 3.0
    z_score_shock_threshold: float = 5.0
    cold_start_static_tripwire: float = 0.05  # 5% flat deviation
    cold_start_ewma_alpha: float = 0.3
    graduation_threshold_samples: int = 30

    # Bounded Graph Construction (§2.4, §4)
    cage_pre_hours: int = 48
    cage_pre_hours_drift: int = 720  # 30 days for systemic drift
    cage_post_hours: int = 12
    max_traversal_hops: int = 2
    edge_prune_weight_threshold: float = 0.50

    # Causal Weighting parameters (§2.5, §5)
    alpha_wt: float = 0.35  # Temporal Proximity
    beta_we: float = 0.35   # Entity Overlap
    gamma_ws: float = 0.30  # Semantic Distance

    # Causal Impact weights: CI = delta*Wsnr + epsilon*Wcf
    delta_wsnr: float = 0.40  # Signal-to-Noise Ratio
    epsilon_wcf: float = 0.60  # Counterfactual Impact

    # Governance & RACI Authority Thresholds (§4.2, §10, §11)
    auto_approve_cost_ceiling_usd: float = 10000.0
    vp_approval_required_cost_usd: float = 100000.0

    # Continuous Learning Loop (§4.1.2, §13)
    model_penalty_decay_rate: float = 0.15
    model_reward_boost_rate: float = 0.10
    semantic_recalibration_step: float = 0.05

    # Telemetry & LLM Economics (§4.3.1, §12.3)
    token_budget_limit: int = 4000
    cost_per_1k_input_tokens_usd: float = 0.0025
    cost_per_1k_output_tokens_usd: float = 0.0100
    
    # Performance & Local Optimization Settings
    prefer_local_tools: bool = os.getenv("PREFER_LOCAL_TOOLS", "True").lower() == "true"
    enable_llm_cache: bool = os.getenv("ENABLE_LLM_CACHE", "True").lower() == "true"
    enable_local_ml_models: bool = os.getenv("ENABLE_LOCAL_ML_MODELS", "True").lower() == "true"

    # LangGraph & Swarm Settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")  # options: 'openai', 'anthropic', 'gemini', 'ollama', 'mock', 'local'
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    huggingface_api_key: str = os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_API_KEY", ""))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")
    swarm_max_iterations: int = 3


# Global configuration instance
CONFIG = SystemConfig()






FORBIDDEN_ACTION_KEYWORDS = ["drop table", "delete from", "rm -rf", "chmod 777", "grant all", "shutdown server", "ssn", "delete database"]
VALID_ACTION_KEYWORDS = ["rollback", "roll back", "shift", "isolate", "price", "hedge", "traffic", "switch", "migrate", "loyalty", "retry", "scale", "circuit breaker", "restart", "flush", "route"]
