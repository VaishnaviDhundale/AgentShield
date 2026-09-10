"""
Human-In-The-Loop Approval REST Endpoints for AgentShield
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.gateway.human_approval import ApprovalDecision

router = APIRouter(prefix="/api/approvals", tags=["Human Approvals"])


class ResolveApprovalPayload(BaseModel):
    decision: str  # ALLOW_ONCE | ALLOW_SESSION | BLOCK
    notes: Optional[str] = None


@router.get("/pending")
def list_pending_approvals():
    """
    Returns all requests currently paused in the Gateway awaiting human authorization.
    """
    return service.approval_registry.get_pending_approvals()


@router.post("/{approval_id}/resolve")
async def resolve_pending_approval(approval_id: str, payload: ResolveApprovalPayload):
    """
    Resolves a pending authorization request.
    ALLOW triggers sandbox execution; BLOCK rejects execution.
    """
    dec_upper = payload.decision.upper()
    if dec_upper not in (ApprovalDecision.ALLOW_ONCE.value, ApprovalDecision.ALLOW_SESSION.value, ApprovalDecision.BLOCK.value):
        raise HTTPException(status_code=400, detail="Invalid decision. Must be ALLOW_ONCE, ALLOW_SESSION, or BLOCK.")

    target_enum = ApprovalDecision(dec_upper)
    success = service.approval_registry.resolve_approval(
        approval_id=approval_id,
        decision=target_enum,
        notes=payload.notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="Pending approval not found or already resolved.")

    # Broadcast resolution event
    await ws_manager.broadcast({
        "event_type": "HUMAN_APPROVAL_RESOLVED",
        "approval_id": approval_id,
        "decision": dec_upper,
        "notes": payload.notes
    })

    return {
        "status": "success",
        "approval_id": approval_id,
        "decision": dec_upper,
        "notes": payload.notes
    }
