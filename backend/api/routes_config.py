"""
Policy and Risk Scoring Configuration REST Endpoints for AgentShield
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.risk.config import RiskScoringConfig

router = APIRouter(prefix="/api/config", tags=["Configuration & Policies"])


class SetPolicyPayload(BaseModel):
    policy_name: str


@router.get("/policies")
def list_available_policies():
    """
    Returns the list of supported security policies, baselines, and ablations,
    along with the currently active Gateway policy.
    """
    return {
        "active_policy": service.gateway.policy.__class__.__name__,
        "available_policies": [
            {
                "id": "AgentShieldPolicy",
                "name": "AgentShield (Full Control Layer)",
                "description": "Multi-signal runtime security control layer combining intent alignment, resource sensitivity, tool risk, and anomaly detection.",
                "type": "control_layer"
            },
            {
                "id": "NoSecurityPolicy",
                "name": "No Security Baseline",
                "description": "Permits all tool requests unconditionally with 0 risk score.",
                "type": "baseline"
            },
            {
                "id": "StaticPermissionPolicy",
                "name": "Static RBAC / Allowlist Baseline",
                "description": "Allows read-only tools and statically blocks command execution, writes, and database operations.",
                "type": "baseline"
            },
            {
                "id": "LLMJudgePolicy",
                "name": "LLM Judge Baseline",
                "description": "Zero-shot prompt evaluation deciding tool safety directly with an LLM prompt.",
                "type": "baseline"
            },
            {
                "id": "no_task_intent",
                "name": "Ablation: No Task Intent",
                "description": "AgentShield with task intent alignment disabled ($w_{intent}=0$).",
                "type": "ablation"
            },
            {
                "id": "no_resource_sensitivity",
                "name": "Ablation: No Resource Sensitivity",
                "description": "AgentShield with resource sensitivity disabled ($w_{res}=0$).",
                "type": "ablation"
            },
            {
                "id": "no_agent_history",
                "name": "Ablation: No Agent History",
                "description": "AgentShield with behavioral history / drift detection disabled ($w_{anom}=0$).",
                "type": "ablation"
            },
            {
                "id": "no_tool_risk",
                "name": "Ablation: No Tool Risk",
                "description": "AgentShield with tool risk weight disabled ($w_{tool}=0$).",
                "type": "ablation"
            }
        ]
    }


@router.post("/policies/set")
async def set_active_policy(payload: SetPolicyPayload):
    """
    Switches the active security policy enforced by the AgentShield Gateway.
    """
    new_policy = service.get_policy(payload.policy_name)
    service.gateway.set_policy(new_policy)

    await ws_manager.broadcast({
        "event_type": "POLICY_SWITCHED",
        "active_policy": new_policy.__class__.__name__
    })

    return {
        "status": "success",
        "active_policy": new_policy.__class__.__name__
    }


@router.get("/risk-engine")
def get_risk_engine_configuration():
    """
    Returns mathematical weights, threshold boundaries, and risk catalogs
    governing the AgentShield Risk Scoring Engine.
    """
    cfg = RiskScoringConfig()
    return {
        "formula": "Risk = (w_res * S_res + w_tool * R_tool + w_intent * M_intent + w_anom * A_hist) + Rules_adjust",
        "weights": {
            "w_resource_sensitivity": cfg.w_resource_sensitivity,
            "w_tool_risk": cfg.w_tool_risk,
            "w_intent_mismatch": cfg.w_intent_mismatch,
            "w_anomaly": cfg.w_anomaly
        },
        "thresholds": {
            "allow_threshold": cfg.allow_threshold,
            "block_threshold": cfg.block_threshold,
            "ask_human_range": f"[{cfg.allow_threshold}, {cfg.block_threshold}]"
        },
        "sensitivity_scores": cfg.sensitivity_scores,
        "tool_risk_scores": cfg.tool_risk_scores
    }
