"""
Database Models for AgentShield Telemetry, Audit Logs, and Experiment Records
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field
import json


class SessionRecord(SQLModel, table=True):
    """Represents an agent task execution session."""
    __tablename__ = "sessions"

    id: str = Field(primary_key=True, index=True)
    task_intent: str
    policy_name: str
    status: str = "running"  # running | completed | failed | blocked
    total_calls: int = 0
    allowed_calls: int = 0
    blocked_calls: int = 0
    human_approved_calls: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class RequestRecord(SQLModel, table=True):
    """Represents an intercepted tool execution request."""
    __tablename__ = "requests"

    id: str = Field(primary_key=True, index=True)
    session_id: str = Field(index=True)
    step_number: int
    tool_name: str = Field(index=True)
    target_resource: Optional[str] = None
    parameters_json: str = "{}"
    task_intent: str
    agent_history_json: str = "[]"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def parameters(self) -> Dict[str, Any]:
        try:
            return json.loads(self.parameters_json)
        except Exception:
            return {}


class DecisionRecord(SQLModel, table=True):
    """Represents the security decision produced for an intercepted request."""
    __tablename__ = "decisions"

    id: str = Field(primary_key=True, index=True)
    request_id: str = Field(index=True)
    session_id: str = Field(index=True)
    decision: str = Field(index=True)  # ALLOW | BLOCK | ASK_HUMAN
    risk_score: int
    confidence: float
    reason: str
    signals_json: str = "[]"
    policy_name: str = Field(index=True)
    resource_sensitivity: str = "LOW"
    action_risk: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    executed_success: Optional[bool] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def signals(self) -> List[str]:
        try:
            return json.loads(self.signals_json)
        except Exception:
            return []


class HumanApprovalRecord(SQLModel, table=True):
    """Records human-in-the-loop decisions."""
    __tablename__ = "human_approvals"

    id: str = Field(primary_key=True, index=True)
    request_id: str = Field(index=True)
    session_id: str = Field(index=True)
    human_decision: str  # ALLOW_ONCE | BLOCK | TIMEOUT
    reviewer_notes: Optional[str] = None
    responded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
