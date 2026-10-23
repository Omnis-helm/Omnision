import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field


def _load_env_file():
    """Simple parser to load .env variables into os.environ if present (never overrides real env vars)."""
    env_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v


_load_env_file()


def _env_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class SystemConfig(BaseModel):
    # ---------------- Detection & Cold-Start (§2.2, §5.5) ----------------
    mature_history_days: int = 30
    z_score_alert_threshold: float = 3.0
    z_score_shock_threshold: float = 5.0
    cold_start_static_tripwire: float = 0.05  # 5% flat deviation
    cold_start_ewma_alpha: float = 0.3
    graduation_threshold_samples: int = 30

    # Dual-window systemic drift ("boiling frog") detector
    fast_ewma_days: int = 7
    slow_ewma_days: int = 28
    systemic_drift_threshold_pct: float = 5.0

    # ---------------- Bounded Graph Construction (§2.4, §4) ----------------
    cage_pre_hours: int = 48
    cage_pre_hours_drift: int = 720  # 30 days for systemic drift
    cage_post_hours: int = 12
    max_traversal_hops: int = 2
    edge_prune_weight_threshold: float = 0.40  # calibrated: keeps secondary Gold-tier drivers (~25%+ share), drops weak/ambient noise
    hop_attenuation: float = 0.85  # path weight decay per extra hop

    # Just-in-time Graph-RAG (historical precedent retrieval)
    history_top_k: int = 3
    history_min_similarity: float = 0.30      # below this a precedent is ignored
    noise_suppression_similarity: float = 0.55  # a local noise signature this similar can suppress an alert
    history_precedent_wcf_local: float = 0.55
    history_precedent_wcf_cross_region: float = 0.35

    # ---------------- Causal Weighting (§2.5, §5) ----------------
    alpha_wt: float = 0.35  # Temporal Proximity
    beta_we: float = 0.35   # Entity Overlap
    gamma_ws: float = 0.30  # Semantic Similarity
    semantic_threshold_initial: float = 0.20  # Ws below this is treated as 0 (gatekeeper), recalibrated by humans

    # Causal Impact weights: CI = delta*Wsnr + epsilon*Wcf
    delta_wsnr: float = 0.40  # Signal-to-Noise Ratio
    epsilon_wcf: float = 0.60  # Counterfactual Impact
    demotion_penalty: float = 0.5  # multiplier applied to W of nodes a human demoted for this KPI

    # ---------------- Governance & RACI Authority (§4.2, §10, §11) ----------------
    auto_approve_cost_ceiling_usd: float = 10000.0
    vp_approval_required_cost_usd: float = 100000.0
    max_time_to_impact_minutes: int = 1440
    supervisor_alignment_threshold: float = 0.15
    max_recommended_actions: int = 3

    # ---------------- Continuous Learning (§4.1.2, §13) ----------------
    model_penalty_decay_rate: float = 0.15
    model_reward_boost_rate: float = 0.10
    semantic_recalibration_step: float = 0.05

    # ---------------- Telemetry & LLM Economics (§4.3.1, §12.3) ----------------
    token_budget_limit: int = 4000
    tokens_per_evidence_node: int = 150
    cost_per_1k_input_tokens_usd: float = 0.0025
    cost_per_1k_output_tokens_usd: float = 0.0100

    # ---------------- Performance & Local Optimization ----------------
    prefer_local_tools: bool = Field(default_factory=lambda: _env_bool("PREFER_LOCAL_TOOLS", "True"))
    enable_llm_cache: bool = Field(default_factory=lambda: _env_bool("ENABLE_LLM_CACHE", "True"))
    enable_local_ml_models: bool = Field(default_factory=lambda: _env_bool("ENABLE_LOCAL_ML_MODELS", "True"))
    enable_dense_embeddings: bool = Field(default_factory=lambda: _env_bool("ENABLE_DENSE_EMBEDDINGS", "False"))

    # ---------------- LLM providers ----------------
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    google_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    huggingface_api_key: str = Field(default_factory=lambda: os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_API_KEY", "")))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    anthropic_model: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))
    llm_timeout_seconds: int = 30
    swarm_max_iterations: int = 3


# Global configuration instance
CONFIG = SystemConfig()

# Providers that send data to a third-party cloud (RBAC + Tier-2 masking apply)
PUBLIC_LLM_PROVIDERS: List[str] = ["openai", "anthropic", "claude", "gemini", "google"]
PRIVATE_LLM_PROVIDERS: List[str] = ["ollama", "mock", "local"]

FORBIDDEN_ACTION_KEYWORDS = [
    "drop table", "delete from", "rm -rf", "chmod 777", "grant all", "shutdown server",
    "ssn", "delete database", "truncate table", "disable firewall", "export customer pii",
]

# Stems of verbs that describe a concrete operational lever (used as one signal of the Critic's correctness test)
VALID_ACTION_KEYWORDS = [
    "rollback", "roll back", "revert", "shift", "isolate", "price", "hedge", "traffic", "switch",
    "migrate", "loyalty", "retry", "scal", "circuit breaker", "restart", "flush", "route", "re-route",
    "failover", "fail over", "disable", "feature flag", "hotfix", "patch", "renegotiat", "reclassif",
    "accru", "reserve", "dual-source", "promotion", "promo", "bundle", "discount", "throttle",
    "suppress", "triage", "escalat", "recover", "invoke",
]
