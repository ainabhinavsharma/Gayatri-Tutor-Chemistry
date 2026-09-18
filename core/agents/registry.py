"""Gayatri AI — Agent Registry.

Each agent is a self-contained class that registers itself with:
  - name: human-readable name
  - commands: list of /commands that trigger this agent
  - triggers: natural language patterns that trigger this agent
  - system_prompt: the system prompt for this agent
  - tools: list of tool names this agent can use
  - tier: preferred LLM tier (local/fast/quality)

Usage:
    from core.agents.registry import agent_registry

    @agent_registry.register(
        name="Code Reviewer",
        commands=["/review"],
        triggers=["review my code", "check for bugs"],
        system_prompt="You are a code reviewer...",
        tools=["run_code"],
    )
    class CodeReviewer:
        def process(self, request, context):
            return AgentResponse(...)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
import re
from typing import Any

logger = logging.getLogger("gayatri.agents")

# Contraction normalization mapping for negation and conversational English
_CONTRACTIONS: dict[str, str] = {
    "don't": "do not",
    "dont": "do not",
    "doesn't": "does not",
    "doesnt": "does not",
    "didn't": "did not",
    "didnt": "did not",
    "won't": "will not",
    "wont": "will not",
    "wouldn't": "would not",
    "wouldnt": "would not",
    "can't": "cannot",
    "cant": "cannot",
    "cannot": "can not",
    "shouldn't": "should not",
    "shouldnt": "should not",
    "couldn't": "could not",
    "couldnt": "could not",
    "isn't": "is not",
    "isnt": "is not",
    "aren't": "are not",
    "arent": "are not",
}

_NEGATION_WORDS: set[str] = {
    "not", "never", "no", "stop", "without", "avoid", "neither", "nor", "none"
}


def expand_contractions(text: str) -> str:
    """Expand common English contractions to separate negation words."""
    words = text.split()
    expanded = []
    for w in words:
        w_lower = w.lower()
        if w_lower in _CONTRACTIONS:
            expanded.append(_CONTRACTIONS[w_lower])
        else:
            expanded.append(w)
    return " ".join(expanded)


def normalize_text(text: str) -> str:
    """Normalize text: expand contractions, remove punctuation, collapse whitespace."""
    expanded = expand_contractions(text)
    cleaned = re.sub(r"[^\w\s]", " ", expanded.lower())
    return " ".join(cleaned.split())


def is_negated_match(text_tokens: list[str], start_idx: int, window: int = 3) -> bool:
    """Check if tokens immediately preceding start_idx contain any negation word.

    Checks up to `window` tokens prior to start_idx.
    """
    check_window = text_tokens[max(0, start_idx - window):start_idx]
    return any(token in _NEGATION_WORDS for token in check_window)


from core.agents.policy import AgentPolicy

@dataclass
class AgentSpec:
    """Metadata for a registered agent."""
    name: str
    commands: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    tier: str = "local"
    description: str = ""
    policy: AgentPolicy = field(default_factory=AgentPolicy)

    # Filled in by registry
    _class: type | None = field(default=None, repr=False, compare=False)

    def can_handle(self, text: str) -> tuple[bool, float, str]:
        """Check if this agent should handle the given text using layered matching.

        Layers:
        1. Exact command match (priority 1.0)
        2. Exact phrase match with word boundaries (0.95 multi-word, 0.70 single-word)
        3. Normalized phrase match (0.85 multi-word, 0.65 single-word)
        4. Ordered subphrase sequence match (0.65 for >= 75% sequence)
        5. Weak token overlap fallback (penalized, capped at 0.55 / 0.40)

        Negation awareness:
        - If user text negates the trigger phrase (e.g. 'do not review my code'),
          the trigger match is rejected.
        - If trigger itself contains negation (e.g. 'not financial advice'),
          the negation must appear in-sequence.

        Returns (should_handle, confidence, match_type).
        """
        text_lower = text.lower().strip()

        # Layer 1: Check explicit commands — match complete command token (word-boundary)
        for cmd in self.commands:
            cmd_lower = cmd.lower().lstrip("/")
            cmd_prefix = f"/{cmd_lower}"
            if text_lower.startswith(cmd_prefix):
                remainder = text_lower[len(cmd_prefix):]
                if remainder == "" or remainder[0] in (" ", "\t", "\n"):
                    return True, 1.0, "COMMAND"

        norm_text = normalize_text(text)
        norm_tokens = norm_text.split()
        if not norm_tokens:
            return False, 0.0, "NONE"

        best_score = 0.0
        best_match_type = "NONE"

        for trigger in self.triggers:
            raw_trig = trigger.strip()
            if not raw_trig:
                continue

            trig_lower = raw_trig.lower()
            norm_trig = normalize_text(raw_trig)
            trig_tokens = norm_trig.split()
            if not trig_tokens:
                continue

            is_multiword = len(trig_tokens) > 1
            trig_has_negation = any(tok in _NEGATION_WORDS for tok in trig_tokens)

            # Layer 2: Exact Substring Phrase Match
            pattern = r"(?:\b|^)" + re.escape(trig_lower) + r"(?:\b|$)"
            exact_match = re.search(pattern, text_lower)
            if exact_match:
                start_char = exact_match.start()
                pre_text = normalize_text(text_lower[:start_char])
                pre_tokens = pre_text.split()
                if not trig_has_negation and any(tok in _NEGATION_WORDS for tok in pre_tokens[-3:]):
                    continue  # Negated trigger action

                score = 0.95 if is_multiword else 0.70
                if score > best_score:
                    best_score = score
                    best_match_type = "EXACT"
                continue

            # Layer 3: Normalized Phrase Match
            found_idx = -1
            n_trig = len(trig_tokens)
            for i in range(len(norm_tokens) - n_trig + 1):
                if norm_tokens[i:i + n_trig] == trig_tokens:
                    found_idx = i
                    break

            if found_idx != -1:
                if not trig_has_negation and is_negated_match(norm_tokens, found_idx, window=3):
                    continue  # Negated trigger action

                score = 0.85 if is_multiword else 0.65
                if score > best_score:
                    best_score = score
                    best_match_type = "NORMALIZED"
                continue

            # Layer 4: Ordered Subphrase / Token Sequence Match (>= 3 words)
            if is_multiword and len(trig_tokens) >= 3 and not trig_has_negation:
                max_consec = 0
                consec_idx = -1
                for sub_len in range(len(trig_tokens) - 1, 1, -1):
                    for start in range(len(trig_tokens) - sub_len + 1):
                        sub = trig_tokens[start:start + sub_len]
                        for j in range(len(norm_tokens) - sub_len + 1):
                            if norm_tokens[j:j + sub_len] == sub:
                                if sub_len > max_consec:
                                    max_consec = sub_len
                                    consec_idx = j
                                break
                        if max_consec > 0:
                            break
                    if max_consec > 0:
                        break

                if max_consec >= 2:
                    ratio = max_consec / len(trig_tokens)
                    if ratio >= 0.75:
                        if not is_negated_match(norm_tokens, consec_idx, window=3):
                            score = 0.65 * ratio
                            if score > best_score:
                                best_score = score
                                best_match_type = "PARTIAL"
                            continue

            # Layer 5: Token Overlap (penalized, unordered fallback)
            if not trig_has_negation:
                trig_word_set = set(trig_tokens)
                text_word_set = set(norm_tokens)
                overlap = len(trig_word_set & text_word_set)
                if overlap > 0:
                    overlap_ratio = overlap / len(trig_tokens)
                    if is_multiword:
                        score = 0.55 * overlap_ratio
                    else:
                        score = 0.40 * overlap_ratio
                    if score > best_score:
                        best_score = score
                        best_match_type = "WEAK"

        threshold = 0.60
        return best_score >= threshold, best_score, best_match_type



class ModelUnavailableError(Exception):
    """Raised when the local model is unavailable or fails inference."""


@dataclass
class AgentResponse:
    """Response from an agent."""
    text: str
    agent_name: str
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    status: str = "SUCCESS"  # SUCCESS | MODEL_UNAVAILABLE | ERROR
    text_stream: Any = None  # Iterator[str] yielding tokens

@dataclass
class IntentMatch:
    spec: AgentSpec
    confidence: float
    match_type: str

@dataclass
class DispatchResult:
    primary: IntentMatch | None
    alternatives: list[IntentMatch]
    is_ambiguous: bool
    is_multi_intent: bool


class AgentRegistry:
    """Registry of all available agents.

    Agents register themselves via the @register decorator.
    The dispatcher queries this registry to find the best agent for a request.
    """

    MIN_CONFIDENCE_THRESHOLD: float = 0.60
    MIN_CONFIDENCE_MARGIN: float = 0.10

    def __init__(self):
        self._agents: dict[str, AgentSpec] = {}
        self._classes: dict[str, type] = {}
        self._default_agent: str | None = None
        self.ambiguity_margin: float = self.MIN_CONFIDENCE_MARGIN
        self.min_confidence_threshold: float = self.MIN_CONFIDENCE_THRESHOLD

    def set_default_agent(self, name: str | None) -> None:
        """Set fallback default agent when dispatch is ambiguous or no agent matches."""
        self._default_agent = name

    def get_default_agent(self) -> AgentSpec | None:
        """Get fallback default agent spec if registered."""
        if self._default_agent and self._default_agent in self._agents:
            return self._agents[self._default_agent]
        return None

    @property
    def default_agent(self) -> str | None:
        return self._default_agent

    @default_agent.setter
    def default_agent(self, name: str | None) -> None:
        self.set_default_agent(name)

    def register(
        self,
        *,
        name: str,
        commands: list[str] | None = None,
        triggers: list[str] | None = None,
        system_prompt: str = "",
        tools: list[str] | None = None,
        tier: str = "local",
        description: str = "",
        policy: AgentPolicy | None = None,
    ) -> Callable:
        """Decorator to register an agent class.

        Usage:
            @agent_registry.register(name="MyAgent", commands=["/my"])
            class MyAgent:
                def process(self, request, context) -> AgentResponse:
                    ...
        """
        def decorator(cls: type) -> type:
            spec = AgentSpec(
                name=name,
                commands=commands or [],
                triggers=triggers or [],
                system_prompt=system_prompt,
                tools=tools or [],
                tier=tier,
                description=description,
                policy=policy or AgentPolicy(),
            )
            spec._class = cls
            self._agents[name] = spec
            self._classes[name] = cls
            logger.info(f"Registered agent: {name} ({len(spec.commands)} commands, {len(spec.triggers)} triggers)")
            return cls
        return decorator

    def get(self, name: str) -> AgentSpec | None:
        """Get an agent spec by name."""
        return self._agents.get(name)

    def get_class(self, name: str) -> type | None:
        """Get an agent class by name."""
        return self._classes.get(name)

    def list_agents(self) -> list[dict]:
        """List all registered agents (for UI display)."""
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "commands": spec.commands,
                "tier": spec.tier,
            }
            for spec in self._agents.values()
        ]

    def list_commands(self) -> list[str]:
        """List all registered /commands."""
        cmds = []
        for spec in self._agents.values():
            cmds.extend(spec.commands)
        return sorted(cmds)

    def dispatch(self, text: str) -> DispatchResult:
        """Find the best agent for the given text.

        Layered matching & disambiguation:
        1. Explicit command check (priority 1.0)
        2. Candidate evaluation with layered matching confidence
        3. Ambiguity margin and tie handling
        4. Multi-intent detection ("and then", "also")

        Returns DispatchResult.
        """
        text_lower = text.lower().strip()
        
        # Check for multi-intent
        multi_intent_separators = [" and then ", " also ", " after that "]
        is_multi_intent = any(sep in text_lower for sep in multi_intent_separators)

        # 1. Explicit command check (priority 1.0)
        command_matches: list[IntentMatch] = []
        for spec in self._agents.values():
            for cmd in spec.commands:
                cmd_lower = cmd.lower().lstrip("/")
                cmd_prefix = f"/{cmd_lower}"
                if text_lower.startswith(cmd_prefix):
                    remainder = text_lower[len(cmd_prefix):]
                    if remainder == "" or remainder[0] in (" ", "\t", "\n"):
                        command_matches.append(IntentMatch(spec=spec, confidence=1.0, match_type="COMMAND"))
                        break

        if len(command_matches) == 1:
            match = command_matches[0]
            logger.info(f"Dispatched via explicit command to '{match.spec.name}' (confidence: 1.0)")
            return DispatchResult(primary=match, alternatives=[], is_ambiguous=False, is_multi_intent=is_multi_intent)
        elif len(command_matches) > 1:
            logger.warning(f"Ambiguous explicit command matches multiple agents")
            return DispatchResult(primary=None, alternatives=command_matches, is_ambiguous=True, is_multi_intent=is_multi_intent)

        # 2. Evaluate all agents
        candidates: list[IntentMatch] = []
        for spec in self._agents.values():
            can_handle, score, match_type = spec.can_handle(text)
            if can_handle and score >= self.min_confidence_threshold:
                candidates.append(IntentMatch(spec=spec, confidence=score, match_type=match_type))

        if not candidates:
            logger.info(f"No agent matched for: {text[:80]}")
            return DispatchResult(primary=None, alternatives=[], is_ambiguous=False, is_multi_intent=is_multi_intent)

        # Sort descending by score
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        if len(candidates) == 1:
            best_match = candidates[0]
            logger.info(f"Dispatched to '{best_match.spec.name}' (confidence: {best_match.confidence:.2f})")
            return DispatchResult(primary=best_match, alternatives=[], is_ambiguous=False, is_multi_intent=is_multi_intent)

        # 3. Multiple candidates: check ambiguity margin and tie handling
        best_match = candidates[0]
        second_match = candidates[1]

        if best_match.confidence == 1.0 and second_match.confidence < 1.0:
            return DispatchResult(primary=best_match, alternatives=candidates[1:], is_ambiguous=False, is_multi_intent=is_multi_intent)

        score_diff = best_match.confidence - second_match.confidence
        if score_diff < self.ambiguity_margin:
            logger.warning(
                f"Ambiguous agent dispatch between '{best_match.spec.name}' ({best_match.confidence:.2f}) and "
                f"'{second_match.spec.name}' ({second_match.confidence:.2f}) with margin {score_diff:.2f} < "
                f"{self.ambiguity_margin}."
            )
            return DispatchResult(primary=None, alternatives=candidates, is_ambiguous=True, is_multi_intent=is_multi_intent)

        logger.info(f"Dispatched to '{best_match.spec.name}' (confidence: {best_match.confidence:.2f}, margin: {score_diff:.2f})")
        return DispatchResult(primary=best_match, alternatives=candidates[1:], is_ambiguous=False, is_multi_intent=is_multi_intent)

    def instantiate(self, name: str, **kwargs) -> Any:
        """Create an instance of an agent by name."""
        cls = self._classes.get(name)
        if cls is None:
            raise ValueError(f"Agent '{name}' not registered")
        return cls(**kwargs)


# Global singleton
agent_registry = AgentRegistry()
