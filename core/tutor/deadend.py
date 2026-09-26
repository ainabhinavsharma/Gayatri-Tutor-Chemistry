"""Gayatri AI — Dead-End Analysis and Next-Action Resolver (Phase 23 / Section 29).

Enforces the core invariant:
"No state may leave the student without a valid next action."

Covers all 11 tutoring scenarios across:
- success path
- failure path
- recovery path
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DeadEndScenario(str, Enum):
    """The 11 mandatory states/scenarios specified in Section 29."""
    NEW_STUDENT = "new_student"
    ACTIVE_LEARNING = "active_learning"
    ASSESSMENT = "assessment"
    REMEDIATION = "remediation"
    REVIEW = "review"
    MASTERED_CONCEPT = "mastered_concept"
    EMPTY_RAG = "empty_rag"
    LLM_TIMEOUT = "llm_timeout"
    DATABASE_FAILURE = "database_failure"
    SESSION_RESTORATION = "session_restoration"
    MODE_SWITCH = "mode_switch"


class ActionPath(str, Enum):
    """The 3 mandatory path types for every state."""
    SUCCESS = "success"
    FAILURE = "failure"
    RECOVERY = "recovery"


@dataclass
class NextAction:
    """Represents an actionable next step for the student."""
    action_id: str
    label: str
    prompt: str
    action_type: str = "prompt"  # "prompt" | "retry" | "navigate" | "assessment" | "review" | "mode_switch"
    is_recovery: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeadEndResolver:
    """Resolves and guarantees actionable next steps for all tutoring scenarios and paths."""

    @staticmethod
    def resolve_actions(
        scenario: DeadEndScenario | str,
        path: ActionPath | str,
        context: dict[str, Any] | None = None,
    ) -> list[NextAction]:
        """Resolve a non-empty list of NextActions for a given scenario and path.

        Invariant: Every state must return at least 1 valid NextAction with non-empty
        label and prompt.
        """
        ctx = context or {}
        sc_val = scenario.value if isinstance(scenario, DeadEndScenario) else str(scenario)
        p_val = path.value if isinstance(path, ActionPath) else str(path)

        concept_name = ctx.get("concept_name") or "Thermodynamics"
        concept_id = ctx.get("concept_id") or "thermo.first_law"

        actions: list[NextAction] = []

        # 1. NEW_STUDENT
        if sc_val == DeadEndScenario.NEW_STUDENT.value:
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("start_curriculum", "🚀 Start Chapter 1: Thermodynamics", f"Let's begin learning {concept_name}.", "navigate"),
                    NextAction("take_diagnostic", "📝 Take Diagnostic Assessment", "I'd like to take a diagnostic test to assess my chemistry baseline.", "assessment"),
                    NextAction("explore_syllabus", "📚 Explore Chemistry Syllabus", "What topics will we cover in NCERT Chemistry?", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("retry_profile_setup", "🔄 Retry Setup", "Please set up my chemistry student profile again.", "retry", is_recovery=True),
                    NextAction("continue_as_guest", "👤 Continue as Guest", "Let's continue as a guest student for now.", "navigate", is_recovery=True),
                    NextAction("browse_topics", "📖 Browse Topics Directly", "Can you show me the available chemistry chapters?", "prompt", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("quick_start_basics", "💡 Begin with Chemical Reactions", "Let's start with basic Chemical Reactions.", "navigate", is_recovery=True),
                    NextAction("guided_onboarding", "🧭 Guided Introduction", "Can you guide me through how this chemistry tutor works?", "prompt", is_recovery=True),
                ]

        # 2. ACTIVE_LEARNING
        elif sc_val == DeadEndScenario.ACTIVE_LEARNING.value:
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("practice_problem", "🎯 Practice Problem", f"Can you give me a practice problem on {concept_name}?", "prompt"),
                    NextAction("give_example", "💡 Give an Example", f"Can you explain {concept_name} with a practical example?", "prompt"),
                    NextAction("next_concept", "⏩ Next Concept", "I understand this concept! What should we cover next?", "navigate"),
                    NextAction("ask_question", "❓ Ask Me a Question", "Test my understanding with a question!", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("rephrase_question", "🔄 Rephrase Question", "Let me rephrase my last chemistry question.", "retry", is_recovery=True),
                    NextAction("ask_for_hint", "💡 Ask for a Hint", f"Can you give me a hint about {concept_name}?", "prompt", is_recovery=True),
                    NextAction("review_summary", "📖 Review Concept Summary", f"Can you summarize the core points of {concept_name}?", "prompt", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("step_back_basics", "⏪ Review Foundations", f"Let's review the prerequisites for {concept_name}.", "navigate", is_recovery=True),
                    NextAction("guided_step_by_step", "🪜 Step-by-Step Breakdown", f"Break down {concept_name} step by step for me.", "prompt", is_recovery=True),
                ]

        # 3. ASSESSMENT
        elif sc_val == DeadEndScenario.ASSESSMENT.value:
            is_completed = ctx.get("is_completed", False)
            weaknesses = ctx.get("weaknesses", [])
            if p_val == ActionPath.SUCCESS.value:
                if is_completed:
                    if weaknesses:
                        actions.append(NextAction("remediate_weakness", f"🎯 Remediate: {weaknesses[0]}", f"I want to review and practice {weaknesses[0]}.", "prompt"))
                    actions.extend([
                        NextAction("view_report", "📊 View Performance Report", "Can you summarize my assessment strengths and weaknesses?", "prompt"),
                        NextAction("return_to_tutor", "📚 Return to Tutor", "Let's return to regular chemistry tutoring.", "navigate"),
                    ])
                else:
                    actions = [
                        NextAction("submit_answer", "✅ Submit Answer", "Submit my answer for evaluation.", "assessment"),
                        NextAction("next_question", "⏩ Next Question", "Move to the next question in this assessment.", "assessment"),
                        NextAction("flag_for_review", "🚩 Flag Question", "Flag this question and move forward.", "assessment"),
                    ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("retry_assessment_question", "🔄 Retry Question", "Please re-evaluate my answer to this question.", "retry", is_recovery=True),
                    NextAction("resume_assessment", "▶️ Resume Assessment", "Resume my in-progress assessment session.", "assessment", is_recovery=True),
                    NextAction("exit_assessment_safely", "💾 Save & Exit", "Save my progress and exit this assessment.", "navigate", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("restart_assessment", "🔄 Restart Assessment", "Let's start a fresh assessment on this chapter.", "assessment", is_recovery=True),
                    NextAction("practice_weak_topics", "🎯 Practice Identified Topics", "Give me practice on the concepts I struggled with.", "prompt", is_recovery=True),
                ]

        # 4. REMEDIATION
        elif sc_val == DeadEndScenario.REMEDIATION.value:
            misconception = ctx.get("misconception_code", "misconception")
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("try_guided_practice", "🎯 Try Guided Practice", f"Give me a guided question to fix my {misconception} understanding.", "prompt"),
                    NextAction("review_counter_example", "💡 View Counter-Example", "Can you show me a clear counter-example illustrating this?", "prompt"),
                    NextAction("check_understanding", "❓ Verify My Understanding", "Ask me a question to verify I understand this now.", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("step_down_difficulty", "📉 Lower Difficulty", "This is too difficult. Can we try an easier foundational question?", "prompt", is_recovery=True),
                    NextAction("review_prerequisite", "⏪ Review Prerequisite Concept", "Let's review the foundational concept before trying again.", "navigate", is_recovery=True),
                    NextAction("explain_differently", "🔄 Explain Differently", "Can you explain this using an everyday analogy?", "prompt", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("reset_concept_foundation", "🏛️ Foundational Walkthrough", "Let's start this concept from absolute first principles.", "prompt", is_recovery=True),
                    NextAction("interactive_quiz", "🧩 Simple Concept Check", "Give me a simple true/false check on the core rule.", "prompt", is_recovery=True),
                ]

        # 5. REVIEW
        elif sc_val == DeadEndScenario.REVIEW.value:
            items_due = ctx.get("items_due", 0)
            if p_val == ActionPath.SUCCESS.value:
                if items_due > 0:
                    actions = [
                        NextAction("next_review_item", "🔁 Next Review Concept", "Let's review the next scheduled concept.", "review"),
                        NextAction("flashcard_recall", "🃏 Flashcard Recall", "Quiz me with a flashcard for this concept.", "prompt"),
                        NextAction("finish_review", "🏁 Finish Review Session", "Let's wrap up today's review session.", "navigate"),
                    ]
                else:
                    actions = [
                        NextAction("return_to_curriculum", "📖 Return to Curriculum", "All reviews done! Let's continue with new material.", "navigate"),
                        NextAction("take_review_quiz", "📝 Comprehensive Review Quiz", "Give me a quick review quiz across recent chapters.", "assessment"),
                    ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("practice_weakest_concept", "🎯 Practice Weakest Concept", "Find my concept with the lowest mastery and practice it.", "prompt", is_recovery=True),
                    NextAction("explore_new_topics", "🚀 Explore New Topics", "Let's move ahead and learn something new.", "navigate", is_recovery=True),
                    NextAction("view_learning_dashboard", "📊 View Learning Progress", "Show me my current mastery across all chapters.", "navigate", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("reschedule_reviews", "📅 Reschedule Due Reviews", "Reschedule my pending reviews for later this week.", "review", is_recovery=True),
                    NextAction("quick_retention_check", "⚡ Quick Retention Check", "Give me 3 rapid-fire questions to check my memory.", "prompt", is_recovery=True),
                ]

        # 6. MASTERED_CONCEPT
        elif sc_val == DeadEndScenario.MASTERED_CONCEPT.value:
            has_next = ctx.get("has_next_concept", True)
            next_name = ctx.get("next_concept_name") or "Hess's Law"
            if p_val == ActionPath.SUCCESS.value:
                if has_next:
                    actions = [
                        NextAction("advance_next_concept", f"⏩ Advance to {next_name}", f"I have mastered {concept_name}. Let's learn {next_name}!", "navigate"),
                        NextAction("deep_dive_challenge", "🏆 Deep Dive Challenge", f"Give me an advanced challenge problem on {concept_name}.", "prompt"),
                        NextAction("take_mastery_quiz", "📝 Take Mastery Quiz", f"Test my mastery of {concept_name} with a challenge quiz.", "assessment"),
                    ]
                else:
                    actions = [
                        NextAction("curriculum_completed_review", "🎓 Comprehensive Chapter Review", "I finished all concepts! Let's do a comprehensive review.", "review"),
                        NextAction("take_final_exam", "🏆 Take Final Mastery Exam", "I'm ready for the comprehensive final assessment.", "assessment"),
                        NextAction("explore_advanced_chem", "🔬 Explore Advanced Chemistry", "What advanced chemistry topics should I explore next?", "prompt"),
                    ]
            elif p_val == ActionPath.FAILURE.value:
                # e.g., end of curriculum reached or unlock failed
                actions = [
                    NextAction("initiate_recovery_review", "🔄 Comprehensive Syllabus Review", "Review all chapters covered in the syllabus.", "review", is_recovery=True),
                    NextAction("reinforce_prerequisites", "💪 Reinforce Foundations", "Let's reinforce the foundational concepts with practice.", "prompt", is_recovery=True),
                    NextAction("browse_all_chapters", "📚 Browse All Chapters", "Show me the chapter list so I can pick a topic.", "navigate", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("start_milestone_test", "📝 Milestone Assessment", "Let's start a milestone test on this subject.", "assessment", is_recovery=True),
                    NextAction("review_mastered_list", "📋 View Mastered Concepts", "Show me the list of concepts I've mastered.", "prompt", is_recovery=True),
                ]

        # 7. EMPTY_RAG
        elif sc_val == DeadEndScenario.EMPTY_RAG.value:
            query = ctx.get("query", "the topic")
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("search_ncert_index", "🔍 Search NCERT Index", f"Is {query} covered under a different name in NCERT?", "prompt"),
                    NextAction("browse_chapter_index", "📖 Browse Chapter Index", "Can you list the standard NCERT chapters for Class 11 and 12?", "prompt"),
                    NextAction("ask_general_chem", "🧪 Ask Chemistry Tutor", f"Can you explain the general chemistry principles of {query}?", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("rephrase_standard_terms", "🔄 Rephrase with Chemistry Terms", "Let me ask again using standard NCERT terminology.", "retry", is_recovery=True),
                    NextAction("pick_from_syllabus", "📋 Select from Syllabus Topics", "Show me the topics in the syllabus so I can select one.", "navigate", is_recovery=True),
                    NextAction("switch_to_general_mode", "🤖 Ask General Assistant", f"Answer my question about {query} in General Assistant mode.", "mode_switch", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("search_thermo", "🔥 Explore Thermodynamics", "Let's explore Thermodynamics instead.", "navigate", is_recovery=True),
                    NextAction("search_bonding", "🔗 Explore Chemical Bonding", "Let's explore Chemical Bonding instead.", "navigate", is_recovery=True),
                ]

        # 8. LLM_TIMEOUT
        elif sc_val == DeadEndScenario.LLM_TIMEOUT.value:
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("continue_learning", "⏩ Continue Learning", "What should we do next?", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("retry_request", "🔄 Retry Request", "Retry the previous request.", "retry", is_recovery=True),
                    NextAction("switch_to_local_model", "⚡ Switch to Fast Model", "Use the faster local model for this question.", "retry", is_recovery=True),
                    NextAction("simplify_question", "❓ Simplify Question", "Let me break down my question into smaller parts.", "prompt", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("resend_last_query", "📤 Resend Last Query", "Resend the last query.", "retry", is_recovery=True),
                    NextAction("check_server_status", "🏥 Check Tutor Status", "Is the tutor engine responsive?", "prompt", is_recovery=True),
                ]

        # 9. DATABASE_FAILURE
        elif sc_val == DeadEndScenario.DATABASE_FAILURE.value:
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("continue_session", "⏩ Continue Session", "Continue with current session.", "prompt"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("retry_db_op", "🔄 Retry Database Operation", "Retry saving my learning progress.", "retry", is_recovery=True),
                    NextAction("continue_in_memory", "💾 Continue in Safe Mode", "Continue this session in temporary safe memory.", "navigate", is_recovery=True),
                    NextAction("restore_from_backup", "📦 Restore From Backup", "Restore learning state from the last valid snapshot.", "navigate", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("init_fresh_db_session", "🆕 Start Safe Session", "Initialize a fresh learning session.", "navigate", is_recovery=True),
                    NextAction("export_offline_progress", "📥 Export Session Progress", "Export my current session answers to file.", "navigate", is_recovery=True),
                ]

        # 10. SESSION_RESTORATION
        elif sc_val == DeadEndScenario.SESSION_RESTORATION.value:
            if p_val == ActionPath.SUCCESS.value:
                actions = [
                    NextAction("resume_last_concept", f"▶️ Resume {concept_name}", f"Let's continue where we left off with {concept_name}.", "navigate"),
                    NextAction("review_previous_turn", "👀 Review Previous Message", "What did we cover in our last message?", "prompt"),
                    NextAction("start_new_topic", "🆕 Start New Topic", "I want to start a new chemistry topic today.", "navigate"),
                ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("start_fresh_session", "🆕 Start Fresh Session", "Start a new session from the beginning.", "navigate", is_recovery=True),
                    NextAction("recover_last_progress", "🔄 Recover Last Known Progress", "Load my most recent saved concept progress.", "retry", is_recovery=True),
                    NextAction("browse_syllabus_chapters", "📚 Browse Syllabus", "Show me the chapter list to start from.", "navigate", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("new_chemistry_chat", "🧪 New Chemistry Chat", "Hello! Let's start learning chemistry.", "prompt", is_recovery=True),
                    NextAction("check_saved_sessions", "📂 Check Saved Sessions", "Show available saved sessions.", "navigate", is_recovery=True),
                ]

        # 11. MODE_SWITCH
        elif sc_val == DeadEndScenario.MODE_SWITCH.value:
            target_mode = ctx.get("target_mode", "chemistry_tutor")
            if p_val == ActionPath.SUCCESS.value:
                if target_mode == "chemistry_tutor":
                    actions = [
                        NextAction("explore_chem", "🧪 Explore Chemistry Topics", "What chemistry topics can we study?", "prompt"),
                        NextAction("ask_chem_question", "❓ Ask Chemistry Question", "Explain the First Law of Thermodynamics.", "prompt"),
                    ]
                else:
                    actions = [
                        NextAction("ask_general", "💬 Ask General Assistant", "How can you help me today?", "prompt"),
                        NextAction("switch_back_chem", "🧪 Switch to Chemistry Tutor", "Switch back to Chemistry Tutor mode.", "mode_switch"),
                    ]
            elif p_val == ActionPath.FAILURE.value:
                actions = [
                    NextAction("switch_chemistry_tutor", "🧪 Switch to Chemistry Tutor", "Activate Chemistry Tutor mode.", "mode_switch", is_recovery=True),
                    NextAction("switch_general_assistant", "🤖 Switch to General Assistant", "Activate General Assistant mode.", "mode_switch", is_recovery=True),
                ]
            else:  # RECOVERY
                actions = [
                    NextAction("confirm_current_mode", "ℹ️ Confirm Active Mode", "What is my current mode and what can I do?", "prompt", is_recovery=True),
                    NextAction("reset_mode_default", "🔄 Reset to Chemistry Tutor", "Set mode to Chemistry Tutor.", "mode_switch", is_recovery=True),
                ]

        # Guarantee invariant: Never return an empty list
        if not actions:
            actions = [
                NextAction("default_ask_question", "❓ Ask a Chemistry Question", "Can you explain a chemistry concept?", "prompt"),
                NextAction("default_browse_topics", "📚 Browse Chemistry Topics", "Show me the syllabus chapters.", "navigate"),
                NextAction("default_restart", "🔄 Restart Session", "Let's reset and start over.", "retry", is_recovery=True),
            ]

        return actions

    @classmethod
    def ensure_next_actions(
        cls,
        current_actions: list[dict[str, Any]] | None,
        scenario: DeadEndScenario | str = DeadEndScenario.ACTIVE_LEARNING,
        path: ActionPath | str = ActionPath.SUCCESS,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Guarantee that a list of next actions has at least one valid action."""
        if current_actions and len(current_actions) > 0:
            # Validate that every action has non-empty label and prompt
            valid = [
                a for a in current_actions
                if isinstance(a, dict) and a.get("label") and a.get("prompt")
            ]
            if valid:
                return valid

        resolved = cls.resolve_actions(scenario, path, context)
        return [a.to_dict() for a in resolved]
