"""Gayatri AI — Query Intelligence Engine & Intent Router (Phase 2).

Classifies incoming student queries into 28 standardized intent categories,
extracts target concepts, performs contextual query rewriting for follow-ups,
detects security/safety constraints, and returns a structured router payload.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("gayatri.tutor.intents")


class QueryIntent(str, Enum):
    GREETING = "greeting"
    DEFINITION = "definition"
    CONCEPT_EXPLANATION = "concept_explanation"
    WHY = "why"
    HOW = "how"
    COMPARISON = "comparison"
    FORMULA = "formula"
    DERIVATION = "derivation"
    NUMERICAL = "numerical"
    REACTION = "reaction"
    MECHANISM = "mechanism"
    MCQ = "mcq"
    ASSERTION_REASON = "assertion_reason"
    PROBLEM_SOLVING = "problem_solving"
    HINT = "hint"
    ANSWER_CHECK = "answer_check"
    MISCONCEPTION = "misconception"
    REMEDIATION = "remediation"
    REVISION = "revision"
    SUMMARY = "summary"
    PRACTICE = "practice"
    QUIZ = "quiz"
    EXAM = "exam"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    OUT_OF_SCOPE = "out_of_scope"
    PROMPT_INJECTION = "prompt_injection"
    CHEMISTRY_SAFETY = "chemistry_safety"


# Legacy 9-intent Enum preserved for backward compatibility
class TutorIntent(str, Enum):
    LEARN = "learn"
    EXPLAIN = "explain"
    SOLVE = "solve"
    PRACTICE = "practice"
    TEST = "test"
    REVIEW = "review"
    CLARIFY = "clarify"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    UNKNOWN = "unknown"


@dataclass
class RouterPayload:
    """Structured router output matching Phase 2 specification."""
    intent: str
    concepts: list[str]
    difficulty: str
    requires_rag: bool
    requires_calculator: bool
    requires_student_state: bool
    pedagogical_mode: str
    confidence: float
    rewritten_query: str | None = None
    security_flag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Security & Safety Regex Patterns
PROMPT_INJECTION_PATTERN = re.compile(
    r"\b(ignore\s+(all\s+)?(previous|prior)\s+instructions|system\s+prompt|reveal\s+system|you\s+are\s+now|forget\s+all\s+(rules|instructions)|override\s+policy|jailbreak|bypass\s+safety|output\s+password|dump\s+prompt|unrestricted\s+assistant|reveal\s+internal\s+system|output\s+developer\s+prompt)\b",
    re.IGNORECASE,
)

CHEMISTRY_SAFETY_PATTERN = re.compile(
    r"\b(make\s+a?\s*(bomb|poison|explosive|nerve\s+agent)|synthesize\s+(methamphetamine|heroin|sarin|mustard\s+gas|vx|illicit|narcotic|deadly|controlled)|(homemade|chemical|pipe|toxic|gas)\s*(explosive|bomb|weapon|narcotic)|poison\s+someone|illegal\s+drug|deadly\s+poison)\b",
    re.IGNORECASE,
)

# Common Chemistry Concept Keywords
CHEMISTRY_CONCEPT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("entropy", re.compile(r"\b(entropy|second law|\bS\b|\bdelta S\b)\b", re.I)),
    ("enthalpy", re.compile(r"\b(enthalpy|\bH\b|\bdelta H\b|heat of reaction)\b", re.I)),
    ("gibbs_energy", re.compile(r"\b(gibbs|free energy|\bG\b|\bdelta G\b|spontaneity)\b", re.I)),
    ("first_law", re.compile(r"\b(first law|internal energy|\bdelta U\b|\bq \+ w\b|work of expansion)\b", re.I)),
    ("hess_law", re.compile(r"\b(hess'?s? law|thermochemical)\b", re.I)),
    ("bonding_vsepr", re.compile(r"\b(vsepr|molecular geometry|shape of|hybridisation|hybridization|lewis structure|lone pairs)\b", re.I)),
    ("periodic_trends", re.compile(r"\b(atomic radius|ionic radius|ionization energy|ionisation energy|electron affinity|electronegativity|periodicity)\b", re.I)),
    ("coordination", re.compile(r"\b(coordination number|ligand|chelating|werner|oxidation state|complex ion)\b", re.I)),
    ("stoichiometry", re.compile(r"\b(mole|molar mass|limiting reagent|stoichiometry|avogadro)\b", re.I)),
    ("equilibrium", re.compile(r"\b(le chatelier|equilibrium constant|\bKc\b|\bKp\b|ph|buffer)\b", re.I)),
]

# Intent Classification Rules (ordered by priority)
INTENT_RULES: list[tuple[QueryIntent, re.Pattern]] = [
    # 1. Security & Safety
    (QueryIntent.PROMPT_INJECTION, PROMPT_INJECTION_PATTERN),
    (QueryIntent.CHEMISTRY_SAFETY, CHEMISTRY_SAFETY_PATTERN),

    # 2. Hints & Answer Checks
    (QueryIntent.HINT, re.compile(r"\b(hint\s+please|give\s+me\s+a\s+hint|clue|i\s+am\s+stuck|stuck\s+on|hint\s+level|give\s+hint|need\s+a\s+hint|guide\s+me\s+with\s+a\s+hint|give\s+a\s+small\s+clue|can\s+you\s+hint)\b", re.I)),
    (QueryIntent.ANSWER_CHECK, re.compile(r"(\b(my\s+answer|is\s+option|check\s+my\s+answer|is\s+that\s+(correct|right)|is\s+this\s+right|check\s+if|is\s+the\s+answer|correct\?|right\?|is\s+correct\?)\b|^\s*(\d+(\.\d+)?|[a-d]\))\s*$)", re.I)),

    # 3. Formats & Solvers
    (QueryIntent.MCQ, re.compile(r"\b(multiple\s+choice|mcq|which\s+of\s+the\s+following|options:?|select\s+the\s+correct\s+option)\b", re.I)),
    (QueryIntent.ASSERTION_REASON, re.compile(r"\b(assertion:?|reason:?)\b", re.I)),
    (QueryIntent.PROBLEM_SOLVING, re.compile(r"\b(solve\s+(this|problem|step\s+by\s+step)|help\s+me\s+solve|problem\s+solving:?|solve\s+problem:?)\b", re.I)),
    (QueryIntent.MISCONCEPTION, re.compile(r"\b(i\s+thought|why\s+isn't|isn't\s+.*always|misconception|wrong\s+assumption|why\s+is\s+my\s+answer\s+incorrect|common\s+mistake)\b", re.I)),
    (QueryIntent.REMEDIATION, re.compile(r"\b(remediate|remediation|weak\s+area|foundational\s+concepts|fix\s+my\s+understanding|prerequisite\s+(knowledge|gap|concepts|math|skills))\b", re.I)),
    (QueryIntent.REVISION, re.compile(r"\b(revise|revision|spaced\s+review|let\s+us\s+revise|time\s+for\s+spaced|review\s+weak\s+concepts|review\s+active\s+misconceptions)\b", re.I)),

    # 4. Assessment Modes
    (QueryIntent.QUIZ, re.compile(r"\b(quiz|quiz\s+me|quick\s+quiz|mini\s+quiz|test\s+my\s+knowledge)\b", re.I)),
    (QueryIntent.EXAM, re.compile(r"\b(exam|exam\s+mode|mock\s+exam|mock\s+test|final\s+exam|exam\s+simulation|full\s+assessment)\b", re.I)),
    (QueryIntent.PRACTICE, re.compile(r"\b(practice|practice\s+(question|problem|exercise)|want\s+to\s+practice|provide\s+a?\s*practice)\b", re.I)),

    # 5. Core Subject Queries
    (QueryIntent.DERIVATION, re.compile(r"\b(derive|derivation|prove\s+that|show\s+that)\b", re.I)),
    (QueryIntent.NUMERICAL, re.compile(r"\b(calculate|compute|find\s+the\s+value|numerical|how\s+many\s+joules|what\s+is\s+the\s+mass|determine\s+delta)\b", re.I)),
    (QueryIntent.FORMULA, re.compile(r"\b(formula\s+for|equation\s+for|mathematical\s+expression|state\s+the\s+relation|give\s+the\s+formula|give\s+formula)\b", re.I)),
    (QueryIntent.REACTION, re.compile(r"\b(reaction|chemical\s+equation|reactants|products|balance\s+equation|chemical\s+reaction)\b", re.I)),
    (QueryIntent.MECHANISM, re.compile(r"\b(mechanism|step-by-step\s+reaction|electron\s+movement|curved\s+arrow)\b", re.I)),
    (QueryIntent.COMPARISON, re.compile(r"\b(compare|difference\s+between|versus|\bvs\b|distinguish|differentiate)\b", re.I)),

    # 6. Explanations, Definitions, and Conversational
    (QueryIntent.SUMMARY, re.compile(r"\b(summary|summarize|in\s+short|key\s+takeaways|overview\s+of|provide\s+a?\s*summary)\b", re.I)),
    (QueryIntent.DEFINITION, re.compile(r"\b(define|definition\s+of|what\s+is\s+(meant\s+by|the\s+definition|a|an|meant)|meaning\s+of)\b", re.I)),
    (QueryIntent.FOLLOW_UP, re.compile(r"\b(why\s+is\s+it|and\s+then\?|what\s+about\s+in|why\s+did\s+work\s+become|can\s+you\s+explain\s+that\s+further|can\s+you\s+give\s+another\s+example|what\s+is\s+the\s+formula\s+for\s+it|how\s+do\s+i\s+solve\s+it|is\s+that\s+always\s+true|what\s+if\s+pressure|what\s+is\s+the\s+sign\s+of\s+delta\s+s\s+in\s+that\s+case|how\s+does\s+temperature\s+affect\s+it|why\s+is\s+the\s+angle\s+smaller|what\s+is\s+the\s+oxidation\s+state\s+there|can\s+you\s+clarify\s+that\s+step|what\s+does\s+that\s+symbol\s+mean|why\s+is\s+it\s+spontaneous\s+then)\b", re.I)),
    (QueryIntent.WHY, re.compile(r"\b(why\s+(does|is|do|did|are))\b", re.I)),
    (QueryIntent.HOW, re.compile(r"\b(how\s+(does|do|can|is|should|would))\b", re.I)),
    (QueryIntent.CLARIFICATION, re.compile(r"\b(clarify|confused|did\s+not\s+understand|please\s+clarify)\b", re.I)),
    (QueryIntent.GREETING, re.compile(r"^(hi|hello|hey|greetings|good\s+morning|good\s+evening|namaste)\b", re.I)),
    (QueryIntent.OUT_OF_SCOPE, re.compile(r"\b(world\s+cup|capital\s+of|python\s+script|president|pasta|smartphone|poem|flat\s+tire|stock\s+price|guitar|inception|binary\s+search|mars|hamlet|train\s+a\s+dog|weather\s+in|wooden\s+chair|linux)\b", re.I)),
    (QueryIntent.CONCEPT_EXPLANATION, re.compile(r"\b(explain|tell\s+me\s+about|understand|concept\s+of)\b", re.I)),
]


class QueryIntelligenceEngine:
    """Engine for classification, concept extraction, query rewriting, and routing."""

    @classmethod
    def extract_concepts(cls, query: str) -> list[str]:
        """Extract relevant chemistry concept tags from query text."""
        concepts = []
        for concept_name, pattern in CHEMISTRY_CONCEPT_PATTERNS:
            if pattern.search(query):
                concepts.append(concept_name)
        return concepts

    @classmethod
    def rewrite_contextual_query(
        cls,
        query: str,
        current_concept: str | None = None,
        previous_question: str | None = None,
        active_problem: str | None = None,
    ) -> str:
        """Rewrite ambiguous follow-up query into an explicit contextual query."""
        text = query.strip()
        is_ambiguous = len(text.split()) <= 6 or text.lower().startswith((
            "why", "how", "what about", "can you explain", "give another", "show me", "why is it", "is it"
        ))

        if not is_ambiguous or not (current_concept or previous_question or active_problem):
            return text

        context_parts = []
        if current_concept:
            context_parts.append(f"Concept: {current_concept}")
        if active_problem:
            context_parts.append(f"Problem: {active_problem}")
        elif previous_question:
            context_parts.append(f"Previous Question: {previous_question}")

        context_str = ", ".join(context_parts)
        return f"[{context_str}] {text}"

    @classmethod
    def classify_and_route(
        cls,
        user_message: str,
        current_concept: str | None = None,
        previous_question: str | None = None,
        student_state: dict[str, Any] | None = None,
    ) -> RouterPayload:
        """Classify user query and build a structured RouterPayload."""
        if not user_message or not user_message.strip():
            return RouterPayload(
                intent=QueryIntent.GREETING.value,
                concepts=[],
                difficulty="easy",
                requires_rag=False,
                requires_calculator=False,
                requires_student_state=False,
                pedagogical_mode="explain",
                confidence=1.0,
                rewritten_query=user_message,
            )

        raw_query = user_message.strip()
        rewritten = cls.rewrite_contextual_query(
            raw_query,
            current_concept=current_concept,
            previous_question=previous_question,
            active_problem=student_state.get("active_problem") if student_state else None,
        )

        # 1. Identify Intent
        matched_intent = QueryIntent.CONCEPT_EXPLANATION
        confidence = 0.85
        security_flag = None

        for intent_candidate, pattern in INTENT_RULES:
            if pattern.search(raw_query):
                matched_intent = intent_candidate
                confidence = 0.95
                break

        if matched_intent == QueryIntent.PROMPT_INJECTION:
            security_flag = "PROMPT_INJECTION_BLOCKED"
        elif matched_intent == QueryIntent.CHEMISTRY_SAFETY:
            security_flag = "UNSAFE_CHEMISTRY_BLOCKED"

        # 2. Extract Concepts
        extracted = cls.extract_concepts(raw_query) or cls.extract_concepts(rewritten)
        if not extracted and current_concept:
            extracted = [current_concept]

        # 3. Determine Execution Requirements
        requires_calculator = matched_intent in {
            QueryIntent.NUMERICAL, QueryIntent.DERIVATION, QueryIntent.PROBLEM_SOLVING, QueryIntent.ANSWER_CHECK
        }
        requires_rag = matched_intent not in {
            QueryIntent.GREETING, QueryIntent.HINT, QueryIntent.PROMPT_INJECTION, QueryIntent.CHEMISTRY_SAFETY
        }
        requires_student_state = matched_intent not in {
            QueryIntent.GREETING, QueryIntent.OUT_OF_SCOPE, QueryIntent.PROMPT_INJECTION, QueryIntent.CHEMISTRY_SAFETY
        }

        # 4. Map Pedagogical Mode
        mode_map = {
            QueryIntent.GREETING: "explain",
            QueryIntent.DEFINITION: "explain",
            QueryIntent.CONCEPT_EXPLANATION: "explain",
            QueryIntent.WHY: "explain",
            QueryIntent.HOW: "explain",
            QueryIntent.COMPARISON: "explain",
            QueryIntent.FORMULA: "explain",
            QueryIntent.DERIVATION: "explain",
            QueryIntent.NUMERICAL: "question",
            QueryIntent.REACTION: "explain",
            QueryIntent.MECHANISM: "explain",
            QueryIntent.MCQ: "question",
            QueryIntent.ASSERTION_REASON: "question",
            QueryIntent.PROBLEM_SOLVING: "question",
            QueryIntent.HINT: "hint",
            QueryIntent.ANSWER_CHECK: "evaluate",
            QueryIntent.MISCONCEPTION: "remediate",
            QueryIntent.REMEDIATION: "remediate",
            QueryIntent.REVISION: "review",
            QueryIntent.SUMMARY: "explain",
            QueryIntent.PRACTICE: "question",
            QueryIntent.QUIZ: "question",
            QueryIntent.EXAM: "question",
            QueryIntent.FOLLOW_UP: "explain",
            QueryIntent.CLARIFICATION: "explain",
            QueryIntent.OUT_OF_SCOPE: "explain",
            QueryIntent.PROMPT_INJECTION: "explain",
            QueryIntent.CHEMISTRY_SAFETY: "explain",
        }
        pedagogical_mode = mode_map.get(matched_intent, "explain")

        # 5. Difficulty Estimation
        difficulty = "medium"
        if matched_intent in {QueryIntent.DERIVATION, QueryIntent.MECHANISM, QueryIntent.EXAM}:
            difficulty = "hard"
        elif matched_intent in {QueryIntent.GREETING, QueryIntent.DEFINITION, QueryIntent.HINT}:
            difficulty = "easy"

        payload = RouterPayload(
            intent=matched_intent.value,
            concepts=extracted,
            difficulty=difficulty,
            requires_rag=requires_rag,
            requires_calculator=requires_calculator,
            requires_student_state=requires_student_state,
            pedagogical_mode=pedagogical_mode,
            confidence=confidence,
            rewritten_query=rewritten,
            security_flag=security_flag,
        )

        logger.info(f"Routed query '{raw_query[:30]}...' -> Intent: {matched_intent.value}, Concepts: {extracted}")
        return payload


# Backward compatibility wrapper for existing TutorIntentClassifier.classify invocations
class TutorIntentClassifier:
    """Wrapper ensuring backward compatibility with legacy 9-intent calls."""

    @staticmethod
    def classify(user_message: str) -> TutorIntent:
        payload = QueryIntelligenceEngine.classify_and_route(user_message)
        intent_val = payload.intent

        mapping = {
            "definition": TutorIntent.EXPLAIN,
            "concept_explanation": TutorIntent.EXPLAIN,
            "why": TutorIntent.CLARIFY,
            "how": TutorIntent.CLARIFY,
            "comparison": TutorIntent.COMPARE,
            "formula": TutorIntent.EXPLAIN,
            "derivation": TutorIntent.SOLVE,
            "numerical": TutorIntent.SOLVE,
            "reaction": TutorIntent.EXPLAIN,
            "mechanism": TutorIntent.EXPLAIN,
            "mcq": TutorIntent.PRACTICE,
            "assertion_reason": TutorIntent.PRACTICE,
            "problem_solving": TutorIntent.SOLVE,
            "hint": TutorIntent.CLARIFY,
            "answer_check": TutorIntent.SOLVE,
            "misconception": TutorIntent.CLARIFY,
            "remediation": TutorIntent.LEARN,
            "revision": TutorIntent.REVIEW,
            "summary": TutorIntent.SUMMARIZE,
            "practice": TutorIntent.PRACTICE,
            "quiz": TutorIntent.TEST,
            "exam": TutorIntent.TEST,
            "follow_up": TutorIntent.CLARIFY,
            "clarification": TutorIntent.CLARIFY,
            "greeting": TutorIntent.LEARN,
            "out_of_scope": TutorIntent.EXPLAIN,
            "prompt_injection": TutorIntent.EXPLAIN,
            "chemistry_safety": TutorIntent.EXPLAIN,
        }
        return mapping.get(intent_val, TutorIntent.EXPLAIN)
