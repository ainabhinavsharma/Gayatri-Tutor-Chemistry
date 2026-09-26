"""Gayatri AI — Chemistry Computational Tools & Deterministic Balancer.

Provides exact, deterministic chemical calculations:
1. Chemical formula parsing (e.g. H2O -> {'H': 2, 'O': 1}, Fe2(SO4)3 -> {'Fe': 2, 'S': 3, 'O': 12}).
2. Stoichiometric equation balancing using nullspace linear algebra.
3. Verification of balanced reactions to prevent LLM arithmetic hallucinations.
"""
from __future__ import annotations

import logging
import math
import re
from fractions import Fraction

logger = logging.getLogger("gayatri.tutor.tools")


class FormulaParser:
    """Parses chemical formulas into element counts supporting parentheses and multipliers."""

    @staticmethod
    def parse_formula(formula: str) -> dict[str, int]:
        """Parse formula string into a dict of {element: count}.

        Example:
            'H2O' -> {'H': 2, 'O': 1}
            'Fe2(SO4)3' -> {'Fe': 2, 'S': 3, 'O': 12}
            'Ca(OH)2' -> {'Ca': 1, 'O': 2, 'H': 2}
        """
        formula = formula.strip().replace(" ", "")

        # Stack-based parser for handling parentheses
        stack: list[dict[str, int]] = [{}]
        i = 0
        n = len(formula)

        while i < n:
            ch = formula[i]

            if ch == "(":
                stack.append({})
                i += 1
            elif ch == ")":
                i += 1
                # Parse multiplier following ')'
                start_num = i
                while i < n and formula[i].isdigit():
                    i += 1
                mult = int(formula[start_num:i]) if i > start_num else 1

                top = stack.pop()
                for el, cnt in top.items():
                    stack[-1][el] = stack[-1].get(el, 0) + cnt * mult
            elif ch.isupper():
                # Parse element name (Upper + optional lower)
                start_el = i
                i += 1
                while i < n and formula[i].islower():
                    i += 1
                element = formula[start_el:i]

                # Parse count following element
                start_num = i
                while i < n and formula[i].isdigit():
                    i += 1
                count = int(formula[start_num:i]) if i > start_num else 1

                stack[-1][element] = stack[-1].get(element, 0) + count
            else:
                # Skip punctuation like state symbols (g), (s), (aq), (l) if present
                i += 1

        # Flatten remaining stack if unbalanced parens
        result: dict[str, int] = {}
        for layer in stack:
            for el, cnt in layer.items():
                result[el] = result.get(el, 0) + cnt

        return result


class ChemicalEquationBalancer:
    """Deterministic stoichiometric balancer for chemical equations."""

    @classmethod
    def parse_species(cls, species_str: str) -> tuple[int, str]:
        """Parse a chemical term like '2H2O' or 'O2' into (coefficient, formula)."""
        s = species_str.strip()
        match = re.match(r"^(\d+)\s*(.+)$", s)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return 1, s

    @classmethod
    def is_balanced(cls, equation: str) -> bool:
        """Check if an existing chemical equation string is stoichiometrically balanced."""
        arrow_match = re.search(r"\s*(?:->|-->|=|⇌|->)\s*", equation)
        if not arrow_match:
            return False

        left_side = equation[:arrow_match.start()]
        right_side = equation[arrow_match.end():]

        reactants = [r.strip() for r in left_side.split("+") if r.strip()]
        products = [p.strip() for p in right_side.split("+") if p.strip()]

        if not reactants or not products:
            return False

        left_counts: dict[str, int] = {}
        for term in reactants:
            coeff, formula = cls.parse_species(term)
            atoms = FormulaParser.parse_formula(formula)
            for el, cnt in atoms.items():
                left_counts[el] = left_counts.get(el, 0) + coeff * cnt

        right_counts: dict[str, int] = {}
        for term in products:
            coeff, formula = cls.parse_species(term)
            atoms = FormulaParser.parse_formula(formula)
            for el, cnt in atoms.items():
                right_counts[el] = right_counts.get(el, 0) + coeff * cnt

        return left_counts == right_counts

    @classmethod
    def balance(cls, equation: str) -> dict[str, object]:
        """Balance an unbalanced chemical equation into exact integer coefficients.

        Returns:
            Dict containing 'balanced_equation', 'reactants', 'products', 'coefficients'.
        """
        arrow_match = re.search(r"\s*(?:->|-->|=|⇌)\s*", equation)
        if not arrow_match:
            return {"success": False, "error": "Invalid equation syntax: missing reaction arrow."}

        left_side = equation[:arrow_match.start()]
        right_side = equation[arrow_match.end():]

        # Clean species names (strip existing coefficients)
        reactants = [cls.parse_species(r.strip())[1] for r in left_side.split("+") if r.strip()]
        products = [cls.parse_species(p.strip())[1] for p in right_side.split("+") if p.strip()]

        if not reactants or not products:
            return {"success": False, "error": "Missing reactants or products."}

        all_species = reactants + products
        num_reactants = len(reactants)
        num_species = len(all_species)

        # Parse formula for every species
        species_atoms = [FormulaParser.parse_formula(sp) for sp in all_species]

        # Collect all unique elements
        elements = sorted(list({el for atoms in species_atoms for el in atoms.keys()}))
        num_elements = len(elements)

        if not elements:
            return {"success": False, "error": "No elements found in reaction."}

        # Build stoichiometric matrix A: rows = elements, cols = species
        # Reactants have positive coefficients; products have negative coefficients
        matrix: list[list[Fraction]] = []
        for el in elements:
            row: list[Fraction] = []
            for j, atoms in enumerate(species_atoms):
                count = Fraction(atoms.get(el, 0))
                if j >= num_reactants:
                    count = -count
                row.append(count)
            matrix.append(row)

        # Solve nullspace of matrix A: A * c = 0 using Gaussian elimination
        # Augmented matrix of size num_elements x num_species
        M = [list(row) for row in matrix]
        r = 0
        lead_cols: list[int] = []

        for col in range(num_species):
            if r >= num_elements:
                break
            # Find pivot in this column
            pivot = -1
            for i in range(r, num_elements):
                if M[i][col] != 0:
                    pivot = i
                    break
            if pivot == -1:
                continue

            # Swap pivot to current row
            M[r], M[pivot] = M[pivot], M[r]
            pivot_val = M[r][col]

            # Normalize pivot row
            M[r] = [val / pivot_val for val in M[r]]

            # Eliminate in other rows
            for i in range(num_elements):
                if i != r and M[i][col] != 0:
                    factor = M[i][col]
                    M[i] = [M[i][k] - factor * M[r][k] for k in range(num_species)]

            lead_cols.append(col)
            r += 1

        # If system has free variables, choose the last species = 1 (or integer)
        free_cols = [c for c in range(num_species) if c not in lead_cols]
        if not free_cols:
            return {"success": False, "error": "Equation has no non-trivial solution."}

        # Solve for coefficients in terms of free variable (setting free var = 1)
        free_col = free_cols[-1]
        raw_coeffs = [Fraction(0)] * num_species
        raw_coeffs[free_col] = Fraction(1)

        for row_idx, lead_c in enumerate(lead_cols):
            raw_coeffs[lead_c] = -M[row_idx][free_col]

        # Check if all coefficients have the same sign (valid non-negative)
        all_pos = all(c > 0 for c in raw_coeffs)
        all_neg = all(c < 0 for c in raw_coeffs)
        if all_neg:
            raw_coeffs = [-c for c in raw_coeffs]
        elif not all_pos:
            return {"success": False, "error": "Could not find all-positive reaction coefficients."}

        # Find least common multiple of denominators to convert to integer
        lcm_denom = 1
        for c in raw_coeffs:
            lcm_denom = (lcm_denom * c.denominator) // math.gcd(lcm_denom, c.denominator)

        int_coeffs = [int(c * lcm_denom) for c in raw_coeffs]

        # Simplify by greatest common divisor of all coefficients
        common_gcd = int_coeffs[0]
        for c in int_coeffs[1:]:
            common_gcd = math.gcd(common_gcd, c)
        final_coeffs = [c // common_gcd for c in int_coeffs]

        # Format balanced string
        reactant_terms = []
        for coeff, sp in zip(final_coeffs[:num_reactants], reactants):
            prefix = f"{coeff}" if coeff > 1 else ""
            reactant_terms.append(f"{prefix}{sp}")

        product_terms = []
        for coeff, sp in zip(final_coeffs[num_reactants:], products):
            prefix = f"{coeff}" if coeff > 1 else ""
            product_terms.append(f"{prefix}{sp}")

        balanced_eq = f"{' + '.join(reactant_terms)} -> {' + '.join(product_terms)}"

        return {
            "success": True,
            "balanced_equation": balanced_eq,
            "coefficients": final_coeffs,
            "reactants": reactants,
            "products": products,
        }
