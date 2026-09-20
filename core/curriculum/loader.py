"""Gayatri AI — Curriculum manifest loader.

Parses training/curriculum/chemistry/curriculum_manifest.json
into typed CurriculumManifest objects and exposes query helpers.
Also contains the legacy shim `load_curriculum` for the KnowledgeGraph provider.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from core.curriculum.models import CurriculumDomain, CurriculumManifest

logger = logging.getLogger("gayatri.curriculum.loader")

# Canonical paths to the curriculum manifest
_DATA_CURRICULUM_PATH = Path(__file__).parent.parent.parent / "data" / "curriculum" / "chemistry" / "ncert_class11_12.json"
_MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "curriculum" / "chemistry" / "curriculum_manifest.json"


class CurriculumManifestLoader:
    """Loads and queries the NCERT/CBSE chemistry curriculum manifest."""

    def __init__(self, manifest_path: str | Path | None = None):
        if manifest_path:
            self._path = Path(manifest_path)
        elif _MANIFEST_PATH.exists():
            self._path = _MANIFEST_PATH
        elif _DATA_CURRICULUM_PATH.exists():
            self._path = _DATA_CURRICULUM_PATH
        else:
            self._path = _MANIFEST_PATH
        self._manifest: Optional[CurriculumManifest] = None

    def load_manifest(self) -> CurriculumManifest:
        """Parse the curriculum manifest into a typed CurriculumManifest.
        Caches the result after first load.
        """
        if self._manifest is not None:
            return self._manifest

        if not self._path.exists():
            raise FileNotFoundError(f"Curriculum manifest not found at {self._path}")

        with open(self._path, encoding="utf-8-sig") as f:
            data = json.load(f)

        domains = []
        if "domains" in data:
            for raw in data.get("domains", []):
                domains.append(
                    CurriculumDomain(
                        name=raw.get("name", ""),
                        classes=raw.get("classes", []),
                        chapters=raw.get("chapters", []),
                        topics=raw.get("topics", []),
                        subtopics=raw.get("subtopics", []),
                        learning_outcomes=raw.get("learning_outcomes", []),
                        prerequisites=raw.get("prerequisites", []),
                    )
                )
        elif "concepts" in data:
            # Parse from ncert_class11_12.json structure
            concepts = data.get("concepts", [])
            thermo_concepts = [c for c in concepts if "thermo" in c.get("id", "")]
            inorg_concepts = [c for c in concepts if "thermo" not in c.get("id", "")]

            if thermo_concepts:
                domains.append(
                    CurriculumDomain(
                        name="Thermodynamics",
                        classes=["Class 11"],
                        chapters=["Thermodynamics"],
                        topics=[c["name"] for c in thermo_concepts],
                        subtopics=[c.get("description", "") for c in thermo_concepts],
                        learning_outcomes=["Understand enthalpy, entropy, Gibbs energy, and thermochemical laws"],
                        prerequisites=["System and Surroundings"],
                    )
                )
            if inorg_concepts:
                domains.append(
                    CurriculumDomain(
                        name="Inorganic Chemistry",
                        classes=["Class 11", "Class 12"],
                        chapters=["Classification of Elements", "Chemical Bonding", "s-Block Elements", "p-Block Elements"],
                        topics=[c["name"] for c in inorg_concepts],
                        subtopics=[c.get("description", "") for c in inorg_concepts],
                        learning_outcomes=["Understand periodic trends, bonding, and group element reactions"],
                        prerequisites=["Periodic Table Trends"],
                    )
                )

        self._manifest = CurriculumManifest(domains=domains)
        logger.info(
            f"Loaded chemistry manifest: {len(domains)} domains, "
            f"{len(self._manifest.all_topics())} topics"
        )
        return self._manifest

    def get_topic_names(self) -> list[str]:
        """Return flat list of all topic names across all domains."""
        return self.load_manifest().all_topics()

    def get_topic_ids(self) -> list[str]:
        """Return flat list of all stable topic IDs across all domains."""
        return self.load_manifest().all_topic_ids()

    def get_prerequisites(self, domain_name: str) -> list[str]:
        """Return prerequisite list for a given domain."""
        manifest = self.load_manifest()
        domain = manifest.get_domain(domain_name)
        return domain.prerequisites if domain else []

    def validate_prerequisites(self) -> list[str]:
        """Check for any obviously broken prerequisite references.
        Since prerequisites are free-text (not IDs) in this manifest,
        we just return them for informational purposes.
        Returns list of (domain_name, prerequisite_text) that reference
        a topic not covered in any domain.
        """
        manifest = self.load_manifest()
        all_topics_lower = {t.lower() for t in manifest.all_topics()}
        all_subtopics_lower = {s.lower() for d in manifest.domains for s in d.subtopics}
        covered = all_topics_lower | all_subtopics_lower

        warnings = []
        for domain in manifest.domains:
            for prereq in domain.prerequisites:
                if prereq.lower() not in covered:
                    warnings.append(f"{domain.name}: '{prereq}' not in any topic/subtopic list")
        return warnings

    def seed_knowledge_graph(self, graph) -> int:
        """Populate a LearningDependencyGraph from the curriculum manifest.

        Each domain becomes a concept node; each topic inside it also becomes
        a node with the domain as a prerequisite.
        Returns total concepts added.
        """
        manifest = self.load_manifest()
        count = 0

        for domain in manifest.domains:
            domain_id = domain.domain_id()
            # Add the domain itself as a top-level concept
            graph.add_concept(
                concept_id=domain_id,
                name=domain.name,
                description=f"NCERT {domain.name} domain: {', '.join(domain.chapters[:2])}",
                difficulty=0.5,
                subject="chemistry",
                minimum_mastery=0.7,
                evidence_count=5,
                assessment_types=["conceptual", "numerical"],
            )
            count += 1

            # Add each topic as a child concept
            for topic, topic_id in zip(domain.topics, domain.topic_ids()):
                graph.add_concept(
                    concept_id=topic_id,
                    name=topic,
                    description=f"Part of {domain.name} ({', '.join(domain.classes)})",
                    difficulty=0.5,
                    subject="chemistry",
                    minimum_mastery=0.7,
                    evidence_count=3,
                    assessment_types=["conceptual", "numerical"],
                )
                graph.add_prerequisite(topic_id, domain_id)
                count += 1

        logger.info(f"Seeded knowledge graph with {count} chemistry concepts from manifest")
        return count


# Singleton loader instance
_loader: Optional[CurriculumManifestLoader] = None


def get_curriculum_loader() -> CurriculumManifestLoader:
    """Return singleton CurriculumManifestLoader."""
    global _loader
    if _loader is None:
        _loader = CurriculumManifestLoader()
    return _loader


def load_curriculum(graph, curriculum_path: str | Path) -> int:
    """Legacy shim: load a curriculum JSON file into the LDG (old format)."""
    path = Path(curriculum_path)
    if not path.exists():
        raise FileNotFoundError(f"load_curriculum: curriculum file not found at {path}")

    import json as _json
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)

    from core.curriculum.provider import CurriculumProvider
    subject = data.get("subject", "unknown")
    provider = CurriculumProvider(subject=subject, grade="unknown")
    provider.file_path = path
    return provider.load_into(graph)
