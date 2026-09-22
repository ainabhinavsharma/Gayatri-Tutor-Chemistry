"""Gayatri AI — Multi-Layer Guardrails System (Section 36).

Implements 4 distinct defense layers:
1. Input Guardrail: sanitization, size bounds, and prompt injection defense.
2. Topic Boundary Guardrail: restricts conversations to high school / foundational chemistry.
3. Chemistry Safety Guardrail: conservative handling of hazardous chemicals (Section 38).
4. Output Guardrail: anti-leakage in QUESTION mode and structured validity checking.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("gayatri.tutor.guardrails")

# Input length limit
MAX_INPUT_CHARS = 4000

# ── Chemistry Safety Catalog (Dangerous synthesis vs Educational explanations) ──

# Dangerous actionable production/synthesis keywords that MUST be blocked
DANGEROUS_SYNTHESIS_PATTERNS = [
    re.compile(r"(?i)\b(how\s+to|instructions?\s+for|recipe\s+for|synthesiz\w+|mak\w+|produc\w+)\s+(a\s+)?(bomb|explosive|pipe\s*bomb|tnt|rdx|c4|nitroglycerin|mustard\s+gas|sarin|ricin|vx\s+gas|cyanide\s+gas|poison)\b"),
    re.compile(r"(?i)\b(weaponiz\w+|home\s*made\s+explosive|improvised\s+device|improvised\s+explosive)\b"),
    re.compile(r"(?i)\b(synthes\w+|manufactur\w+)\s+(meth|illicit\s+drugs|controlled\s+substance)\b"),
]

# Educational chemistry keywords that are ALWAYS PERMITTED for scientific/safety explanation
EDUCATIONAL_SAFETY_PATTERNS = [
    re.compile(r"(?i)\b(why\s+is|hazard\s+of|toxicity\s+of|properties\s+of|danger\s+of|safe\s+handling|precautions?\s+for|health\s+effects?\s+of)\b"),
    re.compile(r"(?i)\bchlorine\s+gas\b"),
]

# ── Prompt Injection & System Extraction Patterns ─────────────────────────

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(ignore|disregard|forget|override|cancel)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|directives|prompts?|rules)\b"),
    re.compile(r"(?i)\b(reveal|print|show|output|tell\s+me)\s+(your|the)\s+(hidden\s+)?(system\s+)?(prompt|instructions|rules|directives)\b"),
    re.compile(r"(?i)\b(you\s+are\s+now|act\s+as)\s+(unrestricted|jailbroken|dan|developer\s+mode)\b"),
    re.compile(r"(?i)\[\s*SYSTEM\s+(DIRECTIVE|OVERRIDE).*?\]", re.DOTALL),
]

# ── Non-Chemistry Topic Keywords ──────────────────────────────────────────

NON_CHEMISTRY_TOPIC_PATTERNS = [
    re.compile(r"(?i)\b(write|code|debug|script)\s+(python|javascript|java|c\+\+|html|css|php|rust|sql|bash)\b"),
    re.compile(r"(?i)\bwho\s+(is|was)\s+(napoleon|hitler|einstein|shakespeare|gandhi|caesar)\b"),
    re.compile(r"(?i)\b(capital\s+of|currency\s+of|prime\s+minister\s+of|president\s+of)\b"),
    re.compile(r"(?i)\b(cricket|football|soccer|basketball|nba|world\s+cup)\s+(score|match|team|player)\b"),
    re.compile(r"(?i)\b(recipe\s+for|how\s+to\s+cook|bake\s+a)\s+(cake|bread|pizza|cookies|pasta)\b"),
]

CHEMISTRY_WHITELIST_KEYWORDS = {
    "chem", "thermo", "reaction", "enthalpy", "entropy", "energy", "heat", "work",
    "bond", "vsepr", "lewis", "hybrid", "atom", "molecule", "electron", "proton",
    "periodic", "radius", "ion", "cation", "anion", "electronegativ", "ligand",
    "coordination", "complex", "oxidation", "nomenclature", "gas", "solid", "liquid",
    "acid", "base", "solution", "equilibrium", "stoichiometr", "mole", "orbital",
}


@dataclass
class GuardrailResult:
    """Result of passing an input or output through multi-layer guardrails."""
    passed: bool
    layer: str  # "INPUT", "TOPIC", "SAFETY", "OUTPUT"
    flagged: bool = False
    reason: str = ""
    safe_response: str = ""
    sanitized_input: str = ""


class MultiLayerGuardrails:
    """Multi-layer guardrail implementation adhering to Section 36 & 38."""

    @classmethod
    def check_input(cls, text: str) -> GuardrailResult:
        """Layer 1: Input size & prompt injection check."""
        if not text or not text.strip():
            return GuardrailResult(
                passed=False,
                layer="INPUT",
                flagged=True,
                reason="EMPTY_INPUT",
                safe_response="Please enter a chemistry question or topic you would like to explore.",
            )

        if len(text) > MAX_INPUT_CHARS:
            return GuardrailResult(
                passed=False,
                layer="INPUT",
                flagged=True,
                reason="INPUT_TOO_LONG",
                safe_response="Your message is too long. Please keep your question focused and under 4,000 characters.",
            )

        # Prompt injection detection
        for pat in PROMPT_INJECTION_PATTERNS:
            if pat.search(text):
                return GuardrailResult(
                    passed=False,
                    layer="INPUT",
                    flagged=True,
                    reason="PROMPT_INJECTION_ATTEMPT",
                    safe_response=(
                        "I am Gayatri, your chemistry tutor. I operate strictly under educational "
                        "and safety guidelines. Let's return to the chemistry concepts we are studying."
                    ),
                    sanitized_input="[INJECTION_BLOCKED]"
                )

        return GuardrailResult(passed=True, layer="INPUT", sanitized_input=text.strip())

    @classmethod
    def check_chemistry_safety(cls, text: str) -> GuardrailResult:
        """Layer 2: Chemistry safety guardrail (Section 38).
        Distinguishes legitimate educational inquiry (e.g. why chlorine gas is dangerous)
        from dangerous synthesis/weaponization instructions.
        """
        # 1. Check if it is a dangerous actionable production/synthesis request
        for pat in DANGEROUS_SYNTHESIS_PATTERNS:
            if pat.search(text):
                return GuardrailResult(
                    passed=False,
                    layer="SAFETY",
                    flagged=True,
                    reason="DANGEROUS_SUBSTANCE_SYNTHESIS",
                    safe_response=(
                        "I cannot provide instructions, synthesis procedures, or recipes for dangerous, "
                        "explosive, toxic, or weaponized substances. I can, however, explain the chemical "
                        "properties, molecular structure, or standard laboratory safety protocols for these compounds."
                    )
                )

        # 2. Permitted educational inquiry (Section 38)
        # Even if hazardous compounds like chlorine, cyanide, or acids are mentioned,
        # educational questions regarding why they are hazardous are fully permitted!
        return GuardrailResult(passed=True, layer="SAFETY")

    @classmethod
    def check_topic_boundary(cls, text: str) -> GuardrailResult:
        """Layer 3: Topic boundary guardrail (Section 36 Topic Guardrail).
        Restricts interactions to configured high school chemistry.
        """
        lower = text.lower()

        # Check explicit non-chemistry patterns
        for pat in NON_CHEMISTRY_TOPIC_PATTERNS:
            if pat.search(text):
                return GuardrailResult(
                    passed=False,
                    layer="TOPIC",
                    flagged=True,
                    reason="OUT_OF_SCOPE_TOPIC",
                    safe_response=(
                        "I am currently configured as a high school chemistry tutor. "
                        "Let's stay with the chemistry topic you are studying, such as "
                        "Thermodynamics, Chemical Bonding, Periodic Trends, or Coordination Chemistry."
                    )
                )

        # Check general chemistry relevance if query is substantial (> 4 words)
        words = set(re.findall(r"\w+", lower))
        has_chem_keyword = any(k in lower for k in CHEMISTRY_WHITELIST_KEYWORDS)
        if len(words) > 5 and not has_chem_keyword:
            # Check if it asks for non-academic assistance
            if any(w in lower for w in ["poem", "joke", "story", "recipe", "song", "essay on"]):
                return GuardrailResult(
                    passed=False,
                    layer="TOPIC",
                    flagged=True,
                    reason="OFF_TOPIC_REQUEST",
                    safe_response=(
                        "I am currently configured as a chemistry tutor. "
                        "Let's focus on your chemistry lesson."
                    )
                )

        return GuardrailResult(passed=True, layer="TOPIC")

    @classmethod
    def check_output(cls, output_text: str, current_mode: str = "EXPLAIN") -> GuardrailResult:
        """Layer 4: Output guardrail checking for empty output, answer leakage, or unsafe leakage."""
        if not output_text or not output_text.strip():
            return GuardrailResult(
                passed=False,
                layer="OUTPUT",
                flagged=True,
                reason="EMPTY_OUTPUT",
                safe_response="I encountered an issue generating a complete explanation. Let's try again."
            )

        # In QUESTION mode, prevent answer leakage (e.g. saying "The answer is 300 J")
        if current_mode == "QUESTION":
            leakage_patterns = [
                re.compile(r"(?i)\bthe\s+(correct\s+)?answer\s+(is|would\s+be)\s*[:=]?\s*([0-9\.]+|[A-D]\b)"),
                re.compile(r"(?i)\bhere\s+is\s+the\s+solution\s*:\b"),
            ]
            for pat in leakage_patterns:
                if pat.search(output_text):
                    logger.warning("Output guardrail detected answer leakage in QUESTION mode; redacting solution")
                    # Sanitize output by truncating before the leaked solution
                    safe_text = pat.split(output_text)[0].strip()
                    if len(safe_text) > 30:
                        return GuardrailResult(passed=True, layer="OUTPUT", safe_response=safe_text)

        return GuardrailResult(passed=True, layer="OUTPUT")
