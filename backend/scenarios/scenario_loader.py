"""
Scenario Dataset Loader and Validator for AgentShield Evaluation
"""

import json
from pathlib import Path
from typing import List, Optional

from backend.scenarios.models import ScenarioDataset, ScenarioItem


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"


class ScenarioLoader:
    """Loads and validates scenarios from JSON files."""

    @classmethod
    def load_dataset(cls, path: Optional[Path] = None) -> ScenarioDataset:
        """Loads and parses the dataset from file."""
        target_path = path or DEFAULT_DATASET_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Scenario dataset not found at {target_path}")

        raw_data = json.loads(target_path.read_text(encoding="utf-8"))
        return ScenarioDataset.model_validate(raw_data)

    @classmethod
    def get_scenarios(cls, category: Optional[str] = None, path: Optional[Path] = None) -> List[ScenarioItem]:
        """Returns filtered list of scenarios."""
        dataset = cls.load_dataset(path)
        if category:
            return [s for s in dataset.scenarios if s.category.lower() == category.lower()]
        return dataset.scenarios
