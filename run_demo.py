"""
CLI Entry Point & Demo Launcher for the KPI Storytelling Engine
"""

import sys
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from kpi_engine.pipeline import KPIStorytellingEngine
from kpi_engine.data.models import UserClearance

# Use safe ascii console fallback on windows
console = Console(highlight=False)


def run_cli_demo(scenario_id: str = "SCENARIO_1_STRIPE_GATEWAY_OUTAGE", role: str = "EXECUTIVE_VP"):
    console.print(Panel.fit(
        "[bold cyan]Omnision: Autonomous KPI Storytelling Engine v3.0[/bold cyan]\n"
        "[dim]Autonomous Anomaly Diagnosis | Multi-Agent Governance | Continuous Learning[/dim]",
        border_style="cyan"
    ))

    user_clearance = getattr(UserClearance, role, UserClearance.EXECUTIVE_VP)
    engine = KPIStorytellingEngine()

    with console.status(f"[bold green]Running pipeline for scenario: {scenario_id}..."):
        result = engine.run_pipeline(scenario_id=scenario_id, user_role=user_clearance)

    if result["status"] == "ABSTAINED":
        console.print(f"\n[bold yellow][!] ENGINE ABSTAINED:[/bold yellow] {result['reason']}")
        console.print(f"    User Role: {user_clearance.value} | Pruned Nodes: {result['security_audit']['pruned_nodes_count']}")
        return

    anchor = result["anchor"]
    master = result["master_payload"]

    # 1. Anchor Summary
    console.print(f"\n[bold magenta]1. ANCHOR NODE (A*):[/bold magenta] {anchor.metric_name} ({anchor.kpi_id})")
    console.print(f"   Variance: [bold red]{anchor.variance_pct:+.2f}%[/bold red] | Z-Score: [bold yellow]{anchor.z_score:.2f}[/bold yellow] | Lifecycle: {anchor.lifecycle_stage.value}")

    # 2. Causal Evidence Table
    table = Table(title="Stage 4: Causal Weighting & Bounded Graph Evidence", show_header=True, header_style="bold green")
    table.add_column("Node ID", style="dim")
    table.add_column("Title")
    table.add_column("Contextual Rel (CR)")
    table.add_column("Causal Impact (CI)")
    table.add_column("Composite W = CR x CI")
    table.add_column("Counterfactual Tier")

    for item in result["scored_nodes"]:
        node, w, cr, ci, tier, _ = item
        table.add_row(
            node.node_id,
            node.title,
            f"{cr:.3f}",
            f"{ci:.3f}",
            f"{w:.3f}",
            tier,
        )
    console.print(table)

    # 3. Governed Action Recommendations
    console.print("\n[bold blue]Stage 6: Multi-Agent Governed Action Recommendations:[/bold blue]")
    for i, action in enumerate(master.executive_view.recommended_actions, 1):
        status_color = "green" if action.approval_status == "AUTO_APPROVED" else "yellow"
        console.print(f"  [bold]{i}. {action.action}[/bold]")
        console.print(f"     Source: [dim]{action.source_layer}[/dim]")
        console.print(f"     Cost: ${action.estimated_cost_usd:,.2f} | Time: {action.time_to_impact_minutes}m | RACI: {action.raci_owner}")
        console.print(f"     Critic: {action.critic_verdict} -> [{status_color}]{action.approval_status}[/{status_color}]\n")

    # 4. Discarded Candidates
    if master.discarded_candidates:
        console.print("[bold red]Discarded Candidate Solutions (The Critic):[/bold red]")
        for d in master.discarded_candidates:
            console.print(f"  * {d.action} ({d.source_layer})")
            console.print(f"    [red]Reason:[/red] {d.critic_verdict}")

    # 5. Telemetry
    console.print(f"\n[bold cyan]Runtime Telemetry:[/bold cyan] Latency: {master.runtime_metadata.execution_latency_ms}ms | Tokens: {master.runtime_metadata.total_tokens_consumed} | Cost: ${master.runtime_metadata.estimated_cost_usd:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KPI Storytelling Engine CLI Runner")
    parser.add_argument("--scenario", default="SCENARIO_1_STRIPE_GATEWAY_OUTAGE", help="Scenario ID to run")
    parser.add_argument("--role", default="EXECUTIVE_VP", help="User Clearance Role (EXECUTIVE_VP, SENIOR_ENGINEER, JUNIOR_ANALYST)")
    args = parser.parse_args()

    run_cli_demo(args.scenario, args.role)
