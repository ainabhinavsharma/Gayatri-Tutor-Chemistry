"""Gayatri AI — Chemistry Entity Normalization Engine (Phase 5).

Extracts and normalizes chemistry entities (elements, compounds, ions, formulas,
reactions, units, variables, laws, principles) across LaTeX, Unicode, plain text,
and IUPAC chemical notation.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# LaTeX and Math Symbol Mappings
LATEX_TO_UNICODE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\\Delta\s*([A-Za-z])"), r"Δ\1"),
    (re.compile(r"\\Delta"), "Δ"),
    (re.compile(r"\\rightarrow"), "→"),
    (re.compile(r"\\rightleftharpoons"), "⇌"),
    (re.compile(r"\^\s*\\circ"), "°"),
    (re.compile(r"\^\{([^}]+)\}"), r"^\1"),
    (re.compile(r"_\{([^}]+)\}"), r"_\1"),
    (re.compile(r"\\alpha"), "α"),
    (re.compile(r"\\beta"), "β"),
    (re.compile(r"\\gamma"), "γ"),
    (re.compile(r"\\pi"), "π"),
    (re.compile(r"\\sigma"), "σ"),
    (re.compile(r"\\mu"), "μ"),
]

# Unicode Subscript / Superscript Maps
SUPERSCRIPT_MAP = str.maketrans("0123456789+-=", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼")
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

# Common Chemistry Entity Regices
ELEMENT_REGEX = re.compile(r"\b(He|Li|Be|B|C|N|O|F|Ne|Na|Mg|Al|Si|P|S|Cl|Ar|K|Ca|Sc|Ti|V|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb|Sr|Y|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|In|Sn|Sb|Te|I|Xe|Cs|Ba|La|Ce|Pr|Nd|Pm|Sm|Eu|Gd|Tb|Dy|Ho|Er|Tm|Yb|Lu|Hf|Ta|W|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi|Po|At|Rn|Fr|Ra|Ac|Th|Pa|U)\b")
COMPOUND_REGEX = re.compile(r"\b([A-Z][a-z]?\d*){2,}\b")
ION_REGEX = re.compile(r"\b([A-Z][a-z]?\d*){1,3}([1-9]?[+\-])\b")
FORMULA_REGEX = re.compile(r"\b(ΔG|ΔH|ΔS|ΔU|q\s*\+\s*w|PΔV|PV\s*=\s*nRT|K_?c|K_?p|pH)\b", re.I)
UNIT_REGEX = re.compile(r"\b(J/mol|kJ/mol|J/K\s*mol|kJ/K\s*mol|\bJ\b|\bkJ\b|\batm\b|\bPa\b|\bkPa\b|\bL\b|\bmL\b|\bK\b|°C|mol/L|\bM\b)\b")


@dataclass
class ChemistryEntity:
    """Extracted normalized chemistry entity matching Section 5 of Master Plan."""
    raw_text: str
    normalized_text: str
    entity_type: str  # element, compound, ion, formula, reaction, unit, variable, law, principle, concept
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChemistryEntityNormalizer:
    """Normalizes chemical formulas, equations, units, and LaTeX notation into standard forms."""

    @classmethod
    def normalize_latex(cls, text: str) -> str:
        """Convert LaTeX math/chemistry representations to clean Unicode."""
        normalized = text
        for pattern, replacement in LATEX_TO_UNICODE:
            normalized = pattern.sub(replacement, normalized)
        return normalized.strip()

    @classmethod
    def format_chemical_formula(cls, formula: str) -> str:
        """Format plain formula (e.g. H2O -> H₂O, O2- -> O²⁻)."""
        clean = cls.normalize_latex(formula)
        # Convert trailing charge superscripts like 2- or +
        clean = re.sub(r"(\d*)([+\-])", lambda m: m.group(0).translate(SUPERSCRIPT_MAP), clean)
        # Convert numeric subscripts for elements
        clean = re.sub(r"([A-Za-z\)])(\d+)", lambda m: m.group(1) + m.group(2).translate(SUBSCRIPT_MAP), clean)
        return clean.strip()

    @classmethod
    def extract_entities(cls, text: str) -> list[ChemistryEntity]:
        """Extract and categorize chemistry entities from text."""
        normalized_source = cls.normalize_latex(text)
        entities: list[ChemistryEntity] = []

        # 1. Formulas & Expressions
        for m in FORMULA_REGEX.finditer(normalized_source):
            raw = m.group(0)
            entities.append(ChemistryEntity(raw_text=raw, normalized_text=cls.normalize_latex(raw), entity_type="formula"))

        # 2. Units
        for m in UNIT_REGEX.finditer(normalized_source):
            raw = m.group(0)
            entities.append(ChemistryEntity(raw_text=raw, normalized_text=raw, entity_type="unit"))

        # 3. Ions
        for m in ION_REGEX.finditer(normalized_source):
            raw = m.group(0)
            entities.append(ChemistryEntity(raw_text=raw, normalized_text=cls.format_chemical_formula(raw), entity_type="ion"))

        # 4. Compounds
        for m in COMPOUND_REGEX.finditer(normalized_source):
            raw = m.group(0)
            # Avoid duplicating formulas
            if not any(e.raw_text == raw for e in entities):
                entities.append(ChemistryEntity(raw_text=raw, normalized_text=cls.format_chemical_formula(raw), entity_type="compound"))

        # 5. Elements
        for m in ELEMENT_REGEX.finditer(normalized_source):
            raw = m.group(0)
            if not any(e.raw_text == raw for e in entities):
                entities.append(ChemistryEntity(raw_text=raw, normalized_text=raw, entity_type="element"))

        return entities
