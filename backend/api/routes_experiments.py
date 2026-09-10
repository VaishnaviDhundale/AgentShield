"""
Benchmark Scenarios and Experiment Runner REST Endpoints for AgentShield
"""

import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.scenarios.scenario_loader import ScenarioLoader
from backend.evaluation.experiment_runner import ExperimentRunner, EXPERIMENTS_DIR
from backend.api.service import service
from backend.api.websocket_manager import ws_manager

router = APIRouter(prefix="/api/experiments", tags=["Experiments & Evaluation"])


class RunBenchmarkPayload(BaseModel):
    policies: List[str] = [
        "NoSecurityPolicy",
        "StaticPermissionPolicy",
        "LLMJudgePolicy",
        "AgentShieldPolicy"
    ]
    trials: int = 1
    hitl_mode: str = "ideal"


@router.get("/scenarios")
def list_scenarios(category: Optional[str] = None):
    """Returns the structured benchmark scenario catalog with ground truth annotations."""
    return ScenarioLoader.get_scenarios(category=category)


@router.post("/run")
async def run_benchmark_experiment(payload: RunBenchmarkPayload):
    """
    Executes an automated benchmark evaluation suite across selected policies.
    Derived strictly from real scenario executions.
    """
    runner = ExperimentRunner(
        sandbox_environment=service.env,
        db_url=service.db_url,
        hitl_mode=payload.hitl_mode
    )

    # Instantiate selected policies
    policy_instances = [service.get_policy(p) for p in payload.policies]

    await ws_manager.broadcast({
        "event_type": "BENCHMARK_STARTED",
        "policies": payload.policies,
        "trials": payload.trials
    })

    suite_results = await runner.run_comparative_suite(
        policies=policy_instances,
        trials=payload.trials,
        export_results=True
    )

    await ws_manager.broadcast({
        "event_type": "BENCHMARK_COMPLETED",
        "policies": suite_results["policies"]
    })

    return suite_results


@router.get("/latest")
def get_latest_benchmark_results():
    """Reads and returns the most recently exported JSON benchmark results."""
    json_files = sorted(EXPERIMENTS_DIR.glob("benchmark_results_*.json"), key=lambda p: p.stat().st_mtime)
    if not json_files:
        raise HTTPException(status_code=404, detail="No benchmark results found. Run an experiment first.")

    latest_file = json_files[-1]
    return json.loads(latest_file.read_text(encoding="utf-8"))


@router.get("/history")
def list_benchmark_history():
    """Lists all saved experiment runs."""
    json_files = sorted(EXPERIMENTS_DIR.glob("benchmark_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "filename": f.name,
            "created_at": f.stat().st_mtime,
            "size_bytes": f.stat().st_size
        }
        for f in json_files
    ]
