"""
Governance loop: misaligned / unsafe proposals are rejected and never reach the executive view.
"""
import json

import kpi_engine.suggester.llm_swarm as llm_swarm
from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance

S1 = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE"


class _Msg:
    def __init__(self, content):
        self.content = content
        self.usage_metadata = {"input_tokens": 100, "output_tokens": 50}


class _GarbageLLM:
    """Simulates a cloud LLM that proposes nonsense / destructive fixes."""

    def invoke(self, prompt):
        if "Chief Supervisor" in prompt:
            return _Msg(json.dumps({"reviews": []}))  # model skips review -> deterministic check applies
        return _Msg(json.dumps({"narrative": "story", "proposals": [
            {"action": "Order pizza for the team and paint the office walls blue", "estimated_cost_usd": 50,
             "raci_owner": "HR", "operational_lever_required": "Pizza_Delivery"},
            {"action": "DROP TABLE checkout_sessions to clear the backlog", "estimated_cost_usd": 0, "raci_owner": "DBA"},
        ]}))


def test_garbage_llm_proposals_are_rejected(monkeypatch):
    monkeypatch.setattr(llm_swarm, "get_llm", lambda provider=None, temperature=0.0: _GarbageLLM())
    engine = KPIStorytellingEngine()
    result = engine.run_pipeline(S1, UserClearance.EXECUTIVE_VP, force_refresh=True, primary_llm="openai")
    master = result["master_payload"]

    actions = [a.action for a in master.executive_view.recommended_actions]
    assert not any("pizza" in a.lower() or "drop table" in a.lower() for a in actions)
    verdicts = {d.action: d.critic_verdict for d in master.discarded_candidates}
    assert any("pizza" in k.lower() and "REJECTED" in v for k, v in verdicts.items())
    assert any("drop table" in k.lower() and "Security violation" in v for k, v in verdicts.items())
    assert master.runtime_metadata.input_tokens > 0


def test_loop_escalates_to_manual_triage_when_nothing_survives():
    engine = KPIStorytellingEngine()
    for lever in engine.layers_store.layer_3_active_levers:
        engine.layers_store.layer_3_active_levers[lever] = False
    result = engine.run_pipeline(S1, force_refresh=True)
    master = result["master_payload"]
    state = result["raw_state"]

    assert state["iteration_count"] >= 2
    assert [a.action_id for a in master.executive_view.recommended_actions] == ["ACT-FALLBACK-001"]
    assert any("No active contract" in d.critic_verdict for d in master.discarded_candidates)


def test_llm_failure_falls_back_closed(monkeypatch):
    class _Down:
        def invoke(self, prompt):
            raise ConnectionError("network down")

    monkeypatch.setattr(llm_swarm, "get_llm", lambda provider=None, temperature=0.0: _Down())
    engine = KPIStorytellingEngine()
    result = engine.run_pipeline(S1, force_refresh=True, primary_llm="openai", bluesky_llm="openai")
    master = result["master_payload"]
    assert master.runtime_metadata.llm_errors                       # error is surfaced
    assert master.executive_view.recommended_actions[0].action_id == "ACT-PM-2291"  # grounded path still works
    assert all(a.approval_status != "DISCARDED" for a in master.executive_view.recommended_actions)
