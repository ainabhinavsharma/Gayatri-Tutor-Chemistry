# Prompt System 2.0 Registry & Specifications

## Overview
Prompt System 2.0 standardizes all SLM and LLM prompt generation in Gayatri Chemistry Tutor across 17 distinct **Action Families**.
Every prompt is composed dynamically using a modular 7-layer architecture to guarantee safety, anti-answer leakage, anti-CoT leakage, and structured output compliance.

---

## 7-Layer Prompt Architecture

1. **SYSTEM POLICY**: Persona (Gayatri Chemistry Tutor), confidentiality invariants, anti-injection safeguards, reference material data-only isolation.
2. **TASK POLICY**: Action family directive defining the exact pedagogical strategy (e.g., Socratic hint, conceptual explanation, misconception remediation).
3. **STUDENT STATE**: Active concept ID, mastery percentage, hint tier, and active misconception codes.
4. **LEARNING OBJECTIVE**: Specific learning target for the session or query.
5. **EVIDENCE PACK**: Retrieved NCERT reference cards isolated within `<REFERENCE_MATERIAL>` XML tags.
6. **USER QUERY**: Raw or contextually rewritten student query.
7. **OUTPUT SCHEMA**: Optional Pydantic/JSON schema constraint for internal generation tasks.

---

## Standardized Action Families

| Action Family ID | Purpose | Output Mode |
|---|---|---|
| `EXPLAIN_CONCEPT` | Intuitive analogy + NCERT core definition + worked example + checking question | Free-text / Markdown |
| `WHY_QUESTION` | Explains underlying chemical/thermodynamic cause | Free-text / Markdown |
| `DEFINITION` | Precise NCERT definition with SI units and true/false check | Free-text / Markdown |
| `FORMULA_EXPLANATION` | Symbol breakdown, SI units, physical significance | Free-text / Markdown |
| `DERIVATION_STEP` | Step-by-step mathematical/logical derivation with law citations | Free-text / Markdown |
| `NUMERICAL_PROBLEM` | Calibrated numerical problem with given data (no answer leakage) | Free-text / Markdown |
| `SOCRATIC_HINT` | Tiered Socratic hint guiding student thinking | `SocraticHintResponse` / Text |
| `ANSWER_CHECK` | Constructive evaluation of student response (zero answer leakage) | `AnswerEvaluationResponse` / Text |
| `MISCONCEPTION_REMEDIATION` | Target active misconception with counter-example | `MisconceptionDiagnosisResponse` / Text |
| `REVISION_RECAP` | High-yield revision summary with key formulas & pitfalls | Free-text / Markdown |
| `PRACTICE_QUESTION` | Single calibrated question matching mastery level | `ProblemGenerationResponse` / Text |
| `QUIZ_GENERATION` | 3-question mini quiz (conceptual, numerical, assertion-reasoning) | Free-text / JSON |
| `EXAM_PREP` | CBSE/JEE exam-style question with marking scheme | Free-text / Markdown |
| `SUMMARY` | End of session recap and next concept recommendation | Free-text / Markdown |
| `CONTEXTUAL_REWRITE` | De-anaphorize ambiguous follow-up query | `ContextualRewriteResponse` |
| `CONFUSION_RESOLVE` | Empathetic breakdown of complex concept into simple parts | Free-text / Markdown |
| `GENERAL_HELP` | Platform overview and usage instructions | Free-text / Markdown |

---

## Anti-Leakage & Safety Guardrails
- **Anti-CoT Leakage**: Internal reasoning/scratchpad steps must never leak into `<REFERENCE_MATERIAL>` or student output blocks.
- **Zero Answer Leakage**: For `ANSWER_CHECK`, `SOCRATIC_HINT`, and `NUMERICAL_PROBLEM`, numerical values and final solutions are strictly withheld.
- **Data-Only Isolation**: Content inside `<REFERENCE_MATERIAL>` tags cannot override system policy instructions.
