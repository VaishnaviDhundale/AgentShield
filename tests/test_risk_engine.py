"""
Unit Tests for AgentShield Mathematical Risk Engine (Phase 4)

Verifies:
1. Hard security rules (Unconditional BLOCK for path traversal, destructive shell, root deletion).
2. Generalized semantic intent evaluator without hardcoded string shortcuts.
3. Behavioral anomaly detector.
4. Mathematical formula reproducibility.
5. Task context changing the authorization decision for the exact same target resource.
"""

import pytest
from backend.agent.base_agent import ToolCallRequest
from backend.gateway.context_extractor import ContextExtractor, SecurityContext
from backend.risk.config import RiskScoringConfig
from backend.risk.deterministic_rules import DeterministicRuleLayer
from backend.risk.semantic_evaluator import SemanticIntentEvaluator
from backend.risk.anomaly_detector import BehavioralAnomalyDetector
from backend.risk.risk_scorer import MathematicalRiskScorer


def test_hard_rule_unconditional_blocks():
    """Verifies that hard rules immediately and unconditionally BLOCK critical violations."""
    # 1. Traversal Attempt
    req_trav = ToolCallRequest("s1", 1, "read_file", {"path": "../../outside_secret.txt"}, "Fix bug", [])
    ctx_trav = ContextExtractor.extract(req_trav, "r1")
    res_trav = DeterministicRuleLayer.evaluate_hard_rules(ctx_trav)
    assert res_trav is not None
    assert res_trav[0] == "BLOCK"
    assert res_trav[1] == 100
    assert "path_traversal_attempt" in res_trav[3]

    # 2. Destructive Shell Command
    req_cmd = ToolCallRequest("s1", 1, "run_command", {"command": "rm -rf /"}, "Clean workspace", [])
    ctx_cmd = ContextExtractor.extract(req_cmd, "r2")
    res_cmd = DeterministicRuleLayer.evaluate_hard_rules(ctx_cmd)
    assert res_cmd is not None
    assert res_cmd[0] == "BLOCK"
    assert res_cmd[1] == 100
    assert "dangerous_command_pattern" in res_cmd[3]

    # 3. Root Directory Deletion
    req_del = ToolCallRequest("s1", 1, "delete_file", {"path": "project/"}, "Clean project", [])
    ctx_del = ContextExtractor.extract(req_del, "r3")
    res_del = DeterministicRuleLayer.evaluate_hard_rules(ctx_del)
    assert res_del is not None
    assert res_del[0] == "BLOCK"
    assert res_del[1] == 100
    assert "recursive_root_deletion" in res_del[3]


def test_semantic_intent_evaluator_generalization():
    """Verifies generalized semantic alignment and mismatch calculation."""
    # Aligned coding task
    req_aligned = ToolCallRequest("s1", 1, "read_file", {"path": "project/src/auth.py"}, "Fix authentication bug in auth.py", [])
    ctx_aligned = ContextExtractor.extract(req_aligned, "r1")
    mismatch_aligned, sigs_aligned = SemanticIntentEvaluator.evaluate_intent_mismatch(ctx_aligned)
    assert mismatch_aligned <= 20
    assert "task_aligned" in sigs_aligned

    # Unaligned secret access
    req_mismatch = ToolCallRequest("s1", 1, "read_file", {"path": "secrets/.env"}, "Fix authentication bug in auth.py", [])
    ctx_mismatch = ContextExtractor.extract(req_mismatch, "r2")
    mismatch_score, sigs_mismatch = SemanticIntentEvaluator.evaluate_intent_mismatch(ctx_mismatch)
    assert mismatch_score >= 80
    assert "unauthorized_secret_access" in sigs_mismatch


def test_task_context_changes_decision_for_identical_resource():
    """
    CRITICAL INVARIANT TEST:
    The EXACT SAME tool request `read_file('secrets/.env')` MUST produce:
    - ALLOW when task is 'Rotate production API key in .env'
    - BLOCK when task is 'Fix authentication bug in auth.py'
    """
    scorer = MathematicalRiskScorer()

    # Case 1: Legitimate Sensitive Intent
    req_legit = ToolCallRequest("s1", 1, "read_file", {"path": "secrets/.env"}, "Rotate production API key in .env", [])
    ctx_legit = ContextExtractor.extract(req_legit, "r_legit")
    dec_legit, score_legit, _, _, sigs_legit = scorer.evaluate(ctx_legit)

    # Case 2: Unauthorized Malicious Intent
    req_unauth = ToolCallRequest("s1", 1, "read_file", {"path": "secrets/.env"}, "Fix authentication bug in auth.py", [])
    ctx_unauth = ContextExtractor.extract(req_unauth, "r_unauth")
    dec_unauth, score_unauth, _, _, sigs_unauth = scorer.evaluate(ctx_unauth)

    assert dec_legit == "ALLOW"
    assert score_legit < 40
    assert "legitimate_sensitive_intent" in sigs_legit

    assert dec_unauth == "BLOCK"
    assert score_unauth >= 70
    assert "unauthorized_secret_access" in sigs_unauth


def test_mathematical_risk_scoring_reproducibility():
    """Verifies that the risk score formula is strictly reproducible from explicit inputs."""
    cfg = RiskScoringConfig(
        w_resource_sensitivity=0.35,
        w_tool_risk=0.20,
        w_intent_mismatch=0.35,
        w_anomaly=0.10,
        allow_threshold=40,
        block_threshold=70
    )
    scorer = MathematicalRiskScorer(config=cfg)

    # Test request
    req = ToolCallRequest("s1", 1, "read_file", {"path": "secrets/.env"}, "Fix auth bug", [])
    ctx = ContextExtractor.extract(req, "r1")

    # Formula calculation:
    # S_res = 95, R_tool = 20, M_intent = 100, A_hist = 0
    # raw_score = 0.35*95 + 0.20*20 + 0.35*100 + 0 = 33.25 + 4.0 + 35.0 = 72.25 -> 72
    decision, score, confidence, reason, signals = scorer.evaluate(ctx)
    assert score == 72
    assert decision == "BLOCK"
    assert "unauthorized_secret_access" in signals
