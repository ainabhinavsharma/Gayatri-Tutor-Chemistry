"""Gayatri AI — Curriculum domain models.

Typed representations of the NCERT/CBSE chemistry curriculum manifest.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CurriculumDomain:
    """A single domain (e.g. Thermodynamics, Inorganic Chemistry) from the manifest."""
    name: str
    classes: list[str] = field(default_factory=list)
    chapters: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    subtopics: list[str] = field(default_factory=list)
    learning_outcomes: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def domain_id(self) -> str:
        """Stable snake_case ID derived from the domain name."""
        return self.name.lower().replace(" ", "_").replace("-", "_")

    def topic_ids(self) -> list[str]:
        """Return stable snake_case topic IDs for each topic string."""
        return [t.lower().replace(" ", "_").replace(",", "").replace("'", "").replace("-", "_")
                for t in self.topics]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain_id": self.domain_id(),
            "classes": self.classes,
            "chapters": self.chapters,
            "topics": self.topics,
            "subtopics": self.subtopics,
            "learning_outcomes": self.learning_outcomes,
            "prerequisites": self.prerequisites,
        }


@dataclass
class CurriculumManifest:
    """The full chemistry curriculum manifest, a collection of domains."""
    domains: list[CurriculumDomain] = field(default_factory=list)

    def get_domain(self, name: str) -> CurriculumDomain | None:
        """Look up a domain by name (case-insensitive)."""
        for d in self.domains:
            if d.name.lower() == name.lower():
                return d
        return None

    def all_topics(self) -> list[str]:
        """Return all topics across all domains."""
        return [topic for d in self.domains for topic in d.topics]

    def all_topic_ids(self) -> list[str]:
        """Return all stable topic IDs across all domains."""
        return [tid for d in self.domains for tid in d.topic_ids()]

    def domain_names(self) -> list[str]:
        """Return all domain names."""
        return [d.name for d in self.domains]

    def supported_classes(self) -> list[str]:
        """Return sorted unique class levels across all domains."""
        seen = set()
        for d in self.domains:
            seen.update(d.classes)
        return sorted(seen)
