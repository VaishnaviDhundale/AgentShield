"""
Semantic Intent Evaluator for AgentShield

Calculates the Intent Mismatch Score (0 to 100) using generalized lexical and semantic
similarity between the declared Task Intent and the requested tool / target resource.
No hardcoded scenario strings or task-specific shortcuts.
"""

import re
from pathlib import Path
from typing import Tuple, List, Set
from backend.gateway.context_extractor import SecurityContext


class SemanticIntentEvaluator:
    """
    Evaluates generalized semantic relevance between task intent and tool actions.
    Extracts structural components (filename stem, target entity) and compares with intent tokens.
    """

    STOP_WORDS = {
        "the", "a", "an", "in", "to", "for", "of", "and", "or", "is", "on", "at",
        "by", "with", "this", "that", "from", "as", "it", "be", "are", "was", "were",
        "project", "src", "app", "lib"
    }

    # Direct synonym clusters
    SYNONYM_CLUSTERS = [
        {"rotate", "rotation", "key_rotation"},
        {"secret", "secrets", "api_key", "api_keys", "token", "tokens", "credential", "credentials", "env"},
        {"auth", "authentication", "login", "password", "authenticate", "session", "user"},
        {"database", "db", "sql", "sqlite", "users_db", "query", "users"},
        {"test", "tests", "pytest", "unit_test"},
        {"config", "configuration", "settings", "yaml", "toml"},
        {"delete", "remove", "clean", "cleanup", "purge"},
        {"doc", "docs", "documentation", "readme"}
    ]

    @classmethod
    def extract_clean_tokens(cls, text: str) -> Set[str]:
        """Extracts normalized alphanumeric tokens from text, excluding generic structural words."""
        normalized = re.sub(r"[^a-zA-Z0-9_]", " ", text.lower())
        raw_tokens = normalized.split()
        return {t for t in raw_tokens if t not in cls.STOP_WORDS and len(t) > 1}

    @classmethod
    def expand_with_clusters(cls, tokens: Set[str]) -> Set[str]:
        """Expands tokens with direct matching synonym cluster members."""
        expanded = set(tokens)
        for token in tokens:
            for cluster in cls.SYNONYM_CLUSTERS:
                if token in cluster:
                    expanded.update(cluster)
        return expanded

    @classmethod
    def calculate_semantic_similarity(cls, intent_text: str, resource_text: str) -> float:
        """
        Computes generalized semantic overlap similarity in [0.0, 1.0].
        Prioritizes base target entity matching over path prefixes.
        """
        intent_tokens = cls.extract_clean_tokens(intent_text)
        
        # Extract target resource tokens (e.g. from 'project/src/auth.py' -> {'auth', 'py'})
        resource_tokens = cls.extract_clean_tokens(resource_text)

        if not resource_tokens:
            return 0.5

        expanded_intent = cls.expand_with_clusters(intent_tokens)
        expanded_resource = cls.expand_with_clusters(resource_tokens)

        # Check intersection
        intersection = expanded_intent.intersection(expanded_resource)
        if not intersection:
            return 0.0

        # Primary overlap metric
        overlap_score = len(intersection) / len(resource_tokens)
        return min(1.0, max(0.85 if len(intersection) >= 1 and len(resource_tokens) <= 2 else overlap_score, overlap_score))

    @classmethod
    def evaluate_intent_mismatch(cls, context: SecurityContext) -> Tuple[int, List[str]]:
        """
        Computes the intent mismatch score M_intent in [0, 100].
        M_intent = 100 * (1.0 - Sim(Intent, Resource))
        """
        target = context.target_resource
        intent = context.task_intent
        signals = []

        similarity = cls.calculate_semantic_similarity(intent, target)
        mismatch_score = int(round(100.0 * (1.0 - similarity)))

        if similarity >= 0.60:
            signals.append("task_aligned")
            if context.resource_sensitivity in ("CRITICAL", "HIGH"):
                signals.append("legitimate_sensitive_intent")
        elif similarity <= 0.15:
            signals.append("task_mismatch")
            if context.resource_sensitivity == "CRITICAL":
                signals.append("unauthorized_secret_access")
            elif context.resource_sensitivity == "HIGH":
                signals.append("unauthorized_database_access")
        else:
            signals.append("partial_task_alignment")

        return mismatch_score, signals
