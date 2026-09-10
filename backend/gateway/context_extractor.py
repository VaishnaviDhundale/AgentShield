"""
Security Context Extractor for AgentShield Gateway

Extracts target resources, classifies resource sensitivity, and computes baseline
action risk from incoming tool requests.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from backend.agent.base_agent import ToolCallRequest


@dataclass
class SecurityContext:
    """Standardized security context passed to the Policy and Risk Engines."""
    request_id: str
    session_id: str
    step_number: int
    tool_name: str
    target_resource: str
    resource_sensitivity: str  # LOW | MEDIUM | HIGH | CRITICAL
    sensitivity_score: int     # 0 to 100
    action_risk: int           # 0 to 100
    task_intent: str
    parameters: Dict[str, Any]
    agent_history: List[Dict[str, Any]]
    raw_request: ToolCallRequest


class ContextExtractor:
    """Extracts security context from tool requests."""

    # Resource Sensitivity Match Patterns
    CRITICAL_PATTERNS = [
        r"\.env", r"credentials\.json", r"api_keys\.txt", r"id_rsa",
        r"\.pem$", r"\.key$", r"password", r"secret"
    ]
    HIGH_PATTERNS = [
        r"users\.db", r"fake_users\.db", r"database/.*\.db", r"prod",
        r"internal\.admin", r"/etc/passwd", r"/etc/shadow"
    ]
    MEDIUM_PATTERNS = [
        r"auth\.py", r"database\.py", r"main\.py", r"settings\.py",
        r"config\.(yaml|json|toml)", r"Dockerfile", r"requirements\.txt"
    ]
    LOW_PATTERNS = [
        r"README\.md", r"tests/.*", r"output/.*", r"\.log$", r"\.txt$", r"docs/.*"
    ]

    # Baseline Action Risk mapping (0-100)
    ACTION_RISK_MAP = {
        "list_files": 10,
        "read_file": 20,
        "git_operation": 30,
        "run_tests": 35,
        "write_file": 50,
        "database_query": 65,
        "http_request": 70,
        "run_command": 80,
        "delete_file": 85,
    }

    @classmethod
    def extract_target_resource(cls, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Determines the primary target resource from parameters."""
        if tool_name in ("read_file", "write_file", "delete_file"):
            return str(parameters.get("path", "")).strip()
        elif tool_name == "list_files":
            return str(parameters.get("directory", ".")).strip()
        elif tool_name == "run_tests":
            return str(parameters.get("test_target", "tests")).strip()
        elif tool_name == "database_query":
            query = str(parameters.get("query", "")).strip()
            # Extract table name if present
            match = re.search(r"(?:FROM|INTO|UPDATE|TABLE)\s+([a-zA-Z0-9_]+)", query, re.IGNORECASE)
            table = match.group(1) if match else "database"
            return f"database:{table}"
        elif tool_name == "http_request":
            return str(parameters.get("url", "")).strip()
        elif tool_name == "run_command":
            cmd = str(parameters.get("command", "")).strip()
            return f"command:{cmd[:40]}"
        elif tool_name == "git_operation":
            subcmd = str(parameters.get("subcommand", "status")).strip()
            return f"git:{subcmd}"
        return "unspecified_resource"

    @classmethod
    def classify_resource_sensitivity(cls, target_resource: str) -> tuple[str, int]:
        """Classifies sensitivity string (LOW, MEDIUM, HIGH, CRITICAL) and numeric score."""
        res_str = target_resource.lower()

        for pat in cls.CRITICAL_PATTERNS:
            if re.search(pat, res_str, re.IGNORECASE):
                return "CRITICAL", 95

        for pat in cls.HIGH_PATTERNS:
            if re.search(pat, res_str, re.IGNORECASE):
                return "HIGH", 70

        for pat in cls.MEDIUM_PATTERNS:
            if re.search(pat, res_str, re.IGNORECASE):
                return "MEDIUM", 40

        for pat in cls.LOW_PATTERNS:
            if re.search(pat, res_str, re.IGNORECASE):
                return "LOW", 10

        # Default classification
        return "LOW", 15

    @classmethod
    def extract(cls, request: ToolCallRequest, request_id: str) -> SecurityContext:
        """Transforms a ToolCallRequest into a full SecurityContext."""
        target_res = cls.extract_target_resource(request.tool_name, request.parameters)
        sensitivity_label, sensitivity_score = cls.classify_resource_sensitivity(target_res)
        action_risk = cls.ACTION_RISK_MAP.get(request.tool_name, 50)

        return SecurityContext(
            request_id=request_id,
            session_id=request.session_id,
            step_number=request.step_number,
            tool_name=request.tool_name,
            target_resource=target_res,
            resource_sensitivity=sensitivity_label,
            sensitivity_score=sensitivity_score,
            action_risk=action_risk,
            task_intent=request.task_intent,
            parameters=request.parameters,
            agent_history=request.agent_history,
            raw_request=request
        )
