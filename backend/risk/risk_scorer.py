"""
Reproducible Mathematical Risk Scorer for AgentShield

Calculates composite risk scores deterministically from explicit signals,
configurable weights, and domain rules.
"""

from typing import Tuple, List, Optional
from backend.gateway.context_extractor import SecurityContext
from backend.risk.config import RiskScoringConfig
from backend.risk.deterministic_rules import DeterministicRuleLayer
from backend.risk.semantic_evaluator import SemanticIntentEvaluator
from backend.risk.anomaly_detector import BehavioralAnomalyDetector


class MathematicalRiskScorer:
    """Calculates risk score and resolves security decision."""

    def __init__(self, config: Optional[RiskScoringConfig] = None):
        self.config = config or RiskScoringConfig()

    def evaluate(self, context: SecurityContext) -> Tuple[str, int, float, str, List[str]]:
        """
        Evaluates the security context.
        Returns (decision, risk_score, confidence, reason, signals).
        """
        # 1. Check Deterministic Hard Rules
        hard_eval = DeterministicRuleLayer.evaluate_hard_rules(context)
        if hard_eval is not None:
            decision, score, reason, signals = hard_eval
            return decision, score, 1.0, reason, signals

        # 2. Extract Individual Explicit Signals
        s_res = context.sensitivity_score
        r_tool = context.action_risk

        m_intent, intent_signals = SemanticIntentEvaluator.evaluate_intent_mismatch(context)
        a_hist, hist_signals = BehavioralAnomalyDetector.evaluate_history_drift(context)
        b_rules, rule_signals = DeterministicRuleLayer.compute_rule_adjustments(context)

        # 3. Apply Configurable Weighted Formula
        raw_score = (
            self.config.w_resource_sensitivity * s_res +
            self.config.w_tool_risk * r_tool +
            self.config.w_intent_mismatch * m_intent +
            self.config.w_anomaly * a_hist +
            b_rules
        )
        risk_score = int(min(100, max(0, round(raw_score))))

        # Aggregate signals
        signals = list(dict.fromkeys(
            [f"sensitivity_{context.resource_sensitivity.lower()}"] +
            intent_signals +
            hist_signals +
            rule_signals
        ))

        # 4. Determine Confidence
        # Higher confidence when multiple independent signals agree
        confidence = round(min(0.99, 0.80 + 0.05 * len(signals)), 2)

        # 5. Resolve Decision via Configurable Thresholds
        if risk_score > self.config.block_threshold:
            decision = "BLOCK"
            if "unauthorized_secret_access" in signals:
                reason = "Agent requested access to a critical secret unrelated to the current task."
            elif "unauthorized_database_access" in signals:
                reason = "Unauthorized database query outside task scope."
            else:
                reason = f"Action risk ({risk_score}/100) exceeds safety threshold ({self.config.block_threshold})."
        elif risk_score >= self.config.allow_threshold:
            decision = "ASK_HUMAN"
            reason = f"Action requires human verification (Risk: {risk_score}/100). Potential configuration or system modification."
        else:
            decision = "ALLOW"
            reason = f"Action is task-aligned and within safe operational limits (Risk: {risk_score}/100)."

        return decision, risk_score, confidence, reason, signals
