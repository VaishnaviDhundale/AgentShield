"""
Base Security Policy Interface for AgentShield
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.gateway.context_extractor import SecurityContext


@dataclass
class PolicyEvaluationResult:
    """Standardized decision returned by any security policy."""
    decision: str  # ALLOW | BLOCK | ASK_HUMAN
    risk_score: int  # 0 to 100
    confidence: float  # 0.0 to 1.0
    reason: str
    signals: List[str] = field(default_factory=list)
    policy_name: str = "BasePolicy"
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class BaseSecurityPolicy(ABC):
    """Abstract interface for all authorization policies."""

    @abstractmethod
    async def evaluate(self, context: Any) -> PolicyEvaluationResult:
        """Evaluates the security context and returns an authorization decision."""
        pass
