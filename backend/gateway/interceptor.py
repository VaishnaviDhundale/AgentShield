"""
AgentShield Security Gateway Interceptor

INVARIANT:
Sits strictly between the AI Agent and the Sandbox Tool Executor.
Every tool request must be intercepted, evaluated by an active policy, logged to the database,
and only dispatched to the Sandbox Executor if permitted (or approved by human in the loop).
"""

import json
import time
import uuid
from typing import Optional, Callable, Dict, Any
from sqlmodel import Session, select

from backend.agent.base_agent import ToolCallRequest, ToolCallResponse, IToolGateway
from backend.gateway.context_extractor import ContextExtractor, SecurityContext
from backend.gateway.human_approval import HumanApprovalRegistry, ApprovalDecision
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult
from backend.sandbox.tools import SandboxToolExecutor
from backend.database.db import get_engine
from backend.database.models import SessionRecord, RequestRecord, DecisionRecord


class AgentShieldGateway(IToolGateway):
    """
    Central Runtime Security Gateway for tool-using AI agents.
    """

    def __init__(
        self,
        policy: BaseSecurityPolicy,
        sandbox_executor: SandboxToolExecutor,
        db_url: Optional[str] = None,
        approval_registry: Optional[HumanApprovalRegistry] = None,
        event_broadcaster: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.policy = policy
        self.sandbox = sandbox_executor
        self.db_url = db_url
        self.engine = get_engine(db_url)
        self.approval_registry = approval_registry or HumanApprovalRegistry(db_url=db_url)
        self.broadcaster = event_broadcaster

    def set_policy(self, policy: BaseSecurityPolicy) -> None:
        """Dynamically switches the active security policy."""
        self.policy = policy

    async def dispatch(self, request: ToolCallRequest) -> ToolCallResponse:
        """
        Intercepts incoming agent tool call, evaluates security policy,
        executes in sandbox if permitted (or approved by human), logs telemetry,
        and returns standardized response.
        """
        start_time = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        # 1. Extract security context
        context: SecurityContext = ContextExtractor.extract(request, request_id)

        # 2. Evaluate through active Security Policy
        eval_result: PolicyEvaluationResult = await self.policy.evaluate(context)

        # 3. Handle Decision Execution & Human Approval Workflow
        final_decision = eval_result.decision
        execution_success = False
        tool_output = None
        tool_error = None
        metadata = {}
        signals = list(eval_result.signals)
        reason = eval_result.reason

        if eval_result.decision == "ALLOW":
            # Execute safely in sandbox
            tool_result = self._execute_in_sandbox(request.tool_name, request.parameters)
            execution_success = tool_result.get("success", False)
            tool_output = tool_result.get("output")
            tool_error = tool_result.get("error")
            metadata = tool_result.get("metadata", {})

        elif eval_result.decision == "BLOCK":
            # Explicitly do NOT execute in sandbox
            execution_success = False
            tool_output = None
            tool_error = f"AgentShield blocked action: {eval_result.reason}"

        elif eval_result.decision == "ASK_HUMAN":
            # Human-in-the-loop security boundary
            pending = self.approval_registry.request_approval(
                request_id=request_id,
                session_id=request.session_id,
                task_intent=request.task_intent,
                tool_name=request.tool_name,
                target_resource=context.target_resource,
                parameters=request.parameters,
                risk_score=eval_result.risk_score,
                reason=eval_result.reason,
                signals=eval_result.signals
            )

            # Broadcast approval prompt to live UI
            if self.broadcaster:
                self.broadcaster({
                    "event_type": "HUMAN_APPROVAL_REQUIRED",
                    "approval_id": pending.id,
                    "request_id": request_id,
                    "session_id": request.session_id,
                    "tool_name": request.tool_name,
                    "target_resource": context.target_resource,
                    "parameters": request.parameters,
                    "risk_score": eval_result.risk_score,
                    "reason": eval_result.reason,
                    "signals": eval_result.signals,
                    "timeout_sec": pending.timeout_sec
                })

            # Wait for human decision or timeout
            human_decision = await self.approval_registry.wait_for_decision(pending.id)

            if human_decision in (ApprovalDecision.ALLOW_ONCE, ApprovalDecision.ALLOW_SESSION):
                final_decision = "ALLOW"
                signals.append("human_approved")
                reason = f"Approved by human operator. (Original: {eval_result.reason})"
                tool_result = self._execute_in_sandbox(request.tool_name, request.parameters)
                execution_success = tool_result.get("success", False)
                tool_output = tool_result.get("output")
                tool_error = tool_result.get("error")
                metadata = tool_result.get("metadata", {})
            else:
                final_decision = "BLOCK"
                if human_decision == ApprovalDecision.TIMEOUT:
                    signals.append("approval_timeout")
                    reason = "Human approval timed out. Defaulted to BLOCK."
                else:
                    signals.append("human_rejected")
                    reason = f"Rejected by human operator: {pending.reviewer_notes or 'Unauthorized action'}"
                execution_success = False
                tool_output = None
                tool_error = f"AgentShield blocked action: {reason}"

        latency = (time.perf_counter() - start_time) * 1000.0

        # 4. Construct standardized ToolCallResponse
        response = ToolCallResponse(
            request_id=request_id,
            decision=final_decision,
            success=execution_success,
            output=tool_output,
            error=tool_error,
            risk_score=eval_result.risk_score,
            reason=reason,
            signals=signals,
            metadata={
                **metadata,
                "latency_ms": latency,
                "policy": eval_result.policy_name,
                "resource_sensitivity": context.resource_sensitivity,
                "action_risk": context.action_risk,
                "original_policy_decision": eval_result.decision
            }
        )

        # 5. Persist audit telemetry to SQLite database
        self._record_telemetry(request, context, eval_result, final_decision, execution_success, latency, signals, reason)

        # 6. Broadcast completed event
        if self.broadcaster:
            event_payload = {
                "event_type": "TOOL_REQUEST_INTERCEPTED",
                "request_id": request_id,
                "session_id": request.session_id,
                "step_number": request.step_number,
                "tool_name": request.tool_name,
                "target_resource": context.target_resource,
                "decision": final_decision,
                "risk_score": eval_result.risk_score,
                "reason": reason,
                "signals": signals,
                "policy_name": eval_result.policy_name,
                "latency_ms": latency,
                "timestamp": time.time()
            }
            try:
                self.broadcaster(event_payload)
            except Exception:
                pass

        return response

    def _execute_in_sandbox(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Routes permitted tool calls to the Sandbox Executor."""
        try:
            if tool_name == "read_file":
                return self.sandbox.read_file(path=params.get("path", ""))
            elif tool_name == "write_file":
                return self.sandbox.write_file(path=params.get("path", ""), content=params.get("content", ""))
            elif tool_name == "delete_file":
                return self.sandbox.delete_file(path=params.get("path", ""))
            elif tool_name == "list_files":
                return self.sandbox.list_files(directory=params.get("directory", "."))
            elif tool_name == "run_command":
                return self.sandbox.run_command(command=params.get("command", ""))
            elif tool_name == "run_tests":
                return self.sandbox.run_tests(test_target=params.get("test_target", "tests"))
            elif tool_name == "database_query":
                return self.sandbox.database_query(
                    query=params.get("query", ""),
                    db_path=params.get("db_path", "database/fake_users.db")
                )
            elif tool_name == "http_request":
                return self.sandbox.http_request(
                    method=params.get("method", "GET"),
                    url=params.get("url", ""),
                    headers=params.get("headers"),
                    body=params.get("body")
                )
            elif tool_name == "git_operation":
                return self.sandbox.git_operation(
                    subcommand=params.get("subcommand", "status"),
                    args=params.get("args")
                )
            else:
                return {"success": False, "output": None, "error": f"Unknown tool: '{tool_name}'"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def _record_telemetry(
        self,
        request: ToolCallRequest,
        context: SecurityContext,
        eval_result: PolicyEvaluationResult,
        final_decision: str,
        execution_success: bool,
        latency_ms: float,
        signals: list,
        reason: str
    ) -> None:
        """Persists session, request, and decision audit logs to SQLite."""
        try:
            with Session(self.engine) as db_session:
                session_rec = db_session.get(SessionRecord, request.session_id)
                if not session_rec:
                    session_rec = SessionRecord(
                        id=request.session_id,
                        task_intent=request.task_intent,
                        policy_name=eval_result.policy_name,
                        status="running",
                        total_calls=1,
                        allowed_calls=1 if final_decision == "ALLOW" else 0,
                        blocked_calls=1 if final_decision == "BLOCK" else 0,
                        human_approved_calls=1 if "human_approved" in signals else 0
                    )
                    db_session.add(session_rec)
                else:
                    session_rec.total_calls += 1
                    if final_decision == "ALLOW":
                        session_rec.allowed_calls += 1
                    elif final_decision == "BLOCK":
                        session_rec.blocked_calls += 1
                    if "human_approved" in signals:
                        session_rec.human_approved_calls += 1
                    db_session.add(session_rec)

                req_rec = RequestRecord(
                    id=context.request_id,
                    session_id=request.session_id,
                    step_number=request.step_number,
                    tool_name=request.tool_name,
                    target_resource=context.target_resource,
                    parameters_json=json.dumps(request.parameters),
                    task_intent=request.task_intent,
                    agent_history_json=json.dumps(request.agent_history)
                )
                db_session.add(req_rec)

                dec_rec = DecisionRecord(
                    id=f"dec_{uuid.uuid4().hex[:12]}",
                    request_id=context.request_id,
                    session_id=request.session_id,
                    decision=final_decision,
                    risk_score=eval_result.risk_score,
                    confidence=eval_result.confidence,
                    reason=reason,
                    signals_json=json.dumps(signals),
                    policy_name=eval_result.policy_name,
                    resource_sensitivity=context.resource_sensitivity,
                    action_risk=context.action_risk,
                    latency_ms=latency_ms,
                    estimated_cost_usd=eval_result.estimated_cost_usd,
                    executed_success=execution_success
                )
                db_session.add(dec_rec)

                db_session.commit()
        except Exception:
            pass
