"""
Configuration and Weight Parameters for AgentShield Mathematical Risk Scoring Engine
"""

from pydantic import BaseModel, Field
from typing import Dict


class RiskScoringConfig(BaseModel):
    """
    Configurable weights and thresholds for the risk scoring formula.
    
    Formula:
    RiskScore = min(100, max(0,
        w_res * S_res +
        w_tool * R_tool +
        w_intent * M_intent +
        w_anom * A_hist +
        sum(Soft_Rule_Adjustments)
    ))
    """
    # Normalized weights
    w_resource_sensitivity: float = Field(default=0.35, ge=0.0, le=1.0)
    w_tool_risk: float = Field(default=0.20, ge=0.0, le=1.0)
    w_intent_mismatch: float = Field(default=0.35, ge=0.0, le=1.0)
    w_anomaly: float = Field(default=0.10, ge=0.0, le=1.0)

    # Decision thresholds (0 to 100)
    allow_threshold: int = Field(default=40, ge=0, le=100)
    block_threshold: int = Field(default=70, ge=0, le=100)

    # Base Resource Sensitivity values (0 to 100)
    sensitivity_scores: Dict[str, int] = Field(default_factory=lambda: {
        "LOW": 10,
        "MEDIUM": 40,
        "HIGH": 70,
        "CRITICAL": 95
    })

    # Base Tool Action Risk values (0 to 100)
    tool_risk_scores: Dict[str, int] = Field(default_factory=lambda: {
        "list_files": 10,
        "read_file": 20,
        "git_operation": 30,
        "run_tests": 35,
        "write_file": 50,
        "database_query": 65,
        "http_request": 70,
        "run_command": 80,
        "delete_file": 85
    })
