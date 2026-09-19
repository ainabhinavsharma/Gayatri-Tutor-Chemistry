"""
Core Adaptive Learning Engine module (Phase 4).
Provides evidence-driven mastery calculation, difficulty policy,
misconception tracking, spaced review scheduling, and concept selection.
"""
from core.learning.mastery import MasteryCalculator, MasteryWeights
from core.learning.policy import DifficultyPolicy, DifficultyDecision
from core.learning.misconceptions import (
    MisconceptionTracker,
    THERMODYNAMICS_MISCONCEPTIONS,
    INORGANIC_MISCONCEPTIONS,
    ALL_MISCONCEPTIONS,
)
from core.learning.selector import ConceptSelector, ConceptSelectionResult

__all__ = [
    "MasteryCalculator",
    "MasteryWeights",
    "DifficultyPolicy",
    "DifficultyDecision",
    "MisconceptionTracker",
    "THERMODYNAMICS_MISCONCEPTIONS",
    "INORGANIC_MISCONCEPTIONS",
    "ALL_MISCONCEPTIONS",
    "ConceptSelector",
    "ConceptSelectionResult",
]
