"""
Phase 3: Telemetry-Driven Trust Weight Tuning (§4.1.2, §13)

Human ACCEPT / REJECT / MODIFY signals on a recommended action adjust the confidence weight (Wm) of
the agent that produced it. The weights are read live by the suggestion network, so the next
investigation ranks that agent's proposals higher or lower.
"""

import random
from datetime import datetime
from typing import Dict, List, Any

from kpi_engine.governor.actor_swarm import ActorSwarm
from kpi_engine.suggester.dual_channel import agent_for_layer
from kpi_engine.config import CONFIG


class ModelTrustTuner:
    """Dynamically adjusts Model Confidence Weights (Wm) based on user Accept/Reject/Modify signals."""

    WEIGHT_FLOOR = 0.05

    def __init__(self, swarm: ActorSwarm, config=CONFIG, rng: random.Random = None):
        self.swarm = swarm
        self.config = config
        self.rng = rng or random.Random()
        self.feedback_log: List[Dict[str, Any]] = []

    def record_feedback(self, action_id: str, source_layer: str, signal: str, user_id: str = "user_ops") -> Dict[str, Any]:
        agent_key = agent_for_layer(source_layer)
        old_weight = self.swarm.model_weights.get(agent_key, 0.80)
        signal = signal.upper()

        if signal == "REJECT":
            # Epsilon-greedy exploration: 5% of the time shield the challenger from decay so the
            # system does not collapse into a risk-averse echo chamber.
            if agent_key == "challenger_agent" and self.rng.random() < 0.05:
                new_weight, signal = old_weight, "REJECT_SHIELDED"
            else:
                new_weight = old_weight * (1.0 - self.config.model_penalty_decay_rate)  # W(t+1) = W(t)(1 - eta)
        elif signal == "ACCEPT":
            new_weight = min(1.0, old_weight * (1.0 + self.config.model_reward_boost_rate))
        else:  # MODIFY
            new_weight = min(1.0, old_weight * 1.02)

        new_weight = round(max(self.WEIGHT_FLOOR, float(new_weight)), 4)
        self.swarm.model_weights[agent_key] = new_weight

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action_id,
            "source_layer": source_layer,
            "agent_key": agent_key,
            "signal": signal,
            "old_weight": old_weight,
            "new_weight": new_weight,
            "user_id": user_id,
        }
        self.feedback_log.append(entry)
        return entry
