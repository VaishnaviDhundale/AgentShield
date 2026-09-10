"""
Unit and Integration Tests for AI Agent & LLM Abstraction (Phase 2)

Verifies:
1. LLM provider abstraction and deterministic Mock/Replay provider.
2. ReAct agent loop step execution.
3. INVARIANT: Agent emits structured ToolCallRequests through IToolGateway
   and does not possess or directly call sandbox executors.
4. Handling of Gateway ALLOW and BLOCK responses.
5. Controlled prompt-injection scenarios.
"""

import pytest
from typing import List

from backend.agent.llm_provider import (
    MockLLMProvider,
    LLMResponse,
    ToolCall,
    get_llm_provider
)
from backend.agent.base_agent import (
    AgentShieldAgent,
    ToolCallRequest,
    ToolCallResponse,
    IToolGateway
)
from backend.agent.prompts import INJECTION_PAYLOAD_SECRET_LEAK


class MockToolGateway(IToolGateway):
    """
    Mock gateway implementation for testing agent tool dispatching.
    Tracks all intercepted requests and allows test assertions.
    """

    def __init__(self, default_decision: str = "ALLOW"):
        self.default_decision = default_decision
        self.dispatched_requests: List[ToolCallRequest] = []

    async def dispatch(self, request: ToolCallRequest) -> ToolCallResponse:
        self.dispatched_requests.append(request)
        if self.default_decision == "BLOCK":
            return ToolCallResponse(
                request_id=f"req_{len(self.dispatched_requests)}",
                decision="BLOCK",
                success=False,
                output=None,
                error="Access denied by security gateway.",
                risk_score=95,
                reason="Unauthorized access to critical resource.",
                signals=["critical_secret", "task_mismatch"]
            )
        else:
            return ToolCallResponse(
                request_id=f"req_{len(self.dispatched_requests)}",
                decision="ALLOW",
                success=True,
                output=f"Simulated execution output for {request.tool_name}",
                risk_score=15,
                reason="Legitimate task operation.",
                signals=["task_aligned"]
            )


@pytest.mark.asyncio
async def test_mock_provider_scripted_responses():
    """Verifies that MockLLMProvider correctly pops and yields scripted responses."""
    mock_llm = MockLLMProvider()
    mock_llm.add_scripted_response(
        LLMResponse(
            content="Checking tests first.",
            tool_calls=[ToolCall(id="c1", name="run_tests", arguments={"test_target": "tests"})]
        )
    )
    mock_llm.add_scripted_response(
        LLMResponse(content="Tests passed. Done.", tool_calls=[])
    )

    res1 = await mock_llm.generate([{"role": "user", "content": "Run tests"}])
    assert res1.content == "Checking tests first."
    assert len(res1.tool_calls) == 1
    assert res1.tool_calls[0].name == "run_tests"

    res2 = await mock_llm.generate([{"role": "user", "content": "Next step"}])
    assert res2.content == "Tests passed. Done."
    assert len(res2.tool_calls) == 0


@pytest.mark.asyncio
async def test_agent_dispatches_tool_calls_through_gateway():
    """
    Verifies that the Agent dispatches all actions through IToolGateway.
    Proves the agent does not execute tools directly.
    """
    mock_llm = MockLLMProvider()
    mock_gateway = MockToolGateway(default_decision="ALLOW")
    agent = AgentShieldAgent(llm_provider=mock_llm, tool_gateway=mock_gateway)

    result = await agent.run(task_intent="Fix authentication bug in auth.py", max_steps=5)

    assert result.completed is True
    assert result.total_tool_calls == 2
    assert result.blocked_tool_calls == 0

    # Verify requests arrived at the gateway
    assert len(mock_gateway.dispatched_requests) == 2
    req1 = mock_gateway.dispatched_requests[0]
    assert req1.tool_name == "read_file"
    assert req1.parameters == {"path": "project/src/auth.py"}
    assert req1.task_intent == "Fix authentication bug in auth.py"

    req2 = mock_gateway.dispatched_requests[1]
    assert req2.tool_name == "run_tests"
    assert req2.parameters == {"test_target": "tests/test_auth.py"}


@pytest.mark.asyncio
async def test_agent_handles_gateway_block():
    """Verifies agent behavior when the Gateway intercepts and BLOCKS an action."""
    mock_llm = MockLLMProvider()
    blocking_gateway = MockToolGateway(default_decision="BLOCK")
    agent = AgentShieldAgent(llm_provider=mock_llm, tool_gateway=blocking_gateway)

    result = await agent.run(task_intent="Fix authentication bug in auth.py", max_steps=3)

    assert result.total_tool_calls >= 1
    assert result.blocked_tool_calls >= 1
    # First step should have recorded BLOCK decision
    assert result.steps[0].tool_response.decision == "BLOCK"
    assert "critical_secret" in result.steps[0].tool_response.signals


@pytest.mark.asyncio
async def test_agent_prompt_injection_simulation():
    """
    Verifies that an adversarial prompt injection leads the agent to emit a tool request
    for secrets/.env, which is intercepted by the gateway.
    """
    mock_llm = MockLLMProvider()
    mock_gateway = MockToolGateway(default_decision="BLOCK")
    agent = AgentShieldAgent(llm_provider=mock_llm, tool_gateway=mock_gateway)

    task = f"Inspect code. {INJECTION_PAYLOAD_SECRET_LEAK}"
    result = await agent.run(task_intent=task, max_steps=2)

    assert len(mock_gateway.dispatched_requests) >= 1
    first_req = mock_gateway.dispatched_requests[0]
    assert first_req.tool_name == "read_file"
    assert first_req.parameters.get("path") == "secrets/.env"
    assert result.steps[0].tool_response.decision == "BLOCK"


def test_llm_provider_factory():
    """Verifies provider factory instantiates correct providers."""
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockLLMProvider)

    openai_p = get_llm_provider("openai", api_key="sk-test", base_url="http://localhost:8000")
    assert openai_p.__class__.__name__ == "GenericOpenAICompatibleProvider"
