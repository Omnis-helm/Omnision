"""
Phase 4: Dynamic Playbook Appends & Continuous Knowledge Ingestion (§3.1, §7, §13)

When an engineer executes a modified version of a recommended fix, the delta is captured as a new
Layer 1 playbook. Its trigger pattern is derived from the root cause it fixed, so the grounded
suggestion network will propose it the next time similar evidence appears.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from kpi_engine.suggester.layers_data import PrescriptiveLayersStore
from kpi_engine.ml.local_ml_engine import tokenize

GENERIC_TERMS = {"back", "integration", "applied", "across", "region", "issue", "problem", "users", "reported",
                 "rollback", "restart", "action", "service", "system"}


class DynamicPlaybookAppender:
    """Captures human modifications during live incident execution and appends them to Layer 1."""

    def __init__(self, layers_store: PrescriptiveLayersStore):
        self.store = layers_store
        self.appended_records: List[Dict[str, Any]] = []

    @staticmethod
    def derive_trigger_pattern(*texts: str, max_terms: int = 8) -> str:
        seen, terms = set(), []
        for t in texts:
            for tok in tokenize(t or ""):
                if (len(tok) > 3 and not any(ch.isdigit() for ch in tok) and tok not in seen
                        and tok not in GENERIC_TERMS):
                    seen.add(tok)
                    terms.append(tok)
        return " ".join(terms[:max_terms])

    def capture_execution_delta(
        self,
        base_action_id: str,
        original_action: str,
        modified_action: str,
        modified_command: str,
        engineer_id: str = "engineer_oncall_1",
        target_environment: str = "prod-west",
        root_cause_text: Optional[str] = None,
        required_lever: Optional[str] = None,
        cost_usd: float = 0.0,
        time_minutes: int = 20,
    ) -> Dict[str, Any]:
        new_id = f"PM-{datetime.now().strftime('%Y%m%d')}-{len(self.appended_records) + 101}"
        trigger_pattern = self.derive_trigger_pattern(root_cause_text) if root_cause_text else \
            self.derive_trigger_pattern(original_action)

        # Inherit the lever of the playbook it was derived from when not specified
        if required_lever is None:
            base = base_action_id.replace("ACT-", "")
            parent = next((p for p in self.store.layer_1_playbooks + self.store.layer_3_lever_actions
                           + self.store.layer_2_market_precedents if p.get("id") == base), None)
            required_lever = parent.get("required_lever") if parent else None

        entry = {
            "id": new_id,
            "trigger_pattern": trigger_pattern,
            "action": modified_action,
            "command": modified_command,
            "target_environment": target_environment,
            "cost_usd": float(cost_usd),
            "time_minutes": int(time_minutes),
            "raci": f"Engineer ({engineer_id})",
            "required_lever": required_lever,
            "metadata": {
                "source": "Dynamic_Human_Execution_Delta",
                "derived_from": base_action_id,
                "original_action": original_action,
                "ingested_at": datetime.now().isoformat(),
            },
        }
        self.store.append_dynamic_playbook(entry)
        self.appended_records.append(entry)
        return entry
