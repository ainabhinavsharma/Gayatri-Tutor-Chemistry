"""Gayatri AI — Explanation Policy (P6-T04).

Structures concept explanations:
1. Direct Explanation
2. Intuition / Analogy
3. Chemistry-specific Example
4. Worked Example (if needed)
5. Student Check Question
"""
from __future__ import annotations


class ExplanationPolicy:
    """Formats system directives for concept explanation turns."""

    @staticmethod
    def get_directive(topic: str, subtopic: str = "", scaffolding: str = "medium") -> str:
        return f"""[PEDAGOGICAL POLICY: EXPLANATION]
Topic: {topic} ({subtopic})
Scaffolding Level: {scaffolding}

Follow this structure for your response:
1. Direct Explanation: Clear NCERT-grounded definition.
2. Intuition / Analogy: Provide a relatable physical intuition or everyday analogy.
3. Chemistry Example: Give a specific chemical scenario or equation.
4. Check Understanding & Next Action: End with a single short question to apply the concept, AND offer a clear next action for the student (e.g. "Do you want to practice this, or move to the next topic?")."""
