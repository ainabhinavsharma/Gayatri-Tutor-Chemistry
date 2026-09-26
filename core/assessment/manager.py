"""Assessment Engine Manager (Phase 6).

Implements question bank schema, assessment session persistence,
attempt recording, grading, score calculation, and student learning state updates.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from core.assessment.grader import AssessmentGrader
from core.assessment.schema import MCQQuestion, NumericalQuestion, Question
from core.learning.misconceptions import MisconceptionTracker
from core.tutor.state import LearningEvent, TutorStateManager, generate_turn_id

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


@dataclass
class QuestionBankItem:
    id: str
    concept_id: str
    difficulty: int
    type: str
    question: str
    answer: Any
    rubric: str = ""
    hint: str = ""
    explanation: str = ""
    common_misconceptions: list[str] = field(default_factory=list)
    source: str = "NCERT"

    def to_question_schema(self) -> Question:
        if self.type == "numeric" or self.type == "numerical":
            try:
                val = float(self.answer)
            except ValueError:
                val = 0.0
            return NumericalQuestion(
                question_id=self.id,
                topic_id=self.concept_id,
                difficulty=self.difficulty,
                question_text=self.question,
                expected_value=val,
                rubric=self.rubric,
                hint=self.hint,
                explanation=self.explanation,
                common_misconceptions=self.common_misconceptions,
                source_id=self.source,
            )
        else:
            return MCQQuestion(
                question_id=self.id,
                topic_id=self.concept_id,
                difficulty=self.difficulty,
                question_text=self.question,
                correct_answer=self.answer,
                rubric=self.rubric,
                hint=self.hint,
                explanation=self.explanation,
                common_misconceptions=self.common_misconceptions,
                source_id=self.source,
            )


# Default Sample Question Bank (P6-T01 NCERT Aligned)
SAMPLE_QUESTION_BANK: list[QuestionBankItem] = [
    QuestionBankItem(
        id="thermo.hess.001",
        concept_id="thermo.hess_law",
        difficulty=3,
        type="numeric",
        question="Given C + O2 -> CO2 (delta H = -393.5 kJ/mol) and CO + 1/2 O2 -> CO2 (delta H = -283.0 kJ/mol), calculate delta H for C + 1/2 O2 -> CO.",
        answer="-110.5",
        rubric="Subtract equation 2 from equation 1",
        hint="Invert the second equation and flip the sign of its enthalpy.",
        explanation="delta H = -393.5 - (-283.0) = -110.5 kJ/mol",
        common_misconceptions=["HESS_LAW_DIRECTION", "THERMO_SIGN_CONVENTION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="thermo.gibbs.001",
        concept_id="thermo.gibbs",
        difficulty=2,
        type="mcq",
        question="For a spontaneous reaction at constant temperature and pressure, which condition must hold true?",
        answer="delta G < 0",
        rubric="Gibbs free energy change must be negative for spontaneous processes",
        explanation="A reaction is spontaneous when delta G = delta H - T delta S is less than zero.",
        common_misconceptions=["GIBBS_SIGN_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="inorganic.periodicity.001",
        concept_id="inorganic.periodicity",
        difficulty=2,
        type="mcq",
        question="Which of the following elements has the highest first ionization enthalpy?",
        answer="Helium",
        rubric="Ionization enthalpy increases across a period and up a group",
        explanation="Helium has a closed-shell 1s2 configuration and smallest atomic radius.",
        common_misconceptions=["PERIODIC_TREND_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="bonding.vsepr.001",
        concept_id="chem_inorg_bonding",
        difficulty=3,
        type="mcq",
        question="According to VSEPR theory, what is the molecular shape of ammonia (NH3)?",
        answer="Trigonal pyramidal",
        rubric="Steric number 4 with 1 lone pair yields trigonal pyramidal shape",
        explanation="Nitrogen in NH3 has 3 bond pairs and 1 lone pair, distorting the tetrahedral geometry into trigonal pyramidal.",
        common_misconceptions=["VSEPR_GEOMETRY_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="bonding.hybrid.001",
        concept_id="chem_inorg_bonding",
        difficulty=3,
        type="mcq",
        question="What is the hybridization of the central sulfur atom in SF6?",
        answer="sp3d2",
        rubric="Steric number 6 with 0 lone pairs corresponds to sp3d2 octahedral",
        explanation="Sulfur shares 6 electron pairs with fluorine atoms, requiring 6 hybrid orbitals: sp3d2.",
        common_misconceptions=["HYBRIDIZATION_CALC_ERROR"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="coord.nomenclature.001",
        concept_id="chem_inorg_pblock",
        difficulty=3,
        type="mcq",
        question="What is the oxidation state of Cobalt in the complex [Co(NH3)6]Cl3?",
        answer="+3",
        rubric="NH3 is neutral, 3 Cl- counterions balance +3 complex charge",
        explanation="Since NH3 is a neutral ligand, the charge on the complex cation [Co(NH3)6]3+ is +3, so Co is in +3 oxidation state.",
        common_misconceptions=["OXIDATION_STATE_ERROR", "COORDINATION_NUMBER_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="equil.lechatelier.001",
        concept_id="chem_equil_le_chatelier",
        difficulty=3,
        type="mcq",
        question="For the exothermic synthesis N2(g) + 3H2(g) <=> 2NH3(g) (delta H < 0), which condition favors maximum yield of ammonia?",
        answer="High pressure and low temperature",
        rubric="Exothermic reaction favored by lower T; fewer moles on product side favored by high P",
        hint="Consider Le Chatelier principle on gas moles and enthalpy sign.",
        explanation="According to Le Chatelier principle, increasing pressure shifts toward fewer gaseous moles (4 -> 2), and lowering temperature shifts toward the exothermic direction.",
        common_misconceptions=["LE_CHATELIER_CATALYST_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="equil.catalyst.001",
        concept_id="chem_equil_le_chatelier",
        difficulty=2,
        type="mcq",
        question="What is the effect of adding a catalyst to a reversible reaction at chemical equilibrium?",
        answer="No shift in equilibrium position",
        rubric="Catalyst increases rates of forward and reverse reactions equally without changing K",
        hint="Does a catalyst affect thermodynamics or kinetics?",
        explanation="A catalyst lowers activation energy equally for both forward and reverse paths, leaving the equilibrium concentrations and equilibrium constant K unaltered.",
        common_misconceptions=["LE_CHATELIER_CATALYST_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="equil.kp_kc.001",
        concept_id="chem_equil_constants",
        difficulty=3,
        type="numeric",
        question="For the reaction PCl5(g) <=> PCl3(g) + Cl2(g), calculate delta n_g (the change in gaseous moles).",
        answer="1.0",
        rubric="delta n_g = moles of gaseous products - moles of gaseous reactants = (1 + 1) - 1",
        hint="Count the stoichiometric coefficients of all gaseous substances.",
        explanation="delta n_g = (1 + 1) - 1 = 1 mole of gas.",
        common_misconceptions=["KP_KC_RELATION_ERROR"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="equil.ph_calc.001",
        concept_id="chem_equil_ionic",
        difficulty=3,
        type="numeric",
        question="What is the pH of a 0.001 M aqueous solution of strong hydrochloric acid (HCl)?",
        answer="3.0",
        rubric="pH = -log10[H+] = -log10(10^-3) = 3.0",
        hint="Express [H+] in scientific notation and take negative log base 10.",
        explanation="For a strong monoprotic acid, [H+] = 0.001 M = 10^-3 M. Therefore, pH = -log(10^-3) = 3.0.",
        common_misconceptions=["PH_BUFFER_CAPACITY_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="coord.ligand.denticity.001",
        concept_id="chem_coord_entities",
        difficulty=2,
        type="mcq",
        question="How many donor atoms does ethylenediamine (en) possess when coordinating to a metal center?",
        answer="2",
        rubric="Ethylenediamine is a neutral bidentate ligand with 2 donor nitrogen atoms",
        hint="Think of the chemical formula NH2-CH2-CH2-NH2.",
        explanation="Ethylenediamine (H2N-CH2-CH2-NH2) has two amine nitrogen atoms with lone pairs, making it a classic bidentate chelating ligand.",
        common_misconceptions=["LIGAND_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="coord.werner.valency.001",
        concept_id="chem_coord_werner",
        difficulty=3,
        type="mcq",
        question="According to Werner's coordination theory, which valency is non-ionizable and corresponds to coordination number?",
        answer="Secondary valency",
        rubric="Primary valency is ionizable (oxidation state); secondary valency is non-ionizable (coordination number)",
        hint="Recall the difference between primary and secondary valency in Werner's postulates.",
        explanation="Werner postulated that secondary valencies are non-ionizable, directional in 3D space, and satisfy the coordination number.",
        common_misconceptions=["COORDINATION_NUMBER_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="thermo.work.calc.001",
        concept_id="chem_thermo_first_law",
        difficulty=4,
        type="numeric",
        question="A gas absorbs 500 J of heat and does 200 J of work during expansion. Calculate the change in internal energy delta U in Joules.",
        answer="300.0",
        rubric="delta U = q + w. Since work is done BY system during expansion, w = -200 J. delta U = 500 + (-200) = 300 J",
        hint="Use the IUPAC sign convention: work of expansion done by the system is negative.",
        explanation="Under IUPAC convention: q = +500 J (absorbed), w = -200 J (expansion work done by system). delta U = q + w = 500 - 200 = 300 J.",
        common_misconceptions=["THERMO_SIGN_CONVENTION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="bonding.dipole.co2.001",
        concept_id="chem_inorg_bonding",
        difficulty=3,
        type="mcq",
        question="Why does carbon dioxide (CO2) have zero net molecular dipole moment despite containing polar C=O bonds?",
        answer="Linear geometry causes bond dipoles to cancel",
        rubric="Linear symmetrical geometry (180 degree bond angle) leads to vector cancellation of dipole moments",
        hint="Consider the molecular symmetry and bond angles in CO2.",
        explanation="CO2 is linear (O=C=O) with two equal C=O bond dipole vectors oriented in exactly opposite directions (180°), yielding a net dipole moment of zero.",
        common_misconceptions=["BOND_POLARITY_VS_DIPOLE"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="inorg.periodic.radius.001",
        concept_id="chem_inorg_periodic",
        difficulty=2,
        type="mcq",
        question="Across a period from left to right in the periodic table, what happens to atomic radius?",
        answer="Decreases",
        rubric="Atomic radius decreases across a period due to increasing effective nuclear charge",
        hint="What happens to the effective nuclear charge (Z_eff) as electrons are added to the same valence shell?",
        explanation="Across a period, nuclear charge increases while electrons enter the same principal energy shell, pulling electron clouds closer to the nucleus.",
        common_misconceptions=["PERIODIC_TREND_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="thermo.entropy.spontaneity.001",
        concept_id="chem_thermo_entropy",
        difficulty=3,
        type="mcq",
        question="According to the Second Law of Thermodynamics, for an isolated system to undergo a spontaneous process, what must be true of delta S?",
        answer="delta S > 0",
        rubric="Entropy of an isolated system increases for spontaneous processes",
        hint="Think about the disorder of the universe or isolated system over time.",
        explanation="For an isolated system (such as the universe), any spontaneous irreversible change leads to an increase in total entropy (delta S_total > 0).",
        common_misconceptions=["ENTHALPY_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="inorg.redox.balancing.001",
        concept_id="chem_balancing",
        difficulty=3,
        type="numeric",
        question="Balance the reaction Fe + O2 -> Fe2O3. What is the stoichiometric coefficient in front of Fe?",
        answer="4.0",
        rubric="4 Fe + 3 O2 -> 2 Fe2O3",
        hint="Balance Fe and O so that atoms on both sides are equal integers.",
        explanation="The balanced chemical equation is 4Fe + 3O2 -> 2Fe2O3. The coefficient of Fe is 4.",
        common_misconceptions=["OXIDATION_STATE_ERROR"],
        source="NCERT",
    ),
]


class AssessmentManager:
    """Manages assessment lifecycle, grading, persistence, and evidence recording."""

    def __init__(self, state_manager: TutorStateManager, questions: list[QuestionBankItem] | None = None):
        self.state_manager = state_manager
        self.questions = questions or SAMPLE_QUESTION_BANK
        self.question_map = {q.id: q for q in self.questions}

    def create_assessment_session(
        self,
        student_id: str,
        concepts: list[str],
        question_count: int = 5,
    ) -> str:
        """Create a new assessment session record (P6-T02) and persist to assessment & assessment_question."""
        from core.security.rate_limiter import get_governor
        get_governor().check_assessment(student_id)

        assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # Select matching questions
        matching_q = [q for q in self.questions if q.concept_id in concepts]
        if not matching_q:
            matching_q = self.questions
        selected_ids = [q.id for q in matching_q[:question_count]]

        with self.state_manager.conn:
            # Section 17 required table: assessment
            self.state_manager.conn.execute('''
                INSERT INTO assessment (
                    assessment_id, student_id, concepts_json, question_ids_json,
                    start_time, status, score
                ) VALUES (?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0)
            ''', (
                assessment_id, student_id, json.dumps(concepts),
                json.dumps(selected_ids), now
            ))
            # Legacy table: assessment_sessions
            self.state_manager.conn.execute('''
                INSERT INTO assessment_sessions (
                    assessment_id, student_id, concepts_json, question_ids_json,
                    start_time, status, score
                ) VALUES (?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0)
            ''', (
                assessment_id, student_id, json.dumps(concepts),
                json.dumps(selected_ids), now
            ))

            # Section 17 required table: assessment_question
            for q_id in selected_ids:
                q_item = self.question_map.get(q_id)
                if q_item:
                    self.state_manager.conn.execute('''
                        INSERT OR REPLACE INTO assessment_question (
                            id, assessment_id, question_id, concept_id, difficulty,
                            type, question, answer, rubric, hint, explanation,
                            common_misconceptions, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        f"{assessment_id}_{q_item.id}",
                        assessment_id,
                        q_item.id,
                        q_item.concept_id,
                        q_item.difficulty,
                        q_item.type,
                        q_item.question,
                        str(q_item.answer),
                        q_item.rubric,
                        q_item.hint,
                        q_item.explanation,
                        json.dumps(q_item.common_misconceptions),
                        q_item.source,
                    ))

        return assessment_id

    def submit_attempt(
        self,
        assessment_id: str,
        student_id: str,
        question_id: str,
        student_answer: Any,
    ) -> dict:
        """Grade and record an attempt on a question (P6-T03) in assessment_attempt & assessment_attempts."""
        item = self.question_map.get(question_id)
        if not item:
            raise ValueError(f"Question ID {question_id} not found in question bank.")

        q_schema = item.to_question_schema()
        is_corr, score_frac, feedback = AssessmentGrader.grade_answer(q_schema, student_answer)

        attempt_id = f"att_{uuid.uuid4().hex[:10]}"
        now = datetime.now().isoformat()

        with self.state_manager.conn:
            # Section 17 required table: assessment_attempt
            self.state_manager.conn.execute('''
                INSERT INTO assessment_attempt (
                    attempt_id, assessment_id, student_id, question_id, concept_id,
                    student_answer, is_correct, score_fraction, feedback, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_id, assessment_id, student_id, question_id, item.concept_id,
                str(student_answer), 1 if is_corr else 0, score_frac, feedback, now
            ))
            # Legacy table: assessment_attempts
            self.state_manager.conn.execute('''
                INSERT INTO assessment_attempts (
                    attempt_id, assessment_id, student_id, question_id, concept_id,
                    student_answer, is_correct, score_fraction, feedback, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_id, assessment_id, student_id, question_id, item.concept_id,
                str(student_answer), 1 if is_corr else 0, score_frac, feedback, now
            ))

        # Check misconception
        detected_misconception = ""
        if not is_corr and item.common_misconceptions:
            detected_misconception = item.common_misconceptions[0]
            tracker = MisconceptionTracker(self.state_manager)
            tracker.record_misconception(student_id, item.concept_id, detected_misconception)

        from core.tutor.deadend import ActionPath, DeadEndResolver, DeadEndScenario
        actions = DeadEndResolver.resolve_actions(
            DeadEndScenario.ASSESSMENT,
            ActionPath.SUCCESS,
            {"is_completed": False}
        )

        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "is_correct": is_corr,
            "score_fraction": score_frac,
            "feedback": feedback,
            "detected_misconception": detected_misconception,
            "next_actions": [a.to_dict() for a in actions],
        }

    def complete_assessment_session(self, assessment_id: str, student_id: str) -> dict:
        """Finalize assessment session, compute score, persist to score table, and update learner state (P6-T04)."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_attempt WHERE assessment_id = ? AND student_id = ?",
            (assessment_id, student_id)
        )
        attempts = cursor.fetchall()
        if not attempts:
            from core.tutor.deadend import ActionPath, DeadEndResolver, DeadEndScenario
            actions = DeadEndResolver.resolve_actions(DeadEndScenario.ASSESSMENT, ActionPath.FAILURE)
            return {
                "assessment_id": assessment_id,
                "score": 0.0,
                "status": "NO_ATTEMPTS",
                "next_actions": [a.to_dict() for a in actions],
            }

        total_score = sum(att["score_fraction"] for att in attempts)
        max_possible = len(attempts)
        score_percentage = round((total_score / max_possible) * 100, 2) if max_possible > 0 else 0.0

        now = datetime.now().isoformat()

        concept_scores: dict[str, list[float]] = {}
        for att in attempts:
            cid = att["concept_id"]
            if cid not in concept_scores:
                concept_scores[cid] = []
            concept_scores[cid].append(att["score_fraction"])

        strengths = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) >= 0.7]
        weaknesses = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) < 0.7]

        # Update assessment session in DB
        score_id = f"score_{uuid.uuid4().hex[:10]}"
        with self.state_manager.conn:
            # Section 17 required table: assessment
            self.state_manager.conn.execute('''
                UPDATE assessment
                SET end_time = ?, status = 'COMPLETED', score = ?
                WHERE assessment_id = ? AND student_id = ?
            ''', (now, score_percentage, assessment_id, student_id))
            # Legacy table: assessment_sessions
            self.state_manager.conn.execute('''
                UPDATE assessment_sessions
                SET end_time = ?, status = 'COMPLETED', score = ?
                WHERE assessment_id = ? AND student_id = ?
            ''', (now, score_percentage, assessment_id, student_id))
            # Section 17 required table: score
            self.state_manager.conn.execute('''
                INSERT OR REPLACE INTO score (
                    score_id, assessment_id, student_id, total_score, max_possible,
                    score_percentage, strengths_json, weaknesses_json, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                score_id,
                assessment_id,
                student_id,
                total_score,
                float(max_possible),
                score_percentage,
                json.dumps(strengths),
                json.dumps(weaknesses),
                now,
            ))

        # Record learning events to mutate student mastery state (Section 17: outcomes become learning events)
        turn_id, ts = generate_turn_id(student_id=student_id, session_id=assessment_id)

        for att in attempts:
            cid = att["concept_id"]
            is_c = bool(att["is_correct"])
            score_frac = att["score_fraction"]

            correctness_str = "correct" if is_c else ("partially_correct" if score_frac > 0 else "incorrect")

            event = LearningEvent(
                event_id=f"evt_{att['attempt_id']}",
                student_id=student_id,
                session_id=assessment_id,
                turn_id=turn_id,
                concept_id=cid,
                question_id=att["question_id"],
                timestamp=ts,
                difficulty=3.0,
                correctness=correctness_str,
                source="assessment",
            )
            self.state_manager.record_learning_event(event)

        from core.tutor.deadend import ActionPath, DeadEndResolver, DeadEndScenario
        actions = DeadEndResolver.resolve_actions(
            DeadEndScenario.ASSESSMENT,
            ActionPath.SUCCESS,
            {"is_completed": True, "strengths": strengths, "weaknesses": weaknesses},
        )

        return {
            "assessment_id": assessment_id,
            "student_id": student_id,
            "score_percentage": score_percentage,
            "total_attempts": len(attempts),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "status": "COMPLETED",
            "next_actions": [a.to_dict() for a in actions],
        }

    def get_assessment(self, assessment_id: str) -> dict | None:
        """Fetch assessment session record from assessment table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment WHERE assessment_id = ?",
            (assessment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_assessment_questions(self, assessment_id: str) -> list[dict]:
        """Fetch all questions for an assessment from assessment_question table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_question WHERE assessment_id = ? ORDER BY question_id",
            (assessment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_assessment_attempts(self, assessment_id: str) -> list[dict]:
        """Fetch all attempts for an assessment from assessment_attempt table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_attempt WHERE assessment_id = ? ORDER BY submitted_at",
            (assessment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_assessment_score(self, assessment_id: str) -> dict | None:
        """Fetch score record for an assessment from score table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM score WHERE assessment_id = ?",
            (assessment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
