"""
Phase 1 & Phase 2: Human-in-the-Loop RCA Override & Semantic Recalibration (§2.5.4, §13)

An analyst demotes the engine's primary driver and either promotes another evidence node or injects a
root cause in free text. The engine then:
  * lowers the semantic gatekeeper threshold by eta (semantic_recalibration_step), letting
    semantically distant but real evidence through on future runs
  * remembers the demotion so the demoted node's W is penalised for this KPI
  * stores the human-verified driver so subsequent runs (and the regenerated payload) use it
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from kpi_engine.data.models import CandidateNode, CandidateNodeType, SecurityTier, UserClearance
from kpi_engine.causal.contextual_relevance import ContextualRelevanceScorer
from kpi_engine.config import CONFIG


class RCACorrectionManager:
    """Manages human analyst overrides and triggers semantic threshold recalibration."""

    def __init__(self, cr_scorer: ContextualRelevanceScorer, config=CONFIG):
        self.cr_scorer = cr_scorer
        self.config = config
        self.override_history: List[Dict[str, Any]] = []

    def perform_rca_override(
        self,
        anchor_kpi_id: str,
        demoted_driver: Optional[CandidateNode],
        promoted_driver: Optional[CandidateNode] = None,
        injected_custom_text: Optional[str] = None,
        analyst_id: str = "analyst_senior_1",
        anchor_timestamp: Optional[datetime] = None,
        anchor_dimensions: Optional[Dict[str, str]] = None,
    ) -> Tuple[CandidateNode, Dict[str, Any]]:
        if promoted_driver is None:
            if not injected_custom_text:
                raise ValueError("Promoted driver or injected text must be provided.")
            promoted_driver = CandidateNode(
                node_id=f"NODE-INJECTED-{int(datetime.now().timestamp())}",
                node_type=CandidateNodeType.OPERATIONAL_LOG,
                title="Analyst-Verified Root Cause",
                content=injected_custom_text,
                timestamp=anchor_timestamp or datetime.now(),
                dimensions={k: v for k, v in (anchor_dimensions or {}).items() if k != "domain"},
                security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
                clearance_required=UserClearance.PUBLIC,
                raw_metric_values={"drop_contrib": 0.90},
                metadata={"override_by": analyst_id, "source": "Human_Expert_Override", "human_verified": True},
            )
        else:
            promoted_driver = promoted_driver.model_copy(deep=True)
            promoted_driver.metadata = {**promoted_driver.metadata, "human_verified": True, "override_by": analyst_id}
            promoted_driver.metadata.pop("causes", None)  # promoted to a direct driver

        old_threshold = self.cr_scorer.semantic_threshold
        self.cr_scorer.semantic_threshold = max(0.05, round(old_threshold - self.config.semantic_recalibration_step, 4))

        record = {
            "timestamp": datetime.now().isoformat(),
            "anchor_kpi_id": anchor_kpi_id,
            "analyst_id": analyst_id,
            "demoted_node_id": demoted_driver.node_id if demoted_driver else None,
            "demoted_title": demoted_driver.title if demoted_driver else None,
            "promoted_node_id": promoted_driver.node_id,
            "promoted_title": promoted_driver.title,
            "previous_semantic_threshold": round(old_threshold, 3),
            "new_semantic_threshold": round(self.cr_scorer.semantic_threshold, 3),
        }
        self.override_history.append(record)
        return promoted_driver, record
