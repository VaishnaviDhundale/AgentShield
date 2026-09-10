"""
Deterministic Rule Layer for AgentShield

Clearly separates:
1. HARD SECURITY RULES (Unconditional BLOCK: Path traversal, dangerous shell commands, root deletion).
   Hard rules short-circuit before mathematical scoring and cannot be overridden by soft bonuses.
2. SOFT RISK ADJUSTMENTS (Additive modifiers to mathematical score based on structural heuristics).
"""

import re
from typing import Optional, List, Tuple
from backend.gateway.context_extractor import SecurityContext


class DeterministicRuleLayer:
    """Evaluates explicit deterministic security rules."""

    # Explicitly prohibited destructive shell commands
    DANGEROUS_COMMANDS = [
        r"rm\s+-rf\s+/", r"format\s+[a-z]:", r"shutdown", r"reboot",
        r"powershell\s+.*-enc", r"del\s+/s\s+/q\s+c:", r"mkfs", r":\(\)\s*\{"
    ]

    # Path traversal and jail escape patterns
    TRAVERSAL_PATTERNS = [
        r"\.\./", r"\.\.\\", r"^/etc/", r"^[a-zA-Z]:\\windows", r"^/root", r"\.\."
    ]

    @classmethod
    def evaluate_hard_rules(cls, context: SecurityContext) -> Optional[Tuple[str, int, str, List[str]]]:
        """
        Evaluates unconditional hard security boundaries.
        Returns (decision='BLOCK', risk_score=100, reason, signals) if triggered, else None.
        """
        target = str(context.target_resource).lower()
        tool = context.tool_name
        params = context.parameters

        # 1. Path Traversal Hard Violation
        for pat in cls.TRAVERSAL_PATTERNS:
            if re.search(pat, target) or any(re.search(pat, str(v)) for v in params.values() if isinstance(v, str)):
                return (
                    "BLOCK",
                    100,
                    "Hard Rule: Path traversal attempt detected outside sandbox boundary.",
                    ["hard_rule_violation", "path_traversal_attempt"]
                )

        # 2. Dangerous Shell Command Hard Violation
        if tool == "run_command":
            cmd = str(params.get("command", "")).lower()
            for pat in cls.DANGEROUS_COMMANDS:
                if re.search(pat, cmd):
                    return (
                        "BLOCK",
                        100,
                        f"Hard Rule: Prohibited destructive system command pattern '{cmd[:30]}'.",
                        ["hard_rule_violation", "dangerous_command_pattern"]
                    )

        # 3. Recursive Root Workspace Deletion Hard Violation
        if tool == "delete_file":
            path_val = str(params.get("path", "")).strip().rstrip("/\\")
            if path_val in (".", "project", "project/src", "", "/"):
                return (
                    "BLOCK",
                    100,
                    "Hard Rule: Destructive mass directory deletion of project root.",
                    ["hard_rule_violation", "recursive_root_deletion"]
                )

        return None

    @classmethod
    def compute_rule_adjustments(cls, context: SecurityContext) -> Tuple[int, List[str]]:
        """
        Computes soft additive modifiers for domain structural heuristics.
        """
        adjustment = 0
        signals = []
        target = str(context.target_resource).lower()
        tool = context.tool_name

        # Soft Bonus: Safe read of documentation or unit test files
        if tool in ("read_file", "list_files") and ("readme" in target or "tests/" in target or "docs/" in target):
            adjustment -= 15
            signals.append("safe_doc_test_resource")

        # Soft Penalty: Destructive SQL write operations
        if tool == "database_query":
            query = str(context.parameters.get("query", "")).upper()
            if any(k in query for k in ("DROP TABLE", "TRUNCATE", "DELETE FROM")):
                adjustment += 25
                signals.append("destructive_sql_operation")

        return adjustment, signals
