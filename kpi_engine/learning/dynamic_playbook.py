"""
Phase 4: Dynamic Playbook Appends & Continuous Knowledge Ingestion (§3.1, §7, §13)
"""

from typing import Dict, Any, List
from datetime import datetime
from kpi_engine.suggester.layers_data import PrescriptiveLayersStore


class DynamicPlaybookAppender:
    """Captures human modifications during live incident execution and appends to Layer 1 Playbooks."""

    def __init__(self, layers_store: PrescriptiveLayersStore):
        self.store = layers_store
        self.appended_records: List[Dict[str, Any]] = []

    def capture_execution_delta(
        self,
        base_action_id: str,
        original_action: str,
        modified_action: str,
        modified_command: str,
        engineer_id: str = "engineer_oncall_1",
        target_environment: str = "prod-west",
    ) -> Dict[str, Any]:
        """Compiles human modification delta into a structured post-mortem and ingests into Layer 1."""
        new_id = f"PM-{datetime.now().strftime('%Y%m%d')}-{len(self.appended_records) + 101}"

        # Extract trigger pattern from original action
        trigger_pattern = " ".join([w.lower() for w in original_action.split() if len(w) > 3])

        new_playbook_entry = {
            "id": new_id,
            "trigger_pattern": trigger_pattern,
            "action": modified_action,
            "command": modified_command,
            "target_environment": target_environment,
            "cost_usd": 0.0,
            "time_minutes": 20,
            "raci": f"Engineer ({engineer_id})",
            "required_lever": "helm_rollback_capability",
            "metadata": {
                "source": "Dynamic_Human_Execution_Delta",
                "derived_from": base_action_id,
                "original_action": original_action,
                "ingested_at": datetime.now().isoformat(),
            },
        }

        # Programmatically ingest into Layer 1 (Internal Prescriptive Data)
        self.store.append_dynamic_playbook(new_playbook_entry)
        self.appended_records.append(new_playbook_entry)

        return new_playbook_entry
