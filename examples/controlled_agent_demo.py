"""Run a real, local README summary through the controlled tool loop."""

import asyncio
import argparse
import json
from pathlib import Path

from src.composition import create_controlled_agent
from src.core.decision import DecisionEngine
from src.jev.client import JEVClient
from src.jev.mock import MockJEVClient


async def main(use_real_jev: bool = False, approve_existing: bool = False) -> None:
    root = Path(__file__).resolve().parents[1]
    runner = create_controlled_agent(
        DecisionEngine(JEVClient.from_env() if use_real_jev else MockJEVClient()), root
    )
    trace = await runner.run(
        "Read README.md, create a short summary, and save it to output/summary.md."
    )
    if trace.status == "approval_required" and approve_existing and trace.pending_action:
        trace = await runner.approve_action(trace.pending_action.action_id, run_id=trace.run_id)
    summary = {
        "run_id": trace.run_id,
        "status": trace.status,
        "steps": [
            {
                "step": step.step,
                "action_id": step.proposal.action_id if step.proposal else None,
                "tool": step.proposal.tool if step.proposal else None,
                "policy": step.policy_result.status.value if step.policy_result else None,
                "decision": step.decision.outcome.value if step.decision else None,
                "confidence": step.decision.confidence if step.decision else None,
                "decision_source": step.decision.source if step.decision else None,
                "permit": step.permit.approval_source if step.permit else None,
                "execution": step.execution_status,
                "result_chars": len(step.tool_result.output) if step.tool_result else None,
            }
            for step in trace.steps
        ],
        "final_output": trace.final_output,
        "stop_reason": trace.stop_reason,
        "pending_action": trace.pending_action.model_dump(mode="json") if trace.pending_action else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if trace.status != "completed":
        raise SystemExit(f"Controlled demo ended with status: {trace.status}")
    print(f"\nCreated: {root / 'output' / 'summary.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-jev",
        action="store_true",
        help="use the configured JEV_API_KEY; without this flag the demo stays offline",
    )
    parser.add_argument(
        "--approve-existing",
        action="store_true",
        help="explicitly approve overwriting output/summary.md if it already exists",
    )
    args = parser.parse_args()
    asyncio.run(main(use_real_jev=args.real_jev, approve_existing=args.approve_existing))
