"""
Unit and Integration Tests for AgentShield Security Gateway (Phase 3)

Verifies:
1. Interception of tool calls by AgentShieldGateway.
2. Context extraction: Target resource, Resource Sensitivity (LOW, MEDIUM, HIGH, CRITICAL), Action Risk.
3. Execution routing for ALLOW decisions to SandboxToolExecutor.
4. Non-execution of Sandbox tools when decision is BLOCK.
5. Telemetry audit logging to SQLite (SessionRecord, RequestRecord, DecisionRecord).
6. Live event broadcaster hook.
"""

import pytest
import shutil
import tempfile
from pathlib import Path
from sqlmodel import Session, select

from backend.agent.base_agent import ToolCallRequest
from backend.sandbox.environment import SandboxEnvironment
from backend.sandbox.tools import SandboxToolExecutor
from backend.gateway.context_extractor import ContextExtractor, SecurityContext
from backend.gateway.interceptor import AgentShieldGateway
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult
from backend.database.models import SessionRecord, RequestRecord, DecisionRecord
from backend.database.db import get_engine


class AllowAllTestPolicy(BaseSecurityPolicy):
    """Test policy that permits all requests."""
    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            decision="ALLOW",
            risk_score=10,
            confidence=0.99,
            reason="Test allow all",
            signals=["test_allow"],
            policy_name="AllowAllTestPolicy"
        )


class BlockAllTestPolicy(BaseSecurityPolicy):
    """Test policy that blocks all requests."""
    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            decision="BLOCK",
            risk_score=95,
            confidence=0.95,
            reason="Test block all",
            signals=["critical_risk"],
            policy_name="BlockAllTestPolicy"
        )


@pytest.fixture
def gateway_setup():
    """Provides a fresh temporary sandbox, SQLite database, and gateway instance."""
    temp_dir = tempfile.mkdtemp(prefix="agentshield_gateway_test_")
    db_path = Path(temp_dir) / "test_telemetry.db"
    db_url = f"sqlite:///{db_path}"

    env = SandboxEnvironment(workspace_root=temp_dir)
    sandbox = SandboxToolExecutor(environment=env)
    
    yield env, sandbox, db_url
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_context_extractor():
    """Verifies that ContextExtractor correctly identifies sensitivity and risk."""
    req_secret = ToolCallRequest(
        session_id="s1",
        step_number=1,
        tool_name="read_file",
        parameters={"path": "secrets/.env"},
        task_intent="Fix bug",
        agent_history=[]
    )
    ctx_secret = ContextExtractor.extract(req_secret, "req_1")
    assert ctx_secret.target_resource == "secrets/.env"
    assert ctx_secret.resource_sensitivity == "CRITICAL"
    assert ctx_secret.sensitivity_score == 95
    assert ctx_secret.action_risk == 20

    req_delete = ToolCallRequest(
        session_id="s1",
        step_number=2,
        tool_name="delete_file",
        parameters={"path": "project/src/main.py"},
        task_intent="Fix bug",
        agent_history=[]
    )
    ctx_delete = ContextExtractor.extract(req_delete, "req_2")
    assert ctx_delete.resource_sensitivity == "MEDIUM"
    assert ctx_delete.action_risk == 85


@pytest.mark.asyncio
async def test_gateway_dispatch_allow(gateway_setup):
    """Verifies that an ALLOW decision executes the tool in sandbox and records audit log."""
    _, sandbox, db_url = gateway_setup
    policy = AllowAllTestPolicy()
    gateway = AgentShieldGateway(policy=policy, sandbox_executor=sandbox, db_url=db_url)

    request = ToolCallRequest(
        session_id="sess_allow_01",
        step_number=1,
        tool_name="read_file",
        parameters={"path": "project/src/auth.py"},
        task_intent="Inspect authentication code",
        agent_history=[]
    )

    response = await gateway.dispatch(request)

    # Verify response structure
    assert response.decision == "ALLOW"
    assert response.success is True
    assert "authenticate_user" in str(response.output)
    assert response.risk_score == 10

    # Verify SQLite database persistence
    engine = get_engine(db_url)
    with Session(engine) as db_session:
        session_rec = db_session.get(SessionRecord, "sess_allow_01")
        assert session_rec is not None
        assert session_rec.total_calls == 1
        assert session_rec.allowed_calls == 1
        assert session_rec.blocked_calls == 0

        req_recs = db_session.exec(select(RequestRecord).where(RequestRecord.session_id == "sess_allow_01")).all()
        assert len(req_recs) == 1
        assert req_recs[0].tool_name == "read_file"

        dec_recs = db_session.exec(select(DecisionRecord).where(DecisionRecord.session_id == "sess_allow_01")).all()
        assert len(dec_recs) == 1
        assert dec_recs[0].decision == "ALLOW"


@pytest.mark.asyncio
async def test_gateway_dispatch_block(gateway_setup):
    """Verifies that a BLOCK decision prevents sandbox tool execution."""
    env, sandbox, db_url = gateway_setup
    policy = BlockAllTestPolicy()
    gateway = AgentShieldGateway(policy=policy, sandbox_executor=sandbox, db_url=db_url)

    # Attempt to delete main.py under BlockAll policy
    request = ToolCallRequest(
        session_id="sess_block_01",
        step_number=1,
        tool_name="delete_file",
        parameters={"path": "project/src/main.py"},
        task_intent="Delete project entrypoint",
        agent_history=[]
    )

    response = await gateway.dispatch(request)

    # Verify Gateway response
    assert response.decision == "BLOCK"
    assert response.success is False
    assert "AgentShield blocked action" in response.error

    # Verify file was NOT deleted in sandbox
    main_path = env.root_path / "project" / "src" / "main.py"
    assert main_path.exists() is True

    # Verify SQLite audit log
    engine = get_engine(db_url)
    with Session(engine) as db_session:
        session_rec = db_session.get(SessionRecord, "sess_block_01")
        assert session_rec.blocked_calls == 1
        assert session_rec.allowed_calls == 0


@pytest.mark.asyncio
async def test_gateway_event_broadcaster(gateway_setup):
    """Verifies that real-time events are broadcasted to listeners."""
    _, sandbox, db_url = gateway_setup
    broadcasted_events = []

    def mock_broadcaster(event):
        broadcasted_events.append(event)

    policy = AllowAllTestPolicy()
    gateway = AgentShieldGateway(
        policy=policy,
        sandbox_executor=sandbox,
        db_url=db_url,
        event_broadcaster=mock_broadcaster
    )

    request = ToolCallRequest(
        session_id="sess_ws_01",
        step_number=1,
        tool_name="list_files",
        parameters={"directory": "project"},
        task_intent="List files in project",
        agent_history=[]
    )

    await gateway.dispatch(request)

    assert len(broadcasted_events) == 1
    event = broadcasted_events[0]
    assert event["event_type"] == "TOOL_REQUEST_INTERCEPTED"
    assert event["session_id"] == "sess_ws_01"
    assert event["decision"] == "ALLOW"
    assert event["tool_name"] == "list_files"
