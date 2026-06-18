"""Validation command registry for `./eba dev validate`."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts.artifact_type_manifest import artifact_type_script_paths
except ModuleNotFoundError:
    from artifact_type_manifest import artifact_type_script_paths


REPO_ROOT = Path(__file__).resolve().parent.parent

COMPILE_TARGETS = [
    "scripts/easy_audit_fixture.py",
    "scripts/easy_audit_site_capture_smoke.py",
    "scripts/fixture_registry.py",
    "scripts/image_normalization_bridge.py",
    "scripts/playwright_cli_public_page_matrix_smoke.py",
    "scripts/playwright_cli_public_page_smoke.py",
    "scripts/playwright_cli_capture_modes_smoke.py",
    "scripts/playwright_cli_finalize_approval.py",
    "scripts/playwright_cli_workbench_server.py",
    "scripts/playwright_cli_workbench_gate.py",
    "scripts/playwright_cli_browser.py",
    "scripts/workbench_bounded_input.py",
    "scripts/workbench_projection.py",
    "scripts/workbench_projection_shape_check.py",
    "scripts/url_stage_capture.py",
    "scripts/publication_pipeline_fixture.py",
    "scripts/publication_pipeline/__init__.py",
    "scripts/publication_pipeline/base_evp.py",
    "scripts/publication_pipeline/campaign_desk_research.py",
    "scripts/publication_pipeline/competitor_workbook.py",
    "scripts/publication_pipeline/core.py",
    "scripts/publication_pipeline/dei_competitor_audit.py",
    "scripts/publication_pipeline/demo_recipes.py",
    "scripts/publication_pipeline/html_views.py",
    "scripts/publication_pipeline/kilos_methodology.py",
    "scripts/publication_pipeline/projection_groups.py",
    "scripts/publication_pipeline/segment_tvp.py",
    "scripts/publication_pipeline/workbook_shared.py",
    "scripts/artifact_type_manifest.py",
    "scripts/eba_cli.py",
    "scripts/eba_commit_msg_hook.py",
    "scripts/eba_signature.py",
    "scripts/validation_registry.py",
]


def validation_commands() -> list[list[str]]:
    commands = [
        [sys.executable, "-m", "py_compile", *COMPILE_TARGETS],
        [sys.executable, "tests/test_workbench_bounded_input.py"],
        [sys.executable, "tests/test_workbench_server_hardening.py"],
        [sys.executable, "tests/test_easy_audit_fixture.py"],
        [sys.executable, "tests/test_publication_pipeline_fixture.py"],
        [sys.executable, "tests/test_publication_default_samples.py"],
        [sys.executable, "tests/test_publication_pipeline_structure.py"],
        [sys.executable, "tests/test_publication_capture_pack.py"],
        [sys.executable, "tests/test_publication_segment_tvp.py"],
        [sys.executable, "tests/test_publication_competitor_workbook.py"],
        [sys.executable, "tests/test_publication_dei_competitor_audit.py"],
        [sys.executable, "tests/test_publication_campaign_desk_research.py"],
        [sys.executable, "tests/test_publication_kilos_methodology.py"],
        [sys.executable, "tests/test_artifact_workbench_browser_control.py"],
        [sys.executable, "tests/test_url_stage_capture.py"],
        [sys.executable, "scripts/workbench_projection_shape_check.py"],
        ["node", "--check", "scripts/artifact_primitives/mermaid_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/markdown_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/markdown_interactions.js"],
        ["node", "--check", "scripts/artifact_primitives/zoom_surface.js"],
        ["node", "--check", "scripts/artifact_primitives/image_viewer.js"],
        ["node", "--check", "scripts/artifact_primitives/document_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/html_renderer.js"],
        ["node", "--check", "scripts/artifacts/core/artifact_common.js"],
        ["node", "--check", "scripts/artifacts/core/bounded_input_controls.js"],
        ["node", "--check", "scripts/artifacts/core/workflow_pairing.js"],
        ["node", "--check", "scripts/artifacts/core/zoom_controls.js"],
        *[["node", "--check", script_path] for script_path in artifact_type_script_paths()],
        ["node", "--check", "scripts/artifacts/artifact_registry.js"],
        ["node", "--check", "scripts/artifact_primitives/artifact_renderer.js"],
        ["node", "--check", "scripts/artifacts/navigation/artifact_navigator.js"],
        ["node", "--check", "scripts/artifact_primitives/interaction_overlay.js"],
        ["node", "--check", "scripts/artifact_primitives/target_link.js"],
        ["node", "--check", "scripts/artifact_primitives/interaction_overlay_controller.js"],
        ["node", "tests/markdown_renderer_primitive_check.js"],
        ["node", "tests/document_renderer_primitive_check.js"],
        ["node", "tests/html_renderer_primitive_check.js"],
        ["node", "tests/zoom_surface_primitive_check.js"],
        ["node", "tests/artifact_registry_check.js"],
        ["node", "tests/artifact_renderer_primitive_check.js"],
        ["node", "tests/artifact_toolbar_check.js"],
        ["node", "tests/artifact_binding_check.js"],
        ["node", "tests/artifact_navigator_check.js"],
        ["node", "tests/bounded_input_controls_check.js"],
        ["node", "tests/workflow_pairing_check.js"],
        ["node", "tests/workbench_shell_check.js"],
        ["node", "tests/interaction_overlay_primitive_check.js"],
        ["node", "tests/target_link_primitive_check.js"],
        ["node", "tests/interaction_overlay_controller_check.js"],
        ["node", "--check", "scripts/artifact_workbench/app.js"],
        ["node", "--check", "scripts/artifact_workbench/artifact_toolbar.js"],
        ["node", "--check", "scripts/artifact_workbench/artifact_binding.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-composition-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-document-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-image-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-layout-regression-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-markdown-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-report-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-live-boot-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-mermaid-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-navigation-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-annotation-reorder-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-interaction-overlay-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-bounded-input-check.js"],
        ["node", "--check", "scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js"],
        ["node", "--check", "scripts/playwright-snippets/settle-page.js"],
        ["node", "--check", "scripts/playwright-snippets/hide-obscuring-elements.js"],
        ["node", "--check", "scripts/playwright-snippets/restore-page.js"],
        ["node", "--check", "scripts/playwright-snippets/extract-visible-text.js"],
        ["node", "--check", "scripts/playwright-snippets/extract-web-blueprint.js"],
    ]
    venv_python = REPO_ROOT / "mcp-server" / ".venv" / "bin" / "python"
    pytest = REPO_ROOT / "mcp-server" / ".venv" / "bin" / "pytest"
    if pytest.exists():
        commands.append(
            [str(venv_python), "-m", "pytest", "-q", "tests/test_eba_control_plane.py"]
        )
        commands.append([str(pytest), "-q", "mcp-server/tests"])
    commands.append(["git", "diff", "--check"])
    return commands
