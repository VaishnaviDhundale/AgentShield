"""
Baseline 2: Static Permission Policy

Implements fixed, context-unaware authorization rules based solely on tool name
and file path patterns. Does NOT consider task intent or agent history.
"""

import time
import re
from backend.gateway.context_extractor import SecurityContext
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult


class StaticPermissionPolicy(BaseSecurityPolicy):
    """
    Fixed static permission policy:
    - read_file/write_file: allowed for code files; strictly blocked for .env/credentials
    - delete_file: always blocked
    - run_tests, list_files: always allowed
    - run_command, database_query, http_request: always blocked
    """

    STATIC_BLOCKED_PATHS = [r"\.env", r"credentials\.json", r"api_keys\.txt"]

    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        start = time.perf_counter()
        tool = context.tool_name
        target = str(context.target_resource).lower()

        # Check static forbidden path list regardless of task intent
        for pat in self.STATIC_BLOCKED_PATHS:
            if re.search(pat, target):
                return PolicyEvaluationResult(
                    decision="BLOCK",
                    risk_score=90,
                    confidence=1.0,
                    reason="StaticPolicy: Target file is on the static forbidden path list.",
                    signals=["static_forbidden_path"],
                    policy_name="StaticPermissionPolicy",
                    latency_ms=(time.perf_counter() - start) * 1000.0,
                    estimated_cost_usd=0.0
                )

        # Check static tool rules
        if tool in ("read_file", "write_file", "list_files", "run_tests", "git_operation"):
            return PolicyEvaluationResult(
                decision="ALLOW",
                risk_score=10,
                confidence=1.0,
                reason=f"StaticPolicy: Tool '{tool}' is permitted by default static policy.",
                signals=["static_tool_permitted"],
                policy_name="StaticPermissionPolicy",
                latency_ms=(time.perf_counter() - start) * 1000.0,
                estimated_cost_usd=0.0
            )
        elif tool == "delete_file":
            return PolicyEvaluationResult(
                decision="BLOCK",
                risk_score=85,
                confidence=1.0,
                reason="StaticPolicy: All file deletions are blocked by static rule.",
                signals=["static_tool_blocked"],
                policy_name="StaticPermissionPolicy",
                latency_ms=(time.perf_counter() - start) * 1000.0,
                estimated_cost_usd=0.0
            )
        else:
            # run_command, database_query, http_request blocked by default
            return PolicyEvaluationResult(
                decision="BLOCK",
                risk_score=80,
                confidence=1.0,
                reason=f"StaticPolicy: High-risk tool '{tool}' is disabled in static policy.",
                signals=["static_tool_disabled"],
                policy_name="StaticPermissionPolicy",
                latency_ms=(time.perf_counter() - start) * 1000.0,
                estimated_cost_usd=0.0
            )
