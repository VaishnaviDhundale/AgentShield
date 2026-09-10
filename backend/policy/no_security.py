"""
Baseline 1: No Security Policy

Allows all requested actions indiscriminately without any authorization checks.
Used as the research baseline to measure raw vulnerability and attack impact.
"""

import time
from backend.gateway.context_extractor import SecurityContext
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult


class NoSecurityPolicy(BaseSecurityPolicy):
    """Permits every tool request without restriction."""

    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        start = time.perf_counter()
        return PolicyEvaluationResult(
            decision="ALLOW",
            risk_score=0,
            confidence=1.0,
            reason="NoSecurityPolicy: All tool requests are unconditionally permitted.",
            signals=["no_security_baseline"],
            policy_name="NoSecurityPolicy",
            latency_ms=(time.perf_counter() - start) * 1000.0,
            estimated_cost_usd=0.0
        )
