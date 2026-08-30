"""
Phase 3: Telemetry-Driven Trust Weight Tuning (§4.1.2, §13)
"""

from typing import Dict, List, Any
from datetime import datetime
from kpi_engine.governor.actor_swarm import ActorSwarm
from kpi_engine.config import CONFIG


class ModelTrustTuner:
    """Dynamically adjusts Model Confidence Weights (Wm) based on user Accept/Reject/Modify signals."""

    def __init__(self, swarm: ActorSwarm, config=CONFIG):
        self.swarm = swarm
        self.config = config
        self.feedback_log: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        action_id: str,
        source_layer: str,
        signal: str,  # "ACCEPT", "REJECT", "MODIFY"
        user_id: str = "user_ops",
    ) -> Dict[str, Any]:
        """Captures user signal and applies trust decay or boost formula."""
        # Identify agent type
        if "Challenger" in source_layer:
            agent_key = "challenger_agent"
        elif "Playbook" in source_layer:
            agent_key = "tech_agent"
        elif "Operational" in source_layer:
            agent_key = "ops_agent"
        else:
            agent_key = "finance_agent"

        old_weight = self.swarm.model_weights.get(agent_key, 0.80)

        if signal.upper() == "REJECT":
            # --- Simulated Epsilon-Greedy Exploration ---
            # 5% of the time, shield the Blue-Sky Challenger from weight decay 
            # to prevent the system from getting trapped in a risk-averse echo chamber.
            import random
            if agent_key == "challenger_agent" and random.random() < 0.05:
                new_weight = old_weight # Shield activated
                signal = "REJECT_SHIELDED"
            else:
                # Penalty decay function: W_m^(t+1) = W_m^(t) * (1 - eta)
                new_weight = old_weight * (1.0 - self.config.model_penalty_decay_rate)
        elif signal.upper() == "ACCEPT":
            # Reward boost function
            new_weight = min(1.0, old_weight * (1.0 + self.config.model_reward_boost_rate))
        else:  # MODIFY
            # Neutral / minor boost for refinement
            new_weight = min(1.0, old_weight * 1.02)

        new_weight = round(float(new_weight), 4)
        self.swarm.model_weights[agent_key] = new_weight

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action_id,
            "source_layer": source_layer,
            "agent_key": agent_key,
            "signal": signal.upper(),
            "old_weight": old_weight,
            "new_weight": new_weight,
            "user_id": user_id,
        }
        self.feedback_log.append(log_entry)
        return log_entry
