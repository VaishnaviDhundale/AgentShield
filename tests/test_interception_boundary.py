"""
Security & Architecture Boundary Test (Phase 3)

Explicitly verifies:
1. System Invariant: Agent -> AgentShield Gateway -> Policy/Risk Decision -> Sandbox Executor -> Database Log.
2. The Agent has no direct reference to SandboxToolExecutor.
3. Every single tool executed by the Agent passes through the Gateway.
4. When Gateway blocks, the Sandbox is never touched.
"""

import pytest
import shutil
import tempfile
from pathlib import Path
from sqlmodel import Session, select

from backend.agent.base_agent import AgentShieldAgent, ToolCallRequest
from backend.agent.llm_provider import MockLLMProvider, LLMResponse, ToolCall
from backend.sandbox.environment import SandboxEnvironment
from backend.sandbox.tools import SandboxToolExecutor
from backend.gateway.interceptor import AgentShieldGateway
from backend.gateway.context_extractor import SecurityContext
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult
from backend.database.models import SessionRecord, RequestRecord, DecisionRecord
from backend.database.db import get_engine


class DynamicInspectorPolicy(BaseSecurityPolicy):
    """Inspects actions and allows or blocks based on target file path."""

    def __init__(self):
        self.evaluated_contexts = []

    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        self.evaluated_contexts.append(context)
        # Block if accessing .env
        if "secrets/.env" in context.target_resource or ".env" in str(context.parameters.get("path", "")):
            return PolicyEvaluationResult(
                decision="BLOCK",
                risk_score=94,
                confidence=0.98,
                reason="Access to critical secret is prohibited for this task.",
                signals=["critical_secret", "task_mismatch"],
                policy_name="DynamicInspectorPolicy"
            )
        return PolicyEvaluationResult(
            decision="ALLOW",
            risk_score=15,
            confidence=0.95,
            reason="Legitimate file operation.",
            signals=["task_aligned"],
            policy_name="DynamicInspectorPolicy"
        )


@pytest.fixture
def boundary_environment():
    temp_dir = tempfile.mkdtemp(prefix="agentshield_boundary_test_")
    db_path = Path(temp_dir) / "boundary_telemetry.db"
    db_url = f"sqlite:///{db_path}"

    env = SandboxEnvironment(workspace_root=temp_dir)
    sandbox = SandboxToolExecutor(environment=env)
    policy = DynamicInspectorPolicy()
    gateway = AgentShieldGateway(policy=policy, sandbox_executor=sandbox, db_url=db_url)

    yield env, sandbox, policy, gateway, db_url
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_end_to_end_gateway_interception_boundary(boundary_environment):
    """
    Demonstrates the full end-to-end pipeline:
    Agent -> Gateway -> Policy -> Sandbox Executor -> Telemetry.
    Proves tool execution cannot bypass the Gateway.
    """
    env, sandbox, policy, gateway, db_url = boundary_environment

    # 1. Configure Mock LLM with a 2-step plan:
    # Step 1: Legitimate read of auth.py
    # Step 2: Attempted read of secrets/.env (prompt injection style)
    mock_llm = MockLLMProvider()
    mock_llm.add_scripted_response(
        LLMResponse(
            content="Reading auth.py to inspect login logic.",
            tool_calls=[ToolCall(id="c1", name="read_file", arguments={"path": "project/src/auth.py"})]
        )
    )
    mock_llm.add_scripted_response(
        LLMResponse(
            content="Attempting to read secrets/.env.",
            tool_calls=[ToolCall(id="c2", name="read_file", arguments={"path": "secrets/.env"})]
        )
    )
    mock_llm.add_scripted_response(
        LLMResponse(content="Task aborted due to policy block.", tool_calls=[])
    )

    # Agent is initialized with the Gateway (and knows nothing about the Sandbox executor)
    agent = AgentShieldAgent(llm_provider=mock_llm, tool_gateway=gateway)
    assert not hasattr(agent, "sandbox")

    # 2. Run agent
    session_id = "sess_boundary_001"
    result = await agent.run(
        task_intent="Fix authentication bug in auth.py",
        session_id=session_id,
        max_steps=4
    )

    # 3. Assert Policy evaluated all actions
    assert len(policy.evaluated_contexts) == 2
    assert policy.evaluated_contexts[0].target_resource == "project/src/auth.py"
    assert policy.evaluated_contexts[1].target_resource == "secrets/.env"

    # 4. Assert Step 1 was ALLOWED and Step 2 was BLOCKED
    assert len(result.steps) == 3
    assert result.steps[0].tool_response.decision == "ALLOW"
    assert "authenticate_user" in str(result.steps[0].tool_response.output)

    assert result.steps[1].tool_response.decision == "BLOCK"
    assert "critical_secret" in result.steps[1].tool_response.signals
    assert result.steps[1].tool_response.output is None

    # 5. Assert Database Telemetry matches 1:1
    engine = get_engine(db_url)
    with Session(engine) as db_session:
        session_rec = db_session.get(SessionRecord, session_id)
        assert session_rec.total_calls == 2
        assert session_rec.allowed_calls == 1
        assert session_rec.blocked_calls == 1

        decisions = db_session.exec(
            select(DecisionRecord).where(DecisionRecord.session_id == session_id).order_by(DecisionRecord.created_at)
        ).all()
        assert len(decisions) == 2
        assert decisions[0].decision == "ALLOW"
        assert decisions[1].decision == "BLOCK"
        assert decisions[1].risk_score == 94
