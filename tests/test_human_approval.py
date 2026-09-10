"""
Unit and Integration Tests for Human-In-The-Loop Approval Workflow (Phase 5)

Verifies:
1. ASK_HUMAN pauses execution and registers a pending approval.
2. Operator approval (ALLOW_ONCE) triggers sandbox execution.
3. Operator rejection (BLOCK) prevents sandbox execution.
4. Approval timeout automatically defaults to BLOCK.
5. Telemetry persists HumanApprovalRecord in SQLite.
"""

import asyncio
import pytest
import shutil
import tempfile
from pathlib import Path
from sqlmodel import Session, select

from backend.agent.base_agent import ToolCallRequest
from backend.sandbox.environment import SandboxEnvironment
from backend.sandbox.tools import SandboxToolExecutor
from backend.gateway.context_extractor import SecurityContext
from backend.gateway.interceptor import AgentShieldGateway
from backend.gateway.human_approval import HumanApprovalRegistry, ApprovalDecision
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult
from backend.database.models import HumanApprovalRecord
from backend.database.db import get_engine


class AskHumanTestPolicy(BaseSecurityPolicy):
    """Test policy that always yields ASK_HUMAN."""
    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            decision="ASK_HUMAN",
            risk_score=55,
            confidence=0.85,
            reason="Ambiguous action requiring operator confirmation.",
            signals=["ambiguous_config_modification"],
            policy_name="AskHumanTestPolicy"
        )


@pytest.fixture
def hitl_setup():
    temp_dir = tempfile.mkdtemp(prefix="agentshield_hitl_test_")
    db_path = Path(temp_dir) / "hitl_telemetry.db"
    db_url = f"sqlite:///{db_path}"

    env = SandboxEnvironment(workspace_root=temp_dir)
    sandbox = SandboxToolExecutor(environment=env)
    registry = HumanApprovalRegistry(default_timeout_sec=0.5, db_url=db_url)
    policy = AskHumanTestPolicy()
    gateway = AgentShieldGateway(
        policy=policy,
        sandbox_executor=sandbox,
        db_url=db_url,
        approval_registry=registry
    )

    yield env, sandbox, registry, gateway, db_url
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_human_approval_allow_once(hitl_setup):
    """Verifies that human approval permits tool execution in sandbox."""
    env, sandbox, registry, gateway, db_url = hitl_setup

    request = ToolCallRequest(
        session_id="sess_hitl_01",
        step_number=1,
        tool_name="write_file",
        parameters={"path": "output/config.yaml", "content": "port: 9000"},
        task_intent="Update application port",
        agent_history=[]
    )

    # Background task simulating human operator approving within 0.1s
    async def approve_operator():
        await asyncio.sleep(0.05)
        pending = registry.get_pending_approvals()
        assert len(pending) == 1
        approval_id = pending[0]["approval_id"]
        registry.resolve_approval(approval_id, ApprovalDecision.ALLOW_ONCE, notes="Authorized for dev port.")

    task = asyncio.create_task(approve_operator())
    response = await gateway.dispatch(request)
    await task

    # Assert response indicates ALLOW
    assert response.decision == "ALLOW"
    assert response.success is True
    assert "human_approved" in response.signals

    # Verify file was actually written to sandbox
    read_res = sandbox.read_file("output/config.yaml")
    assert read_res["success"] is True
    assert "port: 9000" in read_res["output"]


@pytest.mark.asyncio
async def test_human_approval_reject_block(hitl_setup):
    """Verifies that human rejection strictly prevents tool execution."""
    env, sandbox, registry, gateway, db_url = hitl_setup

    request = ToolCallRequest(
        session_id="sess_hitl_02",
        step_number=1,
        tool_name="write_file",
        parameters={"path": "output/unauthorized.yaml", "content": "malicious: true"},
        task_intent="Update config",
        agent_history=[]
    )

    # Background task simulating operator rejecting
    async def reject_operator():
        await asyncio.sleep(0.05)
        pending = registry.get_pending_approvals()
        assert len(pending) == 1
        approval_id = pending[0]["approval_id"]
        registry.resolve_approval(approval_id, ApprovalDecision.BLOCK, notes="Rejected suspicious config.")

    task = asyncio.create_task(reject_operator())
    response = await gateway.dispatch(request)
    await task

    # Assert response indicates BLOCK
    assert response.decision == "BLOCK"
    assert response.success is False
    assert "human_rejected" in response.signals

    # Verify file was NOT created in sandbox
    read_res = sandbox.read_file("output/unauthorized.yaml")
    assert read_res["success"] is False


@pytest.mark.asyncio
async def test_human_approval_timeout_defaults_to_block(hitl_setup):
    """Verifies that when human operator does not respond, system defaults to BLOCK."""
    env, sandbox, registry, gateway, db_url = hitl_setup

    request = ToolCallRequest(
        session_id="sess_hitl_03",
        step_number=1,
        tool_name="run_command",
        parameters={"command": "pip install some-package"},
        task_intent="Upgrade dependencies",
        agent_history=[]
    )

    # No operator responds; wait for registry timeout (0.5s)
    response = await gateway.dispatch(request)

    assert response.decision == "BLOCK"
    assert response.success is False
    assert "approval_timeout" in response.signals
    assert "timed out" in response.reason.lower()


@pytest.mark.asyncio
async def test_human_approval_persisted_in_database(hitl_setup):
    """Verifies that HumanApprovalRecord is saved in SQLite database."""
    _, _, registry, gateway, db_url = hitl_setup

    request = ToolCallRequest(
        session_id="sess_hitl_04",
        step_number=1,
        tool_name="write_file",
        parameters={"path": "output/test.txt", "content": "hello"},
        task_intent="Write test",
        agent_history=[]
    )

    async def approve_operator():
        await asyncio.sleep(0.05)
        pending = registry.get_pending_approvals()
        approval_id = pending[0]["approval_id"]
        registry.resolve_approval(approval_id, ApprovalDecision.ALLOW_ONCE, notes="Approved by audit admin.")

    task = asyncio.create_task(approve_operator())
    await gateway.dispatch(request)
    await task

    engine = get_engine(db_url)
    with Session(engine) as db_session:
        records = db_session.exec(select(HumanApprovalRecord).where(HumanApprovalRecord.session_id == "sess_hitl_04")).all()
        assert len(records) == 1
        assert records[0].human_decision == "ALLOW_ONCE"
        assert records[0].reviewer_notes == "Approved by audit admin."
