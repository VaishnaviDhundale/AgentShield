"""
Request Telemetry and Live Statistics REST Endpoints for AgentShield
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select, func

from backend.api.service import service
from backend.database.models import RequestRecord, DecisionRecord, SessionRecord
from backend.database.db import get_engine

router = APIRouter(prefix="/api", tags=["Requests & Telemetry"])


@router.get("/requests")
def list_requests(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    decision_filter: Optional[str] = None
):
    """
    Returns real-time intercepted requests with their associated decisions from SQLite.
    """
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        query = select(RequestRecord, DecisionRecord).join(
            DecisionRecord, RequestRecord.id == DecisionRecord.request_id, isouter=True
        ).order_by(RequestRecord.created_at.desc()).offset(offset).limit(limit)

        results = db_session.exec(query).all()

        items = []
        for req, dec in results:
            items.append({
                "request_id": req.id,
                "session_id": req.session_id,
                "step_number": req.step_number,
                "tool_name": req.tool_name,
                "target_resource": req.target_resource,
                "task_intent": req.task_intent,
                "parameters": req.parameters,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "decision": dec.decision if dec else "UNKNOWN",
                "risk_score": dec.risk_score if dec else 0,
                "confidence": dec.confidence if dec else 0.0,
                "reason": dec.reason if dec else "",
                "signals": dec.signals if dec else [],
                "policy_name": dec.policy_name if dec else "",
                "resource_sensitivity": dec.resource_sensitivity if dec else "LOW",
                "action_risk": dec.action_risk if dec else 0,
                "latency_ms": dec.latency_ms if dec else 0.0
            })

        if decision_filter:
            items = [i for i in items if i["decision"].upper() == decision_filter.upper()]

        return {"total": len(items), "items": items}


@router.get("/requests/{request_id}")
def get_request_detail(request_id: str):
    """
    Returns granular security breakdown for an individual intercepted tool call.
    """
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        req = db_session.get(RequestRecord, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")

        dec = db_session.exec(
            select(DecisionRecord).where(DecisionRecord.request_id == request_id)
        ).first()

        return {
            "request": {
                "id": req.id,
                "session_id": req.session_id,
                "step_number": req.step_number,
                "tool_name": req.tool_name,
                "target_resource": req.target_resource,
                "task_intent": req.task_intent,
                "parameters": req.parameters,
                "agent_history": json.loads(req.agent_history_json or "[]"),
                "created_at": req.created_at.isoformat() if req.created_at else None
            },
            "decision": {
                "decision": dec.decision if dec else "UNKNOWN",
                "risk_score": dec.risk_score if dec else 0,
                "confidence": dec.confidence if dec else 0.0,
                "reason": dec.reason if dec else "",
                "signals": dec.signals if dec else [],
                "policy_name": dec.policy_name if dec else "",
                "resource_sensitivity": dec.resource_sensitivity if dec else "LOW",
                "action_risk": dec.action_risk if dec else 0,
                "latency_ms": dec.latency_ms if dec else 0.0,
                "estimated_cost_usd": dec.estimated_cost_usd if dec else 0.0
            } if dec else None
        }


@router.get("/stats/overview")
def get_overview_statistics():
    """
    Calculates live dashboard overview metrics directly from the SQLite audit database.
    Zero mock/fake numbers.
    """
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        total_requests = db_session.exec(select(func.count(RequestRecord.id))).one()
        
        allowed_count = db_session.exec(
            select(func.count(DecisionRecord.id)).where(DecisionRecord.decision == "ALLOW")
        ).one()
        
        blocked_count = db_session.exec(
            select(func.count(DecisionRecord.id)).where(DecisionRecord.decision == "BLOCK")
        ).one()
        
        human_approved_count = db_session.exec(
            select(func.count(DecisionRecord.id)).where(DecisionRecord.signals_json.contains("human_approved"))
        ).one()

        avg_latency = db_session.exec(
            select(func.avg(DecisionRecord.latency_ms))
        ).one() or 0.0

        total_sessions = db_session.exec(select(func.count(SessionRecord.id))).one()

        return {
            "system_status": "PROTECTED",
            "total_requests": total_requests,
            "allowed_requests": allowed_count,
            "blocked_requests": blocked_count,
            "human_approvals": human_approved_count,
            "total_sessions": total_sessions,
            "avg_latency_ms": round(float(avg_latency), 2),
            "active_policy": service.gateway.policy.__class__.__name__
        }
