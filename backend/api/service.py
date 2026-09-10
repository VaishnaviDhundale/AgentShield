"""
Core Gateway & Service Container for AgentShield FastAPI Backend
"""

import asyncio
from typing import Dict, Any, Optional
from backend.sandbox.environment import SandboxEnvironment
from backend.sandbox.tools import SandboxToolExecutor
from backend.gateway.interceptor import AgentShieldGateway
from backend.gateway.human_approval import HumanApprovalRegistry
from backend.policy.base import BaseSecurityPolicy
from backend.policy.agentshield_policy import AgentShieldPolicy
from backend.policy.static_policy import StaticPermissionPolicy
from backend.policy.no_security import NoSecurityPolicy
from backend.policy.llm_judge import LLMJudgePolicy
from backend.policy.ablation_policy import AblatedAgentShieldPolicy
from backend.api.websocket_manager import ws_manager
from backend.database.db import get_engine, init_db


class AgentShieldService:
    """
    Singleton service container wiring the Gateway, Sandbox, Database, and WebSocket Broadcaster.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        init_db(db_url)
        self.env = SandboxEnvironment()
        self.sandbox = SandboxToolExecutor(environment=self.env)
        self.approval_registry = HumanApprovalRegistry(default_timeout_sec=30.0, db_url=db_url)
        self.default_policy = AgentShieldPolicy()
        
        # Gateway initialized with thread-safe async broadcaster hook
        self.gateway = AgentShieldGateway(
            policy=self.default_policy,
            sandbox_executor=self.sandbox,
            db_url=db_url,
            approval_registry=self.approval_registry,
            event_broadcaster=self._sync_broadcast_wrapper
        )

    def _sync_broadcast_wrapper(self, event: Dict[str, Any]) -> None:
        """Safely schedules async WebSocket broadcast from synchronous gateway calls."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast(event))
        except RuntimeError:
            pass

    def get_policy(self, name: str) -> BaseSecurityPolicy:
        """Instantiates or retrieves the requested security policy."""
        lowered = name.lower()
        if "nosecurity" in lowered or "none" in lowered:
            return NoSecurityPolicy()
        elif "static" in lowered:
            return StaticPermissionPolicy()
        elif "judge" in lowered or "llm" in lowered:
            return LLMJudgePolicy()
        elif "ablation" in lowered or "no_task_intent" in lowered:
            return AblatedAgentShieldPolicy(ablation_name="no_task_intent", disable_task_intent=True)
        elif "no_sensitivity" in lowered:
            return AblatedAgentShieldPolicy(ablation_name="no_resource_sensitivity", disable_resource_sensitivity=True)
        elif "no_history" in lowered:
            return AblatedAgentShieldPolicy(ablation_name="no_agent_history", disable_history=True)
        elif "no_tool_risk" in lowered:
            return AblatedAgentShieldPolicy(ablation_name="no_tool_risk", disable_tool_risk=True)
        else:
            return AgentShieldPolicy()


# Global service container
service = AgentShieldService()
