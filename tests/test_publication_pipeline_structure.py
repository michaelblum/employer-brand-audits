from __future__ import annotations

import inspect
import sys
import tempfile
import unittest
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

    def test_demo_recipes_live_in_publication_pipeline_module(self) -> None:
        import scripts.publication_pipeline.demo_recipes as demo_recipes

        self.assertIs(eba_cli.demo_recipe_lines, demo_recipes.demo_recipe_lines)

    def test_publication_projection_grouping_lives_in_publication_pipeline_module(self) -> None:
        import scripts.publication_pipeline.projection_groups as projection_groups

        self.assertIs(workbench_projection.publication_view_group_config, projection_groups.publication_view_group_config)

    def test_publication_fixture_script_is_compatibility_wrapper(self) -> None:
        import scripts.publication_pipeline_fixture as publication_pipeline_fixture

        source_lines = inspect.getsource(publication_pipeline_fixture).splitlines()

        self.assertLess(len(source_lines), 160)


if __name__ == "__main__":
    unittest.main()
