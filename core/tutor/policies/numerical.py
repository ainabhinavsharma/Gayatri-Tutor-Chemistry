"""Gayatri AI — Numerical Solver Policy (P6-T05).

Teaches numerical problem-solving method step-by-step:
Given -> Find -> Formula/Principle -> Substitution -> Calculation -> Unit Check -> Final Answer -> Concept Check
"""
from __future__ import annotations


class NumericalPolicy:
    """Formats system directives for numerical problem-solving turns."""

    @staticmethod
    def get_directive(scaffolding: str = "high") -> str:
        return """[PEDAGOGICAL POLICY: NUMERICAL SOLVER]
Guide the student through the problem using the following step-by-step structure:

1. Given: Clearly list all values given in the problem with their units (e.g. q = 400 J, w = -200 J).
2. Find: Clearly state what quantity needs to be calculated (e.g. delta U).
3. Formula / Principle: State the governing NCERT formula (e.g. delta U = q + w).
4. Substitution: Show the numerical values plugged into the formula step-by-step.
5. Calculation: Show the arithmetic working.
6. Unit Check: Verify unit consistency (e.g. Joules, kJ, K).
7. Final Answer: Highlight the final result with units.
8. Concept Check: Ask a brief follow-up question to verify understanding (e.g. "What would happen if the work was done ON the system instead?")."""
