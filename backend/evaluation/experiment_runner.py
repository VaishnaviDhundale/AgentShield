"""
Automated Scientific Benchmark & Experiment Runner for AgentShield

Executes scenario suites across comparison policies without bypassing the Gateway,
tracks detailed HITL review decisions, computes formal evaluation metrics, and exports raw results.
"""

import json
import csv
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.agent.base_agent import ToolCallRequest, ToolCallResponse
from backend.sandbox.environment import SandboxEnvironment
from backend.sandbox.tools import SandboxToolExecutor
from backend.gateway.interceptor import AgentShieldGateway
from backend.gateway.human_approval import HumanApprovalRegistry, ApprovalDecision
from backend.policy.base import BaseSecurityPolicy
from backend.scenarios.models import ScenarioItem
from backend.scenarios.scenario_loader import ScenarioLoader
from backend.evaluation.metrics import ScenarioExecutionRecord, EvaluationMetrics, MetricsCalculator


EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


class ExperimentRunner:
    """
    Automated benchmark harness for reproducible multi-policy security evaluations.
    """

    def __init__(
        self,
        sandbox_environment: Optional[SandboxEnvironment] = None,
        db_url: Optional[str] = None,
        hitl_mode: str = "ideal"  # ideal | reject | timeout
    ):
        self.env = sandbox_environment or SandboxEnvironment()
        self.sandbox = SandboxToolExecutor(environment=self.env)
        self.db_url = db_url
        self.hitl_mode = hitl_mode

    async def run_scenario(
        self,
        scenario: ScenarioItem,
        policy: BaseSecurityPolicy,
        trial_index: int = 1
    ) -> ScenarioExecutionRecord:
        """
        Executes an individual scenario through the Gateway and records outcome.
        """
        # Ensure clean sandbox state before each scenario execution
        self.env.reset()

        approval_registry = HumanApprovalRegistry(default_timeout_sec=0.5, db_url=self.db_url)
        gateway = AgentShieldGateway(
            policy=policy,
            sandbox_executor=self.sandbox,
            db_url=self.db_url,
            approval_registry=approval_registry
        )

        request = ToolCallRequest(
            session_id=f"exp_{scenario.id}_t{trial_index}",
            step_number=1,
            tool_name=scenario.requested_tool,
            parameters=scenario.parameters,
            task_intent=scenario.task_intent,
            agent_history=scenario.agent_history
        )

        human_approval_decision = "NONE"

        # Handle automated HITL resolution based on configured experiment mode
        async def resolve_hitl_sim():
            nonlocal human_approval_decision
            await asyncio.sleep(0.02)
            pending = approval_registry.get_pending_approvals()
            if pending:
                appr_id = pending[0]["approval_id"]
                if self.hitl_mode == "ideal":
                    # Operator follows ideal target decision
                    decision = ApprovalDecision.ALLOW_ONCE if scenario.ideal_security_decision == "ALLOW" else ApprovalDecision.BLOCK
                elif self.hitl_mode == "reject":
                    decision = ApprovalDecision.BLOCK
                else:
                    return  # let timeout occur
                human_approval_decision = decision.value
                approval_registry.resolve_approval(appr_id, decision, notes=f"Automated benchmark operator ({self.hitl_mode})")

        hitl_task = asyncio.create_task(resolve_hitl_sim())

        start_time = time.perf_counter()
        response: ToolCallResponse = await gateway.dispatch(request)
        await hitl_task
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Extract cost metadata if present
        cost_usd = response.metadata.get("estimated_cost_usd", 0.0)
        initial_decision = response.metadata.get("original_policy_decision", response.decision)

        return ScenarioExecutionRecord(
            scenario_id=scenario.id,
            category=scenario.category,
            task_intent=scenario.task_intent,
            tool_name=scenario.requested_tool,
            parameters=scenario.parameters,
            ground_truth=scenario.ground_truth,
            ideal_security_decision=scenario.ideal_security_decision,
            attack_type=scenario.attack_type,
            policy_name=policy.__class__.__name__,
            policy_initial_decision=initial_decision,
            human_approval_decision=human_approval_decision,
            final_decision=response.decision,
            action_executed=response.success,
            risk_score=response.risk_score or 0,
            confidence=response.metadata.get("confidence", 0.9),
            reason=response.reason or "",
            signals=response.signals,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            trial_index=trial_index
        )

    async def run_benchmark(
        self,
        policy: BaseSecurityPolicy,
        scenarios: Optional[List[ScenarioItem]] = None,
        trials: int = 1
    ) -> tuple[EvaluationMetrics, List[ScenarioExecutionRecord]]:
        """
        Runs the full benchmark suite for a specific security policy.
        """
        scenario_list = scenarios or ScenarioLoader.get_scenarios()
        records: List[ScenarioExecutionRecord] = []

        for trial in range(1, trials + 1):
            for scn in scenario_list:
                rec = await self.run_scenario(scn, policy, trial_index=trial)
                records.append(rec)

        metrics = MetricsCalculator.calculate(records, policy_name=policy.__class__.__name__)
        return metrics, records

    async def run_comparative_suite(
        self,
        policies: List[BaseSecurityPolicy],
        scenarios: Optional[List[ScenarioItem]] = None,
        trials: int = 1,
        export_results: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the entire scenario suite across all baseline, proposed, and ablation policies,
        computing comparative metrics and exporting raw data.
        """
        scenario_list = scenarios or ScenarioLoader.get_scenarios()
        suite_results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_scenarios": len(scenario_list),
            "trials_per_scenario": trials,
            "hitl_mode": self.hitl_mode,
            "policies": {},
            "raw_records": []
        }

        all_records: List[ScenarioExecutionRecord] = []

        for pol in policies:
            pol_name = getattr(pol, "ablation_name", None)
            display_name = f"AgentShield_{pol_name}" if pol_name else pol.__class__.__name__
            metrics, records = await self.run_benchmark(pol, scenarios=scenario_list, trials=trials)
            metrics.policy_name = display_name
            suite_results["policies"][display_name] = metrics.model_dump()
            all_records.extend(records)

        suite_results["raw_records"] = [r.model_dump() for r in all_records]

        if export_results:
            self._export_suite_files(suite_results, all_records)

        return suite_results

    def _export_suite_files(self, suite_results: Dict[str, Any], records: List[ScenarioExecutionRecord]) -> None:
        """Saves JSON raw benchmark output and CSV summary table."""
        ts = int(time.time())
        json_path = EXPERIMENTS_DIR / f"benchmark_results_{ts}.json"
        csv_path = EXPERIMENTS_DIR / f"benchmark_summary_{ts}.csv"

        # Save JSON
        json_path.write_text(json.dumps(suite_results, indent=2), encoding="utf-8")

        # Save CSV summary
        policies_data = suite_results.get("policies", {})
        if policies_data:
            fieldnames = list(next(iter(policies_data.values())).keys())
            with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for pol_dict in policies_data.values():
                    writer.writerow(pol_dict)
