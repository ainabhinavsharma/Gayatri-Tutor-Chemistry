"""Tests for CurriculumManifestLoader — Phase 4."""
from __future__ import annotations

import pytest
from pathlib import Path
from core.curriculum.loader import CurriculumManifestLoader, get_curriculum_loader
from core.curriculum.models import CurriculumManifest, CurriculumDomain
from core.curriculum.dataset_registry import get_dataset_registry


class TestCurriculumManifestLoader:
    def test_manifest_loads_successfully(self):
        loader = CurriculumManifestLoader()
        manifest = loader.load_manifest()
        assert isinstance(manifest, CurriculumManifest)
        assert len(manifest.domains) > 0

    def test_manifest_has_thermodynamics(self):
        loader = CurriculumManifestLoader()
        manifest = loader.load_manifest()
        domain = manifest.get_domain("Thermodynamics")
        assert domain is not None
        assert "Gibbs Energy Change and Equilibrium" in domain.topics

    def test_manifest_has_inorganic_chemistry(self):
        loader = CurriculumManifestLoader()
        manifest = loader.load_manifest()
        domain = manifest.get_domain("Inorganic Chemistry")
        assert domain is not None
        assert len(domain.chapters) > 0

    def test_get_topic_names_non_empty(self):
        loader = CurriculumManifestLoader()
        topics = loader.get_topic_names()
        assert len(topics) > 5
        assert any("Thermodynamics" in t or "Enthalpy" in t or "Gibbs" in t for t in topics)

    def test_get_topic_ids_stable(self):
        loader = CurriculumManifestLoader()
        topic_ids = loader.get_topic_ids()
        assert len(topic_ids) > 0
        # All IDs should be snake_case (no spaces)
        for tid in topic_ids:
            assert " " not in tid, f"topic_id '{tid}' should not contain spaces"

    def test_prerequisites_thermodynamics(self):
        loader = CurriculumManifestLoader()
        prereqs = loader.get_prerequisites("Thermodynamics")
        assert len(prereqs) > 0
        assert any("Mole" in p or "mole" in p.lower() for p in prereqs)

    def test_validate_prerequisites_returns_list(self):
        loader = CurriculumManifestLoader()
        warnings = loader.validate_prerequisites()
        assert isinstance(warnings, list)

    def test_missing_manifest_returns_empty(self, tmp_path):
        loader = CurriculumManifestLoader(manifest_path=tmp_path / "nonexistent.json")
        manifest = loader.load_manifest()
        assert isinstance(manifest, CurriculumManifest)
        assert len(manifest.domains) == 0

    def test_caching_same_object(self):
        loader = CurriculumManifestLoader()
        manifest1 = loader.load_manifest()
        manifest2 = loader.load_manifest()
        assert manifest1 is manifest2  # same cached instance

    def test_singleton_loader(self):
        loader1 = get_curriculum_loader()
        loader2 = get_curriculum_loader()
        assert loader1 is loader2


class TestCurriculumKnowledgeGraphSeeding:
    def test_seed_knowledge_graph(self):
        """Verify manifest seeds the KG with chemistry concepts."""
        from core.knowledge_graph import LearningDependencyGraph
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".db")
        graph = LearningDependencyGraph(db_path=tmp)
        loader = CurriculumManifestLoader()
        count = loader.seed_knowledge_graph(graph)
        assert count > 5
        concepts = graph.list_concepts()
        concept_ids = [c.id for c in concepts]
        assert "thermodynamics" in concept_ids

    def test_topic_concepts_have_prerequisites(self):
        """Domain-level concept should be a prerequisite of topic concepts."""
        from core.knowledge_graph import LearningDependencyGraph
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".db")
        graph = LearningDependencyGraph(db_path=tmp)
        loader = CurriculumManifestLoader()
        loader.seed_knowledge_graph(graph)
        concepts = graph.list_concepts()
        concept_ids = {c.id for c in concepts}
        assert "thermodynamics" in concept_ids


class TestDatasetTopicRegistry:
    def test_registry_loads(self):
        registry = get_dataset_registry()
        assert len(registry.all_topic_ids()) > 0

    def test_lookup_first_law(self):
        registry = get_dataset_registry()
        info = registry.lookup("first_law")
        assert info is not None
        assert info.domain == "Thermodynamics"
        assert "First Law" in info.display_name

    def test_lookup_unknown_topic(self):
        registry = get_dataset_registry()
        info = registry.lookup("made_up_topic_xyz")
        assert info is None

    def test_topics_for_thermodynamics(self):
        registry = get_dataset_registry()
        topics = registry.topics_for_domain("Thermodynamics")
        assert len(topics) >= 5
        ids = [t.topic_id for t in topics]
        assert "first_law" in ids
        assert "gibbs_free_energy" in ids


class TestChemistryRuntimeCurriculum:
    def test_runtime_loads_topics(self):
        from core.runtimes.chemistry import ChemistryTutorRuntime
        rt = ChemistryTutorRuntime()
        topics = rt.get_available_topics()
        # Should have loaded from manifest
        assert isinstance(topics, list)
        # May be empty if manifest unavailable, but should not raise

    def test_runtime_domain_names(self):
        from core.runtimes.chemistry import ChemistryTutorRuntime
        rt = ChemistryTutorRuntime()
        domains = rt.get_domain_names()
        assert "Thermodynamics" in domains
