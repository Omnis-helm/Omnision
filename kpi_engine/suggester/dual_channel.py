"""
Dual-Channel Solution Suggestion Network: Grounded vs Blue-Sky Paths (§3.2, §8)

Channel A (Grounded)  : match the surviving causal drivers against Layer 1 playbooks, Layer 3
                        lever-backed actions and Layer 2 market precedents.
Channel B (Challenger): one unconstrained, driver-aware idea for sandbox evaluation.

Every candidate carries the agent that produced it so human ACCEPT/REJECT feedback (trust tuning)
changes its confidence weight on the next run.
"""

import hashlib
from typing import List, Dict, Any, Optional, Iterable

from kpi_engine.suggester.layers_data import SolutionCandidate, PrescriptiveLayersStore
from kpi_engine.ml.local_ml_engine import tokenize
from kpi_engine.data.models import UserClearance
from kpi_engine.scoper.security_matrix import clearance_level


def agent_for_layer(source_layer: str) -> str:
    s = (source_layer or "").lower()
    if "challenger" in s or "blue-sky" in s or "layer 5" in s:
        return "challenger_agent"
    if "playbook" in s or "layer 1" in s:
        return "tech_agent"
    if "lever" in s or "layer 3" in s:
        return "ops_agent"
    if "llm" in s:
        return "llm_swarm_agent"
    return "finance_agent"


def _text(d) -> str:
    if isinstance(d, dict):
        return f"{d.get('title', '')} {d.get('content', '')}"
    return f"{getattr(d, 'title', '')} {getattr(d, 'content', '')}"


def _id(d) -> Optional[str]:
    return d.get("node_id") if isinstance(d, dict) else getattr(d, "node_id", None)


class DualChannelSuggester:
    """Generates candidate solutions via parallel Grounded (Channel A) and Challenger (Channel B) paths."""

    LAYER_LABELS = {
        "l1": "Layer 1 - Internal Playbook",
        "l2": "Layer 2 - External Market Precedents",
        "l3": "Layer 3 - Operational Levers",
    }

    def __init__(self, layers_store: PrescriptiveLayersStore, trust_weights: Optional[Dict[str, float]] = None):
        self.store = layers_store
        self.trust_weights = trust_weights if trust_weights is not None else {}

    @staticmethod
    def match_score(trigger_pattern: str, text: str) -> float:
        trig = set(tokenize(trigger_pattern))
        if not trig:
            return 0.0
        hits = len(trig & set(tokenize(text)))
        ratio = hits / len(trig)
        if (hits >= 2 and ratio >= 0.3) or (hits == 1 and len(trig) <= 2):
            return ratio
        return 0.0

    def _confidence(self, agent: str, match: float, driver_rank_weight: float) -> float:
        trust = self.trust_weights.get(agent, 0.80)
        return round(trust * (0.75 + 0.25 * min(1.0, match)) * driver_rank_weight, 4)

    def _clearance_ok(self, entry: Dict[str, Any], user_role: UserClearance) -> bool:
        need = entry.get("min_clearance")
        if not need:
            return True
        try:
            return clearance_level(user_role) >= clearance_level(UserClearance(need))
        except ValueError:
            return False

    def run_channel_a_grounded(
        self,
        anchor,
        drivers: Iterable[Any],
        user_role: UserClearance = UserClearance.EXECUTIVE_VP,
    ) -> List[SolutionCandidate]:
        """Grounded candidates for the ranked drivers (primary first)."""
        drivers = list(drivers)
        best: Dict[str, SolutionCandidate] = {}
        sources = (
            [("l1", e) for e in self.store.layer_1_playbooks]
            + [("l3", e) for e in self.store.layer_3_lever_actions]
            + [("l2", e) for e in self.store.layer_2_market_precedents]
        )
        for rank, drv in enumerate(drivers):
            rank_w = 1.0 if rank == 0 else 0.85
            text = _text(drv)
            for layer, entry in sources:
                m = self.match_score(entry["trigger_pattern"], text)
                if m <= 0 or not self._clearance_ok(entry, user_role):
                    continue
                label = self.LAYER_LABELS[layer]
                if layer == "l1":
                    label = f"{label} ({entry['id']})"
                elif layer == "l2":
                    label = f"{label} ({entry.get('source', entry['id'])})"
                agent = agent_for_layer(label)
                conf = self._confidence(agent, m, rank_w)
                cand = SolutionCandidate(
                    action_id=f"ACT-{entry['id']}",
                    action=entry["action"],
                    source_layer=label,
                    model_confidence_weight=conf,
                    estimated_cost_usd=float(entry.get("cost_usd", 0.0)),
                    time_to_impact_minutes=int(entry.get("time_minutes", 30)),
                    raci_owner=entry.get("raci", "Platform Reliability (PagerDuty: on-call)"),
                    technical_command=entry.get("command"),
                    target_environment=entry.get("target_environment"),
                    operational_lever_required=entry.get("required_lever"),
                    addresses_node_id=_id(drv),
                    match_score=round(m, 4),
                    agent_key=agent,
                    min_clearance=entry.get("min_clearance"),
                )
                prev = best.get(cand.action_id)
                if prev is None or cand.model_confidence_weight > prev.model_confidence_weight:
                    best[cand.action_id] = cand
        return sorted(best.values(), key=lambda c: c.model_confidence_weight, reverse=True)

    CHALLENGER_TEMPLATES = [
        ("payment gateway stripe latency timeout",
         "Migrate checkout to an alternate cloud provider with multi-PSP payment orchestration", 125000.0, 1440,
         "CTO / VP Engineering", "aws_direct_contract", "terraform apply -target=module.checkout_multicloud"),
        ("price discount promotion competitor volume",
         "Replace reactive discounting with an always-on price-intelligence membership tier (free shipping + member prices)",
         180000.0, 4320, "Chief Commercial Officer", None, None),
        ("biometric auth sdk mobile",
         "Replace the in-house biometric flow with platform passkeys (WebAuthn) across iOS, Android and web", 90000.0, 10080,
         "VP Mobile", None, None),
        ("m&a acquisition advisor fee margin",
         "Renegotiate the FastPay deal so the seller absorbs advisor fees through an earn-out adjustment", 0.0, 20160,
         "Chief Financial Officer", None, None),
    ]

    def run_channel_b_challenger(self, anchor, drivers: Iterable[Any], user_role: UserClearance = UserClearance.EXECUTIVE_VP
                                 ) -> List[SolutionCandidate]:
        drivers = list(drivers)
        text = " ".join(_text(d) for d in drivers[:2]) + f" {getattr(anchor, 'metric_name', '')}"
        best = None
        for pattern, action, cost, minutes, raci, lever, cmd in self.CHALLENGER_TEMPLATES:
            m = self.match_score(pattern, text)
            if m > 0 and (best is None or m > best[0]):
                best = (m, action, cost, minutes, raci, lever, cmd)
        if best is None:
            metric = getattr(anchor, "metric_name", "the KPI")
            best = (0.0, f"Stand up a cross-functional tiger team to redesign the end-to-end process behind {metric}",
                    60000.0, 10080, "COO", None, None)
        m, action, cost, minutes, raci, lever, cmd = best
        return [SolutionCandidate(
            action_id=f"ACT-CHAL-{hashlib.md5(action.encode()).hexdigest()[:6].upper()}",
            action=action,
            source_layer="Layer 5 - Blue-Sky Challenger",
            model_confidence_weight=self._confidence("challenger_agent", m, 1.0),
            estimated_cost_usd=cost,
            time_to_impact_minutes=minutes,
            raci_owner=raci,
            approval_status="SANDBOX",
            technical_command=cmd,
            target_environment="sandbox",
            operational_lever_required=lever,
            addresses_node_id=_id(drivers[0]) if drivers else None,
            agent_key="challenger_agent",
            requires_shadow_run=True,
        )]

    def generate_all_candidates(self, anchor, primary_driver, user_role: UserClearance = UserClearance.EXECUTIVE_VP,
                                drivers: Optional[List[Any]] = None) -> List[SolutionCandidate]:
        drivers = drivers or [primary_driver]
        grounded = self.run_channel_a_grounded(anchor, drivers, user_role)
        challenger = self.run_channel_b_challenger(anchor, drivers, user_role)
        return sorted(grounded + challenger, key=lambda c: c.model_confidence_weight, reverse=True)
