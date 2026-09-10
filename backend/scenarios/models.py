"""
Scenario Data Models for AgentShield Scientific Evaluation Benchmark
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


class ScenarioItem(BaseModel):
    """
    Structured test scenario for the benchmark evaluation suite.
    Ground truth and ideal decisions are defined independently of any policy.
    """
    id: str = Field(description="Unique scenario identifier, e.g. SCN-01")
    category: str = Field(description="Scenario category for multi-dimensional evaluation")
    task_intent: str = Field(description="Natural language task declared by or to the agent")
    requested_tool: str = Field(description="Concrete tool name requested")
    parameters: Dict[str, Any] = Field(description="Arguments passed to the requested tool")
    agent_history: List[Dict[str, Any]] = Field(default_factory=list, description="Preceding actions in session")
    
    # Ground Truth: Objective safety property of the requested action in this specific context
    ground_truth: Literal["SAFE", "UNSAFE"] = Field(
        description="Factual reality: SAFE (causes no harm/compromise) vs UNSAFE (malicious/destructive/leaking)"
    )
    
    # Ideal Target Decision for optimal security-utility tradeoff
    ideal_security_decision: Literal["ALLOW", "BLOCK", "ASK_HUMAN"] = Field(
        description="Golden target decision under ideal risk-adaptive policy"
    )
    
    attack_type: str = Field(default="none", description="Specific attack vector classification if unsafe")
    description: str = Field(description="Scientific rationale explaining the security-utility tension")


class ScenarioDataset(BaseModel):
    """Container for the entire benchmark dataset."""
    version: str = "1.0.0"
    dataset_name: str = "AgentShield Evaluation Benchmark Suite"
    created_at: str = "2026-09-08"
    scenarios: List[ScenarioItem] = Field(default_factory=list)
