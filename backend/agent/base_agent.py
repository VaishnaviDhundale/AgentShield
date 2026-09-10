"""
Base ReAct AI Agent with Mandatory Gateway Tool-Call Dispatching for AgentShield

INVARIANT:
The Agent NEVER directly references or invokes the Sandbox Executor.
All tool executions are requested via the IToolGateway interface.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol, List, Dict, Any, Optional

from backend.agent.llm_provider import BaseLLMProvider, ToolCall, LLMResponse
from backend.agent.prompts import SYSTEM_PROMPT, AGENT_TOOL_DEFINITIONS


@dataclass
class ToolCallRequest:
    """Structured tool request emitted by the Agent to the Gateway."""
    session_id: str
    step_number: int
    tool_name: str
    parameters: Dict[str, Any]
    task_intent: str
    agent_history: List[Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallResponse:
    """Standardized response received by the Agent from the Gateway."""
    request_id: str
    decision: str  # ALLOW | BLOCK | ASK_HUMAN
    success: bool
    output: Any
    error: Optional[str] = None
    risk_score: Optional[int] = None
    reason: Optional[str] = None
    signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IToolGateway(Protocol):
    """
    Protocol / Interface defining the Gateway boundary.
    Any tool execution must pass through this dispatcher.
    """
    async def dispatch(self, request: ToolCallRequest) -> ToolCallResponse:
        """Intercepts, evaluates, and dispatches the tool call."""
        ...


@dataclass
class AgentStep:
    """Record of a single step in the agent's reasoning loop."""
    step_number: int
    thought: Optional[str]
    tool_request: Optional[ToolCallRequest] = None
    tool_response: Optional[ToolCallResponse] = None


@dataclass
class AgentRunResult:
    """Result summary of an agent task execution session."""
    session_id: str
    task_intent: str
    steps: List[AgentStep]
    completed: bool
    final_answer: str
    total_tool_calls: int
    blocked_tool_calls: int
    duration_sec: float


class AgentShieldAgent:
    """
    Autonomous AI Software Engineering Agent.
    
    Operates via a ReAct loop:
    1. Sends current context to LLM.
    2. Extracts thought and planned tool call.
    3. Emits ToolCallRequest to the Gateway (never directly to sandbox tools).
    4. Feeds ToolCallResponse back to context.
    5. Repeats until task completion or max_steps reached.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        tool_gateway: IToolGateway,
        system_prompt: str = SYSTEM_PROMPT,
        tools_schema: Optional[List[Dict[str, Any]]] = None
    ):
        self.llm = llm_provider
        self.gateway = tool_gateway
        self.system_prompt = system_prompt
        self.tools_schema = tools_schema or AGENT_TOOL_DEFINITIONS

    async def run(
        self,
        task_intent: str,
        session_id: Optional[str] = None,
        max_steps: int = 8
    ) -> AgentRunResult:
        """Runs the agent loop for a given task intent."""
        start_time = time.perf_counter()
        session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {task_intent}"}
        ]

        steps: List[AgentStep] = []
        total_calls = 0
        blocked_calls = 0
        final_answer = ""
        completed = False

        history_summary: List[Dict[str, Any]] = []

        for step_idx in range(1, max_steps + 1):
            # 1. Ask LLM for next action
            llm_res: LLMResponse = await self.llm.generate(
                messages=messages,
                tools=self.tools_schema
            )

            thought = llm_res.content or ""
            step_record = AgentStep(step_number=step_idx, thought=thought)

            # If no tool calls, the agent has finished its task
            if not llm_res.tool_calls:
                final_answer = thought
                completed = True
                steps.append(step_record)
                break

            # Process the first planned tool call (ReAct step)
            tool_call: ToolCall = llm_res.tool_calls[0]
            total_calls += 1

            # 2. Package into structured ToolCallRequest
            request = ToolCallRequest(
                session_id=session_id,
                step_number=step_idx,
                tool_name=tool_call.name,
                parameters=tool_call.arguments,
                task_intent=task_intent,
                agent_history=list(history_summary)
            )
            step_record.tool_request = request

            # 3. Dispatch through the Gateway (Invariant: agent does not execute tool)
            response: ToolCallResponse = await self.gateway.dispatch(request)
            step_record.tool_response = response

            if response.decision == "BLOCK":
                blocked_calls += 1

            # 4. Record to history summary for contextual tracking
            history_summary.append({
                "step": step_idx,
                "tool": tool_call.name,
                "parameters": tool_call.arguments,
                "decision": response.decision,
                "success": response.success
            })

            steps.append(step_record)

            # 5. Append assistant thought and tool result to messages
            messages.append({
                "role": "assistant",
                "content": thought,
                "tool_calls": [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": str(tool_call.arguments)
                    }
                }]
            })

            # Format tool observation string for LLM
            if response.decision == "BLOCK":
                obs_content = f"AGENTSHIELD GATEWAY BLOCKED ACTION: {response.reason or 'Security policy violation'}"
            elif response.success:
                obs_content = f"TOOL RESULT:\n{str(response.output)}"
            else:
                obs_content = f"TOOL ERROR: {response.error}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.name,
                "content": obs_content
            })

        duration = time.perf_counter() - start_time
        return AgentRunResult(
            session_id=session_id,
            task_intent=task_intent,
            steps=steps,
            completed=completed,
            final_answer=final_answer or "Max steps reached without explicit completion.",
            total_tool_calls=total_calls,
            blocked_tool_calls=blocked_calls,
            duration_sec=duration
        )
