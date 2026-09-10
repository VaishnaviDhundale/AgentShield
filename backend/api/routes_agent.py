"""
Agent Execution and Session REST Endpoints for AgentShield
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.agent.base_agent import AgentShieldAgent, AgentRunResult
from backend.agent.llm_provider import get_llm_provider
from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.database.models import SessionRecord, RequestRecord, DecisionRecord
from backend.database.db import get_engine

router = APIRouter(prefix="/api/agent", tags=["Agent"])


class AgentRunPayload(BaseModel):
    task_intent: str
    policy_name: str = "AgentShield"
    max_steps: int = 6
    provider_type: str = "mock"
    api_key: Optional[str] = None
    model_name: Optional[str] = None


@router.post("/run")
async def run_agent_task(payload: AgentRunPayload):
    """
    Executes an autonomous agent task session.
    All tool calls are intercepted in real-time by the AgentShield Gateway.
    """
    # 1. Configure target policy on Gateway
    target_policy = service.get_policy(payload.policy_name)
    service.gateway.set_policy(target_policy)

    # 2. Configure LLM provider
    provider = get_llm_provider(
        payload.provider_type,
        api_key=payload.api_key,
        model=payload.model_name or "mock-deterministic"
    )

    # 3. Initialize Agent with the Gateway (Invariant: no direct sandbox access)
    agent = AgentShieldAgent(llm_provider=provider, tool_gateway=service.gateway)

    # 4. Broadcast start event
    await ws_manager.broadcast({
        "event_type": "AGENT_RUN_STARTED",
        "task_intent": payload.task_intent,
        "policy_name": payload.policy_name
    })

    # 5. Run agent loop
    result: AgentRunResult = await agent.run(
        task_intent=payload.task_intent,
        max_steps=payload.max_steps
    )

    # 6. Update Session record status in database
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        session_rec = db_session.get(SessionRecord, result.session_id)
        if session_rec:
            session_rec.status = "completed" if result.completed else "stopped"
            db_session.add(session_rec)
            db_session.commit()

    # 7. Broadcast completion event
    await ws_manager.broadcast({
        "event_type": "AGENT_RUN_COMPLETED",
        "session_id": result.session_id,
        "task_intent": result.task_intent,
        "completed": result.completed,
        "total_calls": result.total_tool_calls,
        "blocked_calls": result.blocked_tool_calls,
        "final_answer": result.final_answer
    })

    return {
        "session_id": result.session_id,
        "task_intent": result.task_intent,
        "completed": result.completed,
        "total_tool_calls": result.total_tool_calls,
        "blocked_tool_calls": result.blocked_tool_calls,
        "duration_sec": round(result.duration_sec, 3),
        "final_answer": result.final_answer,
        "steps": [
            {
                "step_number": s.step_number,
                "thought": s.thought,
                "tool_request": {
                    "tool_name": s.tool_request.tool_name,
                    "parameters": s.tool_request.parameters
                } if s.tool_request else None,
                "tool_response": {
                    "decision": s.tool_response.decision,
                    "success": s.tool_response.success,
                    "output": s.tool_response.output,
                    "error": s.tool_response.error,
                    "risk_score": s.tool_response.risk_score,
                    "reason": s.tool_response.reason,
                    "signals": s.tool_response.signals
                } if s.tool_response else None
            }
            for s in result.steps
        ]
    }


@router.get("/sessions")
def list_sessions(limit: int = Query(default=20, le=100)):
    """Retrieves past agent execution sessions from SQLite database."""
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        sessions = db_session.exec(
            select(SessionRecord).order_by(SessionRecord.created_at.desc()).limit(limit)
        ).all()
        return sessions


@router.get("/sessions/{session_id}")
def get_session_details(session_id: str):
    """Retrieves full request and decision logs for a specific session."""
    engine = get_engine(service.db_url)
    with Session(engine) as db_session:
        session_rec = db_session.get(SessionRecord, session_id)
        if not session_rec:
            raise HTTPException(status_code=404, detail="Session not found")

        requests = db_session.exec(
            select(RequestRecord).where(RequestRecord.session_id == session_id).order_by(RequestRecord.step_number)
        ).all()

        decisions = db_session.exec(
            select(DecisionRecord).where(DecisionRecord.session_id == session_id).order_by(DecisionRecord.created_at)
        ).all()

        return {
            "session": session_rec,
            "requests": requests,
            "decisions": decisions
        }
