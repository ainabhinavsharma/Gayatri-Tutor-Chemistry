"""Gayatri AI — Reaction Tutoring Policy (P6-T06).

Guides chemical reaction tutoring:
Reactants/Products -> Equation Balancing -> Reaction Conditions -> Stepwise Correction
"""
from __future__ import annotations


class ReactionPolicy:
    """Formats system directives for chemical reaction tutoring turns."""

    @staticmethod
    def get_directive() -> str:
        return """[PEDAGOGICAL POLICY: REACTION TUTORING]
Follow this chemical reaction tutoring procedure:

1. Reactants & Products: Identify and write out the states of reactants and products.
2. Equation Balancing: Guide the student to balance atoms on both sides (left vs right count).
3. Reaction Conditions: Specify necessary temperature, pressure, or catalysts if applicable.
4. Error Correction: If the student wrote an unbalanced or incorrect reaction, pinpoint the exact atom imbalance gently without dumping the direct answer.
5. Verification & Next Action: Ask the student to verify the atom balance, AND offer a clear next action (e.g. "Shall we try balancing another equation, or move on?")."""
