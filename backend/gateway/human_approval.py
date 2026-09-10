"""
Human-In-The-Loop (HITL) Security Boundary & Approval Workflow for AgentShield

INVARIANT:
When a policy yields ASK_HUMAN:
Execution is PAUSED -> Emits approval event -> Awaits human decision ->
ALLOW executes tool / BLOCK rejects tool / TIMEOUT defaults to BLOCK.
"""

import asyncio
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlmodel import Session

from backend.database.models import HumanApprovalRecord
from backend.database.db import get_engine


class ApprovalDecision(str, Enum):
    ALLOW_ONCE = "ALLOW_ONCE"
    ALLOW_SESSION = "ALLOW_SESSION"
    BLOCK = "BLOCK"
    TIMEOUT = "TIMEOUT"


@dataclass
class PendingApproval:
    """Represents an action paused awaiting human authorization."""
    id: str
    request_id: str
    session_id: str
    task_intent: str
    tool_name: str
    target_resource: str
    parameters: Dict[str, Any]
    risk_score: int
    reason: str
    signals: List[str]
    created_at: float = field(default_factory=time.time)
    timeout_sec: float = 30.0
    status: str = "PENDING"  # PENDING | RESOLVED | TIMED_OUT
    decision: Optional[ApprovalDecision] = None
    reviewer_notes: Optional[str] = None
    _event: asyncio.Event = field(default_factory=asyncio.Event)


class HumanApprovalRegistry:
    """
    Thread-safe async registry managing human approval requests and resolution events.
    """

    def __init__(self, default_timeout_sec: float = 30.0, db_url: Optional[str] = None):
        self.default_timeout_sec = default_timeout_sec
        self.db_url = db_url
        self._pending: Dict[str, PendingApproval] = {}
        self._session_allow_all: Dict[str, Set[str]] = {}  # session_id -> allowed tool_names

    def request_approval(
        self,
        request_id: str,
        session_id: str,
        task_intent: str,
        tool_name: str,
        target_resource: str,
        parameters: Dict[str, Any],
        risk_score: int,
        reason: str,
        signals: List[str],
        timeout_sec: Optional[float] = None
    ) -> PendingApproval:
        """Creates and registers a new pending approval."""
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        pending = PendingApproval(
            id=approval_id,
            request_id=request_id,
            session_id=session_id,
            task_intent=task_intent,
            tool_name=tool_name,
            target_resource=target_resource,
            parameters=parameters,
            risk_score=risk_score,
            reason=reason,
            signals=signals,
            timeout_sec=timeout_sec or self.default_timeout_sec
        )
        self._pending[approval_id] = pending
        return pending

    async def wait_for_decision(self, approval_id: str) -> ApprovalDecision:
        """
        Pauses execution until the human submits a decision or timeout expires.
        Defaults to BLOCK on timeout.
        """
        pending = self._pending.get(approval_id)
        if not pending:
            return ApprovalDecision.BLOCK

        try:
            await asyncio.wait_for(pending._event.wait(), timeout=pending.timeout_sec)
            decision = pending.decision or ApprovalDecision.BLOCK
        except asyncio.TimeoutError:
            decision = ApprovalDecision.TIMEOUT
            pending.decision = ApprovalDecision.TIMEOUT
            pending.status = "TIMED_OUT"
            pending.reviewer_notes = f"Automatic timeout after {pending.timeout_sec}s. Defaulted to BLOCK."

        # Record human approval audit in SQLite database
        self._record_approval_db(pending)
        return decision

    def resolve_approval(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        notes: Optional[str] = None
    ) -> bool:
        """Called by UI / API when a human operator approves or rejects an action."""
        pending = self._pending.get(approval_id)
        if not pending or pending.status != "PENDING":
            return False

        pending.decision = decision
        pending.reviewer_notes = notes
        pending.status = "RESOLVED"
        pending._event.set()
        return True

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Returns list of all currently active pending approval requests."""
        return [
            {
                "approval_id": p.id,
                "request_id": p.request_id,
                "session_id": p.session_id,
                "task_intent": p.task_intent,
                "tool_name": p.tool_name,
                "target_resource": p.target_resource,
                "parameters": p.parameters,
                "risk_score": p.risk_score,
                "reason": p.reason,
                "signals": p.signals,
                "created_at": p.created_at,
                "timeout_sec": p.timeout_sec,
                "status": p.status
            }
            for p in self._pending.values()
            if p.status == "PENDING"
        ]

    def _record_approval_db(self, pending: PendingApproval) -> None:
        """Persists the review decision to the database."""
        try:
            engine = get_engine(self.db_url)
            with Session(engine) as db_session:
                rec = HumanApprovalRecord(
                    id=pending.id,
                    request_id=pending.request_id,
                    session_id=pending.session_id,
                    human_decision=pending.decision.value if pending.decision else "BLOCK",
                    reviewer_notes=pending.reviewer_notes,
                    responded_at=datetime.now(timezone.utc)
                )
                db_session.add(rec)
                db_session.commit()
        except Exception:
            pass
