from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import eba_cli, workbench_projection
from scripts.publication_pipeline_fixture import (
    generate_publication_pipeline_fixture,
    generate_segment_tvp_audit_fixture,
)


class PublicationPipelineStructureTests(unittest.TestCase):
    def test_generators_reject_repo_root_output_cleanup(self) -> None:
        for generator in (generate_publication_pipeline_fixture, generate_segment_tvp_audit_fixture):
            with self.subTest(generator=generator.__name__):
                with self.assertRaises(ValueError):
                    generator(REPO_ROOT)

    def test_generators_reject_output_dir_outside_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unsafe_output = Path(tmp) / "publication-output"
            unsafe_output.mkdir()
            with self.assertRaises(ValueError):
                generate_publication_pipeline_fixture(unsafe_output)

    def test_generators_refuse_non_empty_unmarked_artifact_dir(self) -> None:
        artifacts_root = REPO_ROOT / "artifacts"
        artifacts_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts_root) as tmp:
            unowned_output = Path(tmp) / "url-stage"
            unowned_output.mkdir()
            sentinel = unowned_output / "keep-me.txt"
            sentinel.write_text("existing generated data", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-empty"):
                generate_publication_pipeline_fixture(unowned_output)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing generated data")

    def test_generators_mark_owned_output_before_recursive_cleanup(self) -> None:
        artifacts_root = REPO_ROOT / "artifacts"
        artifacts_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts_root) as tmp:
            output_dir = Path(tmp) / "publication-output"

            generate_publication_pipeline_fixture(output_dir)
            marker = output_dir / ".publication-fixture-output"
            self.assertTrue(marker.is_file())

            stale_file = output_dir / "stale.txt"
            stale_file.write_text("delete on next owned generation", encoding="utf-8")

            generate_publication_pipeline_fixture(output_dir)

            self.assertTrue(marker.is_file())
            self.assertFalse(stale_file.exists())

    def test_demo_recipes_live_in_publication_pipeline_module(self) -> None:
        import scripts.publication_pipeline.demo_recipes as demo_recipes

        self.assertIs(eba_cli.demo_recipe_lines, demo_recipes.demo_recipe_lines)

    def test_publication_projection_grouping_uses_manifest_metadata(self) -> None:
        workflow_steps = [
            {
                "id": "p4-publication-view",
                "name": "Publication view",
                "artifact_ids": ["p4-custom-view"],
            }
        ]
        artifacts = [
            {
                "id": "p2-evidence",
                "layer": 2,
                "type": "evidence_matrix",
                "parent_ids": [],
            },
            {
                "id": "p4-custom-view",
                "layer": 4,
                "type": "html",
                "kind": "custom_publication_view",
                "parent_ids": ["p2-evidence"],
                "facets": {
                    "composite_group": {
                        "kind": "custom_publication_bundle",
                        "label": "Custom Publication View",
                        "slot": "publication.custom.bundle",
                    }
                },
            },
        ]

        groups = workbench_projection.audit_report_artifact_groups(workflow_steps, artifacts)

        self.assertEqual(groups[0]["kind"], "custom_publication_bundle")
        self.assertEqual(groups[0]["slot"], "publication.custom.bundle")
        self.assertEqual(groups[0]["source"]["kind"], "manifest_declared_composite_group")

    def test_manifest_authored_facets_cannot_overwrite_canonical_projection_facets(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            root = Path(tmp)
            (root / "view.html").write_text("<h1>View</h1>", encoding="utf-8")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "audit_id": "facet-whitelist-regression",
                        "company": "Sample Co",
                        "domain": "sample.example",
                        "steps": [
                            {
                                "id": "p4-view",
                                "name": "View",
                                "artifact_ids": ["p4-view"],
                            }
                        ],
                        "artifacts": [
                            {
                                "id": "p4-view",
                                "layer": 4,
                                "type": "html",
                                "file_path": "view.html",
                                "params": {"slot": "publication.safe"},
                                "facets": {
                                    "host": "evil.example",
                                    "artifact_type": "image",
                                    "artifact_kind": "screenshot",
                                    "slot": "publication.evil",
                                    "layer": 99,
                                    "composite_group": {
                                        "kind": "custom_publication_bundle",
                                        "label": "Custom Publication View",
                                        "slot": "publication.custom.bundle",
                                    },
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            projection = workbench_projection.project_audit_manifest(manifest_path)

        artifact = next(item for item in projection["artifacts"] if item["id"] == "p4-view")
        self.assertEqual(
            artifact["facets"],
            {
                "host": "sample.example",
                "artifact_type": "html",
                "artifact_kind": "html",
                "slot": "publication.safe",
                "layer": 4,
                "composite_group": {
                    "kind": "custom_publication_bundle",
                    "label": "Custom Publication View",
                    "slot": "publication.custom.bundle",
                },
            },
        )

    def test_generic_projection_does_not_import_publication_grouping(self) -> None:
        source = inspect.getsource(workbench_projection)

        self.assertNotIn("publication_pipeline.projection_groups", source)
        self.assertNotIn("publication_view_group_config", source)

    def test_publication_fixture_script_is_compatibility_wrapper(self) -> None:
        import scripts.publication_pipeline_fixture as publication_pipeline_fixture

        source_lines = inspect.getsource(publication_pipeline_fixture).splitlines()

        self.assertLess(len(source_lines), 160)

    def test_archetype_modules_own_generators_and_builders(self) -> None:
        required_defs = {
            "scripts.publication_pipeline.base_evp": [
                "generate_publication_pipeline_fixture",
                "build_manifest",
                "report_docx_body",
            ],
            "scripts.publication_pipeline.segment_tvp": [
                "load_segment_tvp_profile",
                "build_segment_tvp_manifest",
                "segment_tvp_report_body",
                "generate_segment_tvp_audit_fixture",
            ],
            "scripts.publication_pipeline.competitor_workbook": [
                "load_competitor_workbook_profile",
                "build_competitor_workbook_manifest",
                "workbook_view_body",
                "generate_competitor_messaging_workbook_fixture",
            ],
            "scripts.publication_pipeline.dei_competitor_audit": [
                "load_dei_competitor_profile",
                "build_dei_competitor_audit_manifest",
                "dei_deck_body",
                "generate_dei_competitor_audit_fixture",
            ],
            "scripts.publication_pipeline.campaign_desk_research": [
                "load_campaign_profile",
                "build_campaign_manifest",
                "campaign_recommendation_body",
                "generate_campaign_desk_research_fixture",
            ],
            "scripts.publication_pipeline.kilos_methodology": [
                "kilos_framework",
                "build_kilos_methodology_manifest",
                "kilos_l4_body",
                "generate_kilos_methodology_fixture",
            ],
        }

        for module_name, def_names in required_defs.items():
            with self.subTest(module=module_name):
                source = inspect.getsource(import_module(module_name))
                for def_name in def_names:
                    self.assertIn(f"def {def_name}(", source)

    def test_archetype_modules_do_not_import_shared_helpers_from_sibling_archetypes(self) -> None:
        sibling_imports = {
            "scripts.publication_pipeline.competitor_workbook": [
                "from .segment_tvp import segment_tvp_table_body",
            ],
            "scripts.publication_pipeline.dei_competitor_audit": [
                "from .competitor_workbook import",
                "from .segment_tvp import segment_tvp_table_body",
            ],
            "scripts.publication_pipeline.campaign_desk_research": [
                "from .segment_tvp import segment_tvp_table_body",
            ],
            "scripts.publication_pipeline.kilos_methodology": [
                "from .segment_tvp import segment_tvp_table_body",
            ],
        }

        for module_name, forbidden_imports in sibling_imports.items():
            with self.subTest(module=module_name):
                source = inspect.getsource(import_module(module_name))
                for forbidden_import in forbidden_imports:
                    self.assertNotIn(forbidden_import, source)

    def test_core_contains_only_shared_publication_primitives(self) -> None:
        import scripts.publication_pipeline.core as core

        source = inspect.getsource(core)

        self.assertLess(len(source.splitlines()), 1200)
        for def_name in [
            "generate_publication_pipeline_fixture",
            "generate_segment_tvp_audit_fixture",
            "generate_competitor_messaging_workbook_fixture",
            "generate_dei_competitor_audit_fixture",
            "generate_campaign_desk_research_fixture",
            "generate_kilos_methodology_fixture",
            "build_segment_tvp_manifest",
            "build_competitor_workbook_manifest",
            "build_dei_competitor_audit_manifest",
            "build_campaign_manifest",
            "build_kilos_methodology_manifest",
        ]:
            self.assertNotIn(f"def {def_name}(", source)

    def test_publication_manifests_declare_composite_group_metadata(self) -> None:
        artifacts_root = REPO_ROOT / "artifacts"
        artifacts_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts_root) as tmp:
            manifest_path = generate_publication_pipeline_fixture(Path(tmp) / "publication-output")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        publication_view = next(
            artifact
            for artifact in manifest["artifacts"]
            if artifact["id"] == "p4-report-docx"
        )

        self.assertEqual(
            publication_view["facets"]["composite_group"],
            {
                "kind": "publication_report_docx_bundle",
                "label": "Report DOCX View",
                "slot": "publication.report_docx.bundle",
            },
        )

    def test_cli_uses_fixture_and_validation_registries(self) -> None:
        import scripts.fixture_registry as fixture_registry
        import scripts.validation_registry as validation_registry

        source = inspect.getsource(eba_cli)

        self.assertIs(eba_cli.FIXTURE_GENERATORS, fixture_registry.FIXTURE_GENERATORS)
        self.assertIs(eba_cli.COMPILE_TARGETS, validation_registry.COMPILE_TARGETS)
        self.assertIs(eba_cli.validation_commands, validation_registry.validation_commands)
        self.assertNotIn('"publication-pipeline": generate_publication_pipeline_fixture', source)
        self.assertNotIn('"scripts/publication_pipeline/core.py"', source)
        self.assertLess(len(source.splitlines()), 1000)


if __name__ == "__main__":
    unittest.main()
