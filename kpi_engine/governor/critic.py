"""
The Critic: Feasibility, Budget Limits & Cross-Examination (§4.2, §10)

Deterministic, symbolic gate applied to every candidate fix before any human sees it:
  0. Security   - forbidden / destructive commands are rejected outright
  1. Feasibility- a named lever must exist in Layer 3 and be active
  2. Correctness- the fix must address a surviving causal driver (grounded match, semantic
                  alignment, or a concrete operational lever verb with some alignment)
  3. Liveness   - the operational endpoint must respond (simulated unless enabled)
  4. Timeliness - operational fixes must act within `max_time_to_impact_minutes`
  5. Governance - RACI cost thresholds decide AUTO / DIRECTOR / VP approval
"""

import os
import random
from typing import List, Tuple, Any, Iterable, Optional, Union

from kpi_engine.suggester.layers_data import SolutionCandidate, PrescriptiveLayersStore
from kpi_engine.ml.local_ml_engine import LocalSemanticSupervisor
from kpi_engine.config import CONFIG, FORBIDDEN_ACTION_KEYWORDS, VALID_ACTION_KEYWORDS


def check_liveness_ping(lever: Optional[str], action: str) -> bool:
    """Simulated real-time ping of the operational lever (AWS API, LaunchDarkly, traffic router...).
    Enable random failures with ENABLE_LIVENESS_SIMULATION=True."""
    if os.environ.get("ENABLE_LIVENESS_SIMULATION", "False").lower() == "true":
        return random.random() > 0.10
    return True


def _driver_texts(drivers: Union[Any, Iterable[Any]]) -> List[str]:
    if drivers is None:
        return []
    if not isinstance(drivers, (list, tuple)):
        drivers = [drivers]
    out = []
    for d in drivers:
        if isinstance(d, dict):
            out.append(f"{d.get('title', '')} {d.get('content', '')}")
        elif isinstance(d, str):
            out.append(d)
        else:
            out.append(f"{getattr(d, 'title', '')} {getattr(d, 'content', '')}")
    return out


class TheCritic:
    """Independent evaluator agent that cross-examines candidate fixes against hard constraints."""

    def __init__(self, layers_store: PrescriptiveLayersStore, config=CONFIG):
        self.store = layers_store
        self.config = config

    def approval_status_for_cost(self, cost: float) -> Tuple[str, str]:
        if cost > self.config.vp_approval_required_cost_usd:
            return "PENDING_VP_APPROVAL", "PASS - High-cost strategic action, requires VP approval."
        if cost > self.config.auto_approve_cost_ceiling_usd:
            return "PENDING_DIRECTOR_APPROVAL", "PASS - Feasible, exceeds auto-approve ceiling (Director sign-off)."
        return "AUTO_APPROVED", "PASS - Correct, feasible, in budget."

    def evaluate_one(self, cand: SolutionCandidate, driver_texts: List[str], is_blue_sky: bool = False
                     ) -> Tuple[bool, str]:
        action_text = (cand.action or "").strip()
        action_lower = action_text.lower()
        cmd_lower = (cand.technical_command or "").lower()

        if not action_text:
            return False, "REJECTED: Empty action (schema violation)."
        for term in FORBIDDEN_ACTION_KEYWORDS:
            if term in action_lower or term in cmd_lower:
                return False, f"REJECTED: Security violation - '{term}' is forbidden."

        # Feasibility first: a fix that needs a lever the company does not have can never ship
        lever = cand.operational_lever_required
        if lever and not self.store.lever_is_active(lever):
            if is_blue_sky:
                return True, f"SANDBOX - No active contract or capability for '{lever}'; would need procurement first."
            return False, f"REJECTED: No active contract or technical capability with named provider ({lever})"

        alignment = LocalSemanticSupervisor.alignment_score(driver_texts, action_text) if driver_texts else 0.0
        grounded = cand.match_score > 0 and cand.addresses_node_id is not None
        has_lever_verb = any(kw in action_lower for kw in VALID_ACTION_KEYWORDS)
        correct = grounded or alignment >= self.config.supervisor_alignment_threshold or (has_lever_verb and alignment >= 0.05)
        if not correct and not is_blue_sky:
            return False, f"REJECTED: Does not neutralize the identified root cause (alignment {alignment:.2f})."

        if not check_liveness_ping(cand.operational_lever_required, action_text):
            return False, "REJECTED: Operational lever failed liveness ping (endpoint unresponsive)."

        if not is_blue_sky and cand.time_to_impact_minutes > self.config.max_time_to_impact_minutes:
            return False, (f"REJECTED: Time to impact {cand.time_to_impact_minutes} min exceeds the "
                           f"{self.config.max_time_to_impact_minutes} min operational window.")
        return True, f"alignment={alignment:.2f}"

    def evaluate_candidates(
        self,
        anchor,
        primary_driver,
        candidates: List[SolutionCandidate],
        is_blue_sky: bool = False,
    ) -> Tuple[List[SolutionCandidate], List[SolutionCandidate]]:
        """Applies the feasibility matrix. `primary_driver` may be one driver or a ranked list.
        Returns (passed_candidates, discarded_candidates)."""
        texts = _driver_texts(primary_driver)
        passed: List[SolutionCandidate] = []
        discarded: List[SolutionCandidate] = []
        for cand in candidates:
            ok, note = self.evaluate_one(cand, texts, is_blue_sky)
            if not ok:
                cand.critic_verdict = note
                cand.approval_status = "DISCARDED"
                discarded.append(cand)
                continue
            if is_blue_sky:
                cand.approval_status = "SANDBOX"
                cand.critic_verdict = note if note.startswith("SANDBOX") else "SANDBOX - Passed safety checks; requires shadow run before promotion."
            else:
                cand.approval_status, cand.critic_verdict = self.approval_status_for_cost(cand.estimated_cost_usd)
            passed.append(cand)
        return passed, discarded
