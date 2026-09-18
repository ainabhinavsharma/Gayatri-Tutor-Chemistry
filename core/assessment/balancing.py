"""Gayatri AI — Deterministic Chemical Equation Balancing Engine.

Parses chemical formulas and verifies atom count balance on both sides of a reaction.
Ex: '2 Na + 2 H2O -> 2 NaOH + H2'
"""
from __future__ import annotations

import logging
import re
from collections import Counter

logger = logging.getLogger("gayatri.assessment.balancing")


def _parse_formula(formula: str) -> Counter:
    """Parse a single chemical formula string into a Counter of element -> count.
    Ex: '2 H2O' -> Counter({'H': 4, 'O': 2})
    """
    formula = formula.strip()
    if not formula:
        return Counter()

    # Extract leading coefficient
    match_coeff = re.match(r"^(\d+)\s*(.*)$", formula)
    if match_coeff:
        coeff = int(match_coeff.group(1))
        body = match_coeff.group(2)
    else:
        coeff = 1
        body = formula

    element_counts = Counter()
    # Match element symbols (e.g. Na, H, O, Ca, Cl) and subscripts
    pattern = re.compile(r"([A-Z][a-z]*)(\d*)")
    matches = pattern.findall(body)

    for elem, sub in matches:
        count = int(sub) if sub else 1
        element_counts[elem] += count * coeff

    return element_counts


def _parse_side(side_str: str) -> Counter:
    """Parse one side of a chemical equation (reactants or products).
    Ex: '2 Na + 2 H2O' -> Counter({'Na': 2, 'H': 4, 'O': 2})
    """
    compounds = side_str.split("+")
    total = Counter()
    for c in compounds:
        total.update(_parse_formula(c))
    return total


class EquationBalancingEngine:
    """Deterministic verifier for chemical equation atom balance."""

    @staticmethod
    def verify_balance(equation: str) -> tuple[bool, str]:
        """Verify if a chemical equation is atom-balanced.
        Returns (is_balanced, explanation_message).
        """
        if "->" not in equation and "=" not in equation:
            return False, "Equation must contain '->' or '='"

        delim = "->" if "->" in equation else "="
        left_str, right_str = equation.split(delim, 1)

        left_atoms = _parse_side(left_str)
        right_atoms = _parse_side(right_str)

        if not left_atoms or not right_atoms:
            return False, "Invalid equation format"

        all_elements = set(left_atoms.keys()) | set(right_atoms.keys())
        imbalances = []

        for elem in sorted(all_elements):
            l_cnt = left_atoms[elem]
            r_cnt = right_atoms[elem]
            if l_cnt != r_cnt:
                imbalances.append(f"{elem}: left={l_cnt}, right={r_cnt}")

        if not imbalances:
            return True, "Equation is perfectly balanced!"
        else:
            return False, f"Imbalanced elements: {', '.join(imbalances)}"
