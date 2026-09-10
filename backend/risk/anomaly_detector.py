"""
Behavioral Anomaly and Step Drift Detector for AgentShield
"""

from typing import Tuple, List, Dict, Any
from backend.gateway.context_extractor import SecurityContext


class BehavioralAnomalyDetector:
    """Detects behavioral drift, sudden pivots, and anomaly patterns across agent history."""

    @classmethod
    def evaluate_history_drift(cls, context: SecurityContext) -> Tuple[int, List[str]]:
        """
        Analyzes the agent's action history to compute an anomaly drift score (0-100).
        """
        history = context.agent_history
        signals = []

        if not history:
            # First action in the session
            return 0, []

        is_sensitive = context.resource_sensitivity in ("CRITICAL", "HIGH")
        previous_tools = [h.get("tool") for h in history]

        # 1. Sudden Pivot to Critical Secret
        # If previous steps were normal coding/testing, and current step targets a critical secret
        if is_sensitive and all(t in ("read_file", "list_files", "run_tests") for t in previous_tools):
            # Check if any prior step touched a secret
            prior_targets = [str(h.get("parameters", {}).get("path", "")) for h in history]
            had_prior_secrets = any(".env" in p or "credential" in p for p in prior_targets)
            if not had_prior_secrets:
                signals.append("sudden_behavioral_pivot")
                signals.append("prompt_injection_drift_suspected")
                return 70, signals

        # 2. Repeated Block Anomaly
        recent_blocks = sum(1 for h in history if h.get("decision") == "BLOCK")
        if recent_blocks >= 2:
            signals.append("repeated_blocked_actions")
            return 80, signals

        # 3. High Action Count / Long Chain
        if len(history) > 6:
            signals.append("extended_execution_chain")
            return 30, signals

        return 0, []
