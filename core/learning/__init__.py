"""
Core Adaptive Learning Engine module (Phase 4 & Phase 5).
Provides evidence-driven mastery calculation, difficulty policy,
misconception tracking, spaced review scheduling, concept selection,
and event stream filtering.
"""
from core.learning.events import LearningEventStream
from core.learning.mastery import MasteryCalculator, MasteryWeights
from core.learning.misconceptions import (
    ALL_MISCONCEPTIONS,
    INORGANIC_MISCONCEPTIONS,
    THERMODYNAMICS_MISCONCEPTIONS,
    MisconceptionTracker,
)
from core.learning.policy import DifficultyDecision, DifficultyPolicy
from core.learning.progress import ProgressService, get_status_label
from core.learning.scheduler import ReviewScheduleResult, SpacedReviewScheduler
from core.learning.selector import ConceptSelectionResult, ConceptSelector

__all__ = [
    "ALL_MISCONCEPTIONS",
    "INORGANIC_MISCONCEPTIONS",
    "THERMODYNAMICS_MISCONCEPTIONS",
    "ConceptSelectionResult",
    "ConceptSelector",
    "DifficultyDecision",
    "DifficultyPolicy",
    "LearningEventStream",
    "MasteryCalculator",
    "MasteryWeights",
    "MisconceptionTracker",
    "ProgressService",
    "ReviewScheduleResult",
    "SpacedReviewScheduler",
    "get_status_label",
]
