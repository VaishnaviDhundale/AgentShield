"""
Ablation Testing Policies for Scientific Evaluation

Enables disabling specific contextual signals to isolate their individual contribution:
- Full AgentShield (All signals enabled)
- No Task Intent (w_intent_mismatch = 0.0)
- No Resource Sensitivity (w_resource_sensitivity = 0.0)
- No Agent History (w_anomaly = 0.0)
- No Tool Risk (w_tool_risk = 0.0)
- No Context (All contextual weights = 0.0)
"""

import time
from typing import Optional

from backend.gateway.context_extractor import SecurityContext
from backend.policy.base import BaseSecurityPolicy, PolicyEvaluationResult
from backend.risk.config import RiskScoringConfig
from backend.risk.risk_scorer import MathematicalRiskScorer


class AblatedAgentShieldPolicy(BaseSecurityPolicy):
    """
    Configurable ablation policy variant of AgentShield.
    Explicitly removes target signal weights from the scoring formula.
    """

    def __init__(
        self,
        ablation_name: str = "custom",
        disable_task_intent: bool = False,
        disable_resource_sensitivity: bool = False,
        disable_history: bool = False,
        disable_tool_risk: bool = False,
        disable_all_context: bool = False
    ):
        self.ablation_name = ablation_name
        self.config = RiskScoringConfig()

        if disable_all_context:
            self.config.w_resource_sensitivity = 0.0
            self.config.w_tool_risk = 0.0
            self.config.w_intent_mismatch = 0.0
            self.config.w_anomaly = 0.0
            self.ablation_name = "no_context"
        else:
            if disable_task_intent:
                self.config.w_intent_mismatch = 0.0
                if self.ablation_name == "custom":
                    self.ablation_name = "no_task_intent"
            if disable_resource_sensitivity:
                self.config.w_resource_sensitivity = 0.0
                if self.ablation_name == "custom":
                    self.ablation_name = "no_resource_sensitivity"
            if disable_history:
                self.config.w_anomaly = 0.0
                if self.ablation_name == "custom":
                    self.ablation_name = "no_agent_history"
            if disable_tool_risk:
                self.config.w_tool_risk = 0.0
                if self.ablation_name == "custom":
                    self.ablation_name = "no_tool_risk"

        self.scorer = MathematicalRiskScorer(config=self.config)

    @classmethod
    def create_ablation_suite(cls) -> list["AblatedAgentShieldPolicy"]:
        """Returns the complete standardized ablation suite."""
        return [
            cls(ablation_name="no_task_intent", disable_task_intent=True),
            cls(ablation_name="no_resource_sensitivity", disable_resource_sensitivity=True),
            cls(ablation_name="no_agent_history", disable_history=True),
            cls(ablation_name="no_tool_risk", disable_tool_risk=True),
            cls(ablation_name="no_context", disable_all_context=True)
        ]

    async def evaluate(self, context: SecurityContext) -> PolicyEvaluationResult:
        start_time = time.perf_counter()
        decision, risk_score, confidence, reason, signals = self.scorer.evaluate(context)
        latency = (time.perf_counter() - start_time) * 1000.0

        return PolicyEvaluationResult(
            decision=decision,
            risk_score=risk_score,
            confidence=confidence,
            reason=f"[Ablation: {self.ablation_name}] {reason}",
            signals=[f"ablation_{self.ablation_name}"] + signals,
            policy_name=f"AgentShield_{self.ablation_name}",
            latency_ms=latency,
            estimated_cost_usd=0.0
        )
