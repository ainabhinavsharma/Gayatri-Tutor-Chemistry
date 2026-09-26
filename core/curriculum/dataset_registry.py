"""Gayatri AI — Dataset Topic Registry.

Maps topic_id strings used in the training dataset (e.g. 'first_law', 'hess's_law')
to their full CurriculumDomain context for use by TutorStateManager.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("gayatri.curriculum.dataset_registry")

# Authoritative mapping from training dataset topic_id → (domain_name, display_name)
# Derived from training/datasets/chemistry/train.jsonl metadata
DATASET_TOPIC_MAP: dict[str, dict] = {
    # Thermodynamics topics
    "first_law": {
        "domain": "Thermodynamics",
        "display_name": "First Law of Thermodynamics",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "heat_capacity": {
        "domain": "Thermodynamics",
        "display_name": "Heat Capacity",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "enthalpy_of_formation": {
        "domain": "Thermodynamics",
        "display_name": "Enthalpy of Formation",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "hess's_law": {
        "domain": "Thermodynamics",
        "display_name": "Hess's Law of Constant Heat Summation",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "gibbs_free_energy": {
        "domain": "Thermodynamics",
        "display_name": "Gibbs Free Energy and Equilibrium",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "thermodynamic_terms": {
        "domain": "Thermodynamics",
        "display_name": "Thermodynamic Terms and Concepts",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "spontaneity": {
        "domain": "Thermodynamics",
        "display_name": "Spontaneity and Entropy",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    "calorimetry": {
        "domain": "Thermodynamics",
        "display_name": "Calorimetry",
        "source_id": "NCERT_CH6",
        "class_level": "Class 11",
    },
    # Inorganic Chemistry topics
    "p-block_trends": {
        "domain": "Inorganic Chemistry",
        "display_name": "p-Block Elements Trends",
        "source_id": "NCERT_CH11",
        "class_level": "Class 11",
    },
    "coordination_compounds": {
        "domain": "Inorganic Chemistry",
        "display_name": "Coordination Compounds",
        "source_id": "NCERT_CH9",
        "class_level": "Class 12",
    },
    "s-block_reactivity": {
        "domain": "Inorganic Chemistry",
        "display_name": "s-Block Elements Reactivity",
        "source_id": "NCERT_CH10",
        "class_level": "Class 11",
    },
    "hydrogen_preparation": {
        "domain": "Inorganic Chemistry",
        "display_name": "Preparation of Hydrogen",
        "source_id": "NCERT_CH9",
        "class_level": "Class 11",
    },
    "d-block_oxidation_states": {
        "domain": "Inorganic Chemistry",
        "display_name": "d-Block Elements Oxidation States",
        "source_id": "NCERT_CH8",
        "class_level": "Class 12",
    },
    "s_block_elements": {
        "domain": "Inorganic Chemistry",
        "display_name": "s-Block Elements",
        "source_id": "NCERT_CH10",
        "class_level": "Class 11",
    },
}


@dataclass
class TopicInfo:
    topic_id: str
    domain: str
    display_name: str
    source_id: str
    class_level: str


class DatasetTopicRegistry:
    """Registry mapping training dataset topic_ids to curriculum metadata."""

    def __init__(self):
        self._map = DATASET_TOPIC_MAP

    def lookup(self, topic_id: str) -> TopicInfo | None:
        """Return TopicInfo for a topic_id, or None if unknown."""
        raw = self._map.get(topic_id)
        if not raw:
            return None
        return TopicInfo(
            topic_id=topic_id,
            domain=raw["domain"],
            display_name=raw["display_name"],
            source_id=raw["source_id"],
            class_level=raw["class_level"],
        )

    def all_topic_ids(self) -> list[str]:
        return list(self._map.keys())

    def topics_for_domain(self, domain: str) -> list[TopicInfo]:
        return [
            TopicInfo(topic_id=tid, **raw)
            for tid, raw in self._map.items()
            if raw["domain"].lower() == domain.lower()
        ]


_registry: DatasetTopicRegistry | None = None


def get_dataset_registry() -> DatasetTopicRegistry:
    global _registry
    if _registry is None:
        _registry = DatasetTopicRegistry()
    return _registry
