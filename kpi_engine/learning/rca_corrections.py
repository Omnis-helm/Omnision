"""
Phase 1 & Phase 2: Human-in-the-Loop RCA Override & Semantic Recalibration (§2.5.4, §13)
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
        demoted_driver: CandidateNode,
        promoted_driver: Optional[CandidateNode] = None,
        injected_custom_text: Optional[str] = None,
        analyst_id: str = "analyst_senior_1",
    ) -> Tuple[CandidateNode, Dict[str, Any]]:
        """Applies manual RCA override and recalibrates semantic similarity thresholds."""
        if promoted_driver is None and injected_custom_text:
            # Create injected custom node
            promoted_driver = CandidateNode(
                node_id=f"NODE-INJECTED-{int(datetime.now().timestamp())}",
                node_type=CandidateNodeType.OPERATIONAL_LOG,
                title="Analyst Injected Root Cause",
                content=injected_custom_text,
                timestamp=datetime.now(),
                dimensions={"source": "Human_Expert_Override"},
                security_tier=SecurityTier.PUBLIC_UNRESTRICTED,
                clearance_required=UserClearance.PUBLIC,
                raw_metric_values={"drop_contrib": 0.90},
                metadata={"override_by": analyst_id},
            )

        assert promoted_driver is not None, "Promoted driver or injected text must be provided."

        # Semantic Recalibration: Adjust threshold to favor promoted driver keywords
        old_threshold = self.cr_scorer.semantic_threshold
        self.cr_scorer.semantic_threshold = max(0.05, old_threshold - self.config.semantic_recalibration_step)

        record = {
            "timestamp": datetime.now().isoformat(),
            "anchor_kpi_id": anchor_kpi_id,
            "analyst_id": analyst_id,
            "demoted_node_id": demoted_driver.node_id,
            "demoted_title": demoted_driver.title,
            "promoted_node_id": promoted_driver.node_id,
            "promoted_title": promoted_driver.title,
            "previous_semantic_threshold": round(old_threshold, 3),
            "new_semantic_threshold": round(self.cr_scorer.semantic_threshold, 3),
        }
        self.override_history.append(record)
        return promoted_driver, record
