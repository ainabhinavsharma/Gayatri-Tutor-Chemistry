"""Learning Event Stream and Evidence Filter (Phase 4).

Provides evidence filtering and stream analysis for learning events.
"""
from __future__ import annotations

from typing import List
from core.tutor.state import LearningEvent


class LearningEventStream:
    """Helper class for analyzing and filtering evidence event streams."""

    @staticmethod
    def filter_valid_events(events: List[LearningEvent]) -> List[LearningEvent]:
        """Filter out 'uncertain' events from mastery evidence calculation."""
        return [e for e in events if e.correctness != 'uncertain']

    @staticmethod
    def calculate_recent_accuracy(events: List[LearningEvent], n: int = 5) -> float:
        """Calculate accuracy over the last N valid events."""
        valid = LearningEventStream.filter_valid_events(events)
        if not valid:
            return 0.0
        recent = valid[-n:]
        scores = []
        for e in recent:
            if e.correctness == 'correct':
                scores.append(1.0)
            elif e.correctness == 'partially_correct':
                scores.append(0.5)
            else:
                scores.append(0.0)
        return sum(scores) / len(scores)

    @staticmethod
    def calculate_long_term_accuracy(events: List[LearningEvent]) -> float:
        """Calculate overall accuracy over all valid historical events."""
        valid = LearningEventStream.filter_valid_events(events)
        if not valid:
            return 0.0
        scores = []
        for e in valid:
            if e.correctness == 'correct':
                scores.append(1.0)
            elif e.correctness == 'partially_correct':
                scores.append(0.5)
            else:
                scores.append(0.0)
        return sum(scores) / len(scores)

    @staticmethod
    def get_independent_success_rate(events: List[LearningEvent]) -> float:
        """Calculate ratio of correct events completed without hints."""
        valid = LearningEventStream.filter_valid_events(events)
        correct_events = [e for e in valid if e.correctness == 'correct']
        if not correct_events:
            return 0.0
        independent_count = sum(1 for e in correct_events if e.hint_used == 0)
        return independent_count / len(correct_events)
