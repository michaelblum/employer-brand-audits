from __future__ import annotations

import json
import contextlib
import io
import argparse
import re
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import playwright_cli_workbench_gate as gate


class ArtifactWorkbenchBrowserControlTests(unittest.TestCase):
    def test_browser_control_tests_are_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        self.assertIn(
            [sys.executable, "tests/test_artifact_workbench_browser_control.py"],
            validation_commands(),
        )

    def test_document_renderer_primitive_is_served_and_validated(self) -> None:
        from scripts.eba_cli import validation_commands
        from scripts.playwright_cli_workbench_server import WORKBENCH_ASSETS

        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/document_renderer.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/html_renderer.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/artifact_renderer.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/core/artifact_common.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/types/image_artifact.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/types/markdown_artifact.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/types/html_artifact.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/types/document_artifact.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/artifact_registry.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifacts/navigation/artifact_navigator.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/interaction_overlay.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/target_link.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/interaction_overlay_controller.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_navigator_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/document_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/html_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_toolbar_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_binding_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_registry_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/interaction_overlay_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/target_link_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/interaction_overlay_controller_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/markdown_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/markdown_renderer.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/markdown_interactions.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/image_viewer.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_workbench/artifact_toolbar.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_workbench/artifact_binding.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-image-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-markdown-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-report-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-live-boot-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-navigation-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-annotation-reorder-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/artifact-workbench-bounded-input-check.js"],
            validation_commands(),
        )
        self.assertIn("/assets/artifact-primitives/document_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/html_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/core/artifact_common.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/types/image_artifact.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/types/markdown_artifact.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/types/html_artifact.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/types/document_artifact.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/artifact_registry.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/artifact_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_interactions.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/image_viewer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifacts/navigation/artifact_navigator.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/interaction_overlay.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/target_link.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/interaction_overlay_controller.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-toolbar.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-binding.js", WORKBENCH_ASSETS)

    def test_workbench_index_references_served_assets_and_icons(self) -> None:
        from scripts.playwright_cli_workbench_server import WORKBENCH_ASSETS, WORKBENCH_INDEX

        html = WORKBENCH_INDEX.read_text(encoding="utf-8")
        refs = set(re.findall(r"""(?:src|href)=["']([^"']+)["']""", html))
        asset_refs = {ref.split("#", 1)[0] for ref in refs if ref.startswith("/assets/")}
        self.assertGreater(len(asset_refs), 0)
        self.assertEqual(set(), asset_refs - set(WORKBENCH_ASSETS))

        icon_file = WORKBENCH_ASSETS["/assets/artifact-workbench-icons.svg"][0]
        icon_text = icon_file.read_text(encoding="utf-8")
        icon_ids = set(re.findall(r"""<symbol[^>]+id=["']([^"']+)["']""", icon_text))
        index_icon_refs = {
            ref.split("#", 1)[1]
            for ref in refs
            if ref.startswith("/assets/artifact-workbench-icons.svg#")
        }
        module_icon_refs = set()
        for path, _content_type in WORKBENCH_ASSETS.values():
            if path.suffix != ".js":
                continue
            source = path.read_text(encoding="utf-8")
            module_icon_refs.update(re.findall(r"""renderIconUse\(["']([^"']+)["']\)""", source))
            module_icon_refs.update(re.findall(r"""/assets/artifact-workbench-icons\.svg#([^"'`<>\s)]+)""", source))
        module_icon_refs = {ref for ref in module_icon_refs if "${" not in ref}
        self.assertEqual(set(), (index_icon_refs | module_icon_refs) - icon_ids)

    def test_active_workbench_names_do_not_regress_to_stale_workflow_or_review_terms(self) -> None:
        forbidden = [
            "workflow" + "_artifact_workbench",
            "workflow" + "-artifact-workbench",
            "workflow" + "-artifact-toolbar",
            "Workflow" + "ArtifactWorkbench",
            "workflow" + "-summary",
            "Workflow" + " summary",
            "review" + "-workbench",
            "review" + "_workbench",
        ]
        search_roots = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "docs" / "superpowers" / "project-sop.md",
            REPO_ROOT / "docs" / "AGENTS.md",
            REPO_ROOT / "scripts",
            REPO_ROOT / "tests",
        ]
        offenders: list[str] = []
        for root in search_roots:
            paths = [root] if root.is_file() else [
                path for path in root.rglob("*")
                if path.is_file() and ".pyc" not in path.suffixes
            ]
            for path in paths:
                if any(part in {"__pycache__", "vendor"} for part in path.parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for token in forbidden:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")
        self.assertEqual([], offenders)

    def test_browser_open_plan_uses_named_repo_wrapper_session(self) -> None:
        plan = gate.build_workbench_browser_plan(
            "http://127.0.0.1:8765/",
            session="eba-workbench",
            browser="chrome",
            viewport_size=None,
        )

        self.assertEqual(plan["session"], "eba-workbench")
        self.assertEqual(plan["profile"], "chrome-profile/workbench")
        self.assertEqual(
            plan["open_command"],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "open",
                "http://127.0.0.1:8765/",
                "--session",
                "eba-workbench",
                "--browser",
                "chrome",
                "--persistent",
                "--profile",
                "chrome-profile/workbench",
                "--config",
                "scripts/playwright_cli_workbench_config.json",
            ],
        )
        config_path = REPO_ROOT / plan["config"]
        self.assertTrue(config_path.exists())
        config = json.loads(config_path.read_text(encoding="utf-8"))
        args = config["browser"]["launchOptions"]["args"]
        self.assertIn("--disable-infobars", args)
        self.assertIn("--no-first-run", args)
        self.assertIn("--no-default-browser-check", args)
        self.assertIn("--test-type", args)
        self.assertEqual(
            plan["window_maximize_command"],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "window-maximize",
                "--session",
                "eba-workbench",
            ],
        )
        self.assertEqual(
            plan["window_focus_command"],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "window-focus",
                "--session",
                "eba-workbench",
            ],
        )
        self.assertEqual(
            plan["close_command"],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "close",
                "--session",
                "eba-workbench",
            ],
        )
        self.assertIsNone(plan["initial_resize_command"])

    def test_browser_wrapper_exposes_tab_close_for_workbench_cleanup(self) -> None:
        parser = __import__("scripts.playwright_cli_browser", fromlist=["build_parser"]).build_parser()

        args = parser.parse_args(["tab-close", "3", "--session", "eba-workbench"])

        self.assertEqual(args.command, "tab-close")
        self.assertEqual(args.index, 3)
        self.assertEqual(args.session, "eba-workbench")

    def test_workbench_tab_cleanup_closes_blank_and_duplicate_workbench_tabs(self) -> None:
        commands: list[list[str]] = []

        class Result:
            returncode = 0
            stderr = ""

            def __init__(self, stdout: str = "") -> None:
                self.stdout = stdout

        tab_list = """+ wrapper echo
### Result
- 0: (current) [EBA Workbench](http://127.0.0.1:8765/)
- 1: [](about:blank)
- 2: [EBA Workbench](http://127.0.0.1:8765/)
- 3: [](about:blank)
- 4: [Docs](http://127.0.0.1:8765/docs)
- 5: [](about:blank)
- 6: [EBA Workbench](http://127.0.0.1:8765/)
"""

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            if command[2] == "tab-list":
                return Result(tab_list)
            return Result()

        original_run = gate.run_browser_command
        try:
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            with io.StringIO() as log:
                result = gate.clean_workbench_tabs(
                    "http://127.0.0.1:8765/",
                    session="eba-workbench",
                    log_handle=log,
                )
        finally:
            gate.run_browser_command = original_run  # type: ignore[assignment]

        self.assertEqual(result["kept_index"], 0)
        self.assertEqual(result["closed_indexes"], [6, 5, 3, 2, 1])
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-list",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-close",
                    "6",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-close",
                    "5",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-close",
                    "3",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-close",
                    "2",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-close",
                    "1",
                    "--session",
                    "eba-workbench",
                ],
            ],
        )

    def test_workbench_tab_cleanup_selects_existing_workbench_tab_before_closing_current_blank(
        self,
    ) -> None:
        commands: list[list[str]] = []

        class Result:
            returncode = 0
            stderr = ""

            def __init__(self, stdout: str = "") -> None:
                self.stdout = stdout

        tab_list = """### Result
- 0: (current) [](about:blank)
- 1: [EBA Workbench](http://127.0.0.1:8765/)
- 2: [](about:blank)
"""

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            if command[2] == "tab-list":
                return Result(tab_list)
            return Result()

        original_run = gate.run_browser_command
        try:
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            with io.StringIO() as log:
                result = gate.clean_workbench_tabs(
                    "http://127.0.0.1:8765/",
                    session="eba-workbench",
                    log_handle=log,
                )
        finally:
            gate.run_browser_command = original_run  # type: ignore[assignment]

        self.assertEqual(result["kept_index"], 1)
        self.assertEqual(result["closed_indexes"], [2, 0])
        self.assertEqual(commands[1], [
            sys.executable,
            "scripts/playwright_cli_browser.py",
            "tab-select",
            "1",
            "--session",
            "eba-workbench",
        ])

    def test_workbench_profile_cleanup_suppresses_chrome_restore_prompt_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            profile = Path(tmp) / "profile"
            default = profile / "Default"
            default.mkdir(parents=True)
            preferences = {
                "profile": {
                    "exit_type": "Crashed",
                    "exited_cleanly": False,
                },
                "sessions": {
                    "event_log": [
                        {"type": 0, "crashed": True},
                        {"type": 5, "restore_browser": True},
                    ],
                    "session_data_status": 1,
                },
            }
            local_state = {
                "user_experience_metrics": {
                    "stability": {
                        "exited_cleanly": False,
                    }
                }
            }
            (default / "Preferences").write_text(json.dumps(preferences), encoding="utf-8")
            (profile / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

            gate.sanitize_workbench_browser_profile(profile)

            cleaned_preferences = json.loads((default / "Preferences").read_text(encoding="utf-8"))
            cleaned_local_state = json.loads((profile / "Local State").read_text(encoding="utf-8"))
            self.assertEqual("Normal", cleaned_preferences["profile"]["exit_type"])
            self.assertTrue(cleaned_preferences["profile"]["exited_cleanly"])
            self.assertEqual([], cleaned_preferences["sessions"]["event_log"])
            self.assertTrue(
                cleaned_local_state["user_experience_metrics"]["stability"]["exited_cleanly"]
            )

    def test_browser_open_plan_keeps_explicit_viewport_resize_available(self) -> None:
        plan = gate.build_workbench_browser_plan(
            "http://127.0.0.1:8765/",
            session="eba-workbench",
            browser="chrome",
            viewport_size="1440,1000",
        )

        self.assertEqual(
            plan["initial_resize_command"],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "resize",
                "1440",
                "1000",
                "--session",
                "eba-workbench",
            ],
        )
        self.assertIn("--config", plan["open_command"])

    def test_reused_browser_session_syncs_when_display_state_changes(self) -> None:
        commands: list[list[str]] = []
        statuses = [
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
        ]

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_status(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return statuses.pop(0)

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            return Result()

        def fake_metrics(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return {
                "innerWidth": 1484,
                "innerHeight": 949,
                "outerWidth": 1512,
                "outerHeight": 949,
                "screenX": 0,
                "screenY": 33,
                "devicePixelRatio": 1,
                "screenAvailLeft": 0,
                "screenAvailTop": 0,
                "screenAvailWidth": 1484,
                "screenAvailHeight": 883,
            }

        original_require_cli = gate.require_session_aware_cli
        original_require_wrapper = gate.require_workbench_browser_wrapper
        original_status = gate.browser_session_status
        original_run = gate.run_browser_command
        original_metrics = gate.browser_page_metrics
        try:
            gate.require_session_aware_cli = lambda: "playwright-cli"  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = lambda: gate.BROWSER_WRAPPER  # type: ignore[assignment]
            gate.browser_session_status = fake_status  # type: ignore[assignment]
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            gate.browser_page_metrics = fake_metrics  # type: ignore[assignment]

            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                root = Path(tmp)
                (root / "workbench-browser-state.json").write_text(
                    json.dumps(
                        {
                            "display_signature": {
                                "screenX": -1920,
                                "screenY": 33,
                                "screenAvailLeft": 0,
                                "screenAvailTop": 0,
                                "screenAvailWidth": 1920,
                                "screenAvailHeight": 1080,
                                "devicePixelRatio": 1,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                result = gate.open_with_playwright(
                    "http://127.0.0.1:8765/",
                    {
                        "artifact_root": root,
                        "browser_log": root / "workbench-browser.log",
                        "browser_state": root / "workbench-browser-state.json",
                    },
                    "chrome",
                    None,
                    session="eba-workbench",
                    profile=REPO_ROOT / "chrome-profile" / "workbench",
                )
        finally:
            gate.require_session_aware_cli = original_require_cli  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = original_require_wrapper  # type: ignore[assignment]
            gate.browser_session_status = original_status  # type: ignore[assignment]
            gate.run_browser_command = original_run  # type: ignore[assignment]
            gate.browser_page_metrics = original_metrics  # type: ignore[assignment]

        self.assertTrue(result["reused"])
        self.assertFalse(result["resized"])
        self.assertTrue(result["window_maximized"])
        self.assertTrue(result["window_focused"])
        self.assertTrue(result["viewport_synced"])
        self.assertEqual(result["viewport_target"], (1484, 883))
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "goto",
                    "http://127.0.0.1:8765/",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "tab-list",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "window-maximize",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "resize",
                    "1484",
                    "883",
                    "--session",
                    "eba-workbench",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "window-focus",
                    "--session",
                    "eba-workbench",
                ],
            ],
        )

    def test_reused_browser_session_skips_reset_when_display_state_matches(self) -> None:
        commands: list[list[str]] = []
        statuses = [
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
        ]

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_status(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return statuses.pop(0)

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            return Result()

        def fake_metrics(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return {
                "innerWidth": 1484,
                "innerHeight": 916,
                "outerWidth": 1512,
                "outerHeight": 949,
                "screenX": 0,
                "screenY": 33,
                "devicePixelRatio": 1,
                "screenAvailLeft": 0,
                "screenAvailTop": 0,
                "screenAvailWidth": 1484,
                "screenAvailHeight": 949,
            }

        original_require_cli = gate.require_session_aware_cli
        original_require_wrapper = gate.require_workbench_browser_wrapper
        original_status = gate.browser_session_status
        original_run = gate.run_browser_command
        original_metrics = gate.browser_page_metrics
        try:
            gate.require_session_aware_cli = lambda: "playwright-cli"  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = lambda: gate.BROWSER_WRAPPER  # type: ignore[assignment]
            gate.browser_session_status = fake_status  # type: ignore[assignment]
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            gate.browser_page_metrics = fake_metrics  # type: ignore[assignment]

            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                root = Path(tmp)
                (root / "workbench-browser-state.json").write_text(
                    json.dumps(
                        {
                            "display_signature": {
                                "screenX": 0,
                                "screenY": 33,
                                "screenAvailLeft": 0,
                                "screenAvailTop": 0,
                                "screenAvailWidth": 1484,
                                "screenAvailHeight": 949,
                                "devicePixelRatio": 1,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                result = gate.open_with_playwright(
                    "http://127.0.0.1:8765/",
                    {
                        "artifact_root": root,
                        "browser_log": root / "workbench-browser.log",
                        "browser_state": root / "workbench-browser-state.json",
                    },
                    "chrome",
                    None,
                    session="eba-workbench",
                    profile=REPO_ROOT / "chrome-profile" / "workbench",
                )
        finally:
            gate.require_session_aware_cli = original_require_cli  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = original_require_wrapper  # type: ignore[assignment]
            gate.browser_session_status = original_status  # type: ignore[assignment]
            gate.run_browser_command = original_run  # type: ignore[assignment]
            gate.browser_page_metrics = original_metrics  # type: ignore[assignment]

        self.assertTrue(result["reused"])
        self.assertFalse(result["window_maximized"])
        self.assertTrue(result["window_focused"])
        self.assertFalse(result["viewport_synced"])
        self.assertEqual(
            commands,
            [
                [sys.executable, "scripts/playwright_cli_browser.py", "goto", "http://127.0.0.1:8765/", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "tab-list", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "window-focus", "--session", "eba-workbench"],
            ],
        )

    def test_explicit_summon_replaces_reused_browser_session(self) -> None:
        commands: list[list[str]] = []
        statuses = [
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
        ]

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_status(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return statuses.pop(0)

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            return Result()

        def fake_metrics(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return {
                "innerWidth": 1484,
                "innerHeight": 916,
                "outerWidth": 1512,
                "outerHeight": 949,
                "screenX": 0,
                "screenY": 33,
                "devicePixelRatio": 1,
                "screenAvailLeft": 0,
                "screenAvailTop": 0,
                "screenAvailWidth": 1484,
                "screenAvailHeight": 949,
            }

        original_require_cli = gate.require_session_aware_cli
        original_require_wrapper = gate.require_workbench_browser_wrapper
        original_status = gate.browser_session_status
        original_run = gate.run_browser_command
        original_metrics = gate.browser_page_metrics
        try:
            gate.require_session_aware_cli = lambda: "playwright-cli"  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = lambda: gate.BROWSER_WRAPPER  # type: ignore[assignment]
            gate.browser_session_status = fake_status  # type: ignore[assignment]
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            gate.browser_page_metrics = fake_metrics  # type: ignore[assignment]

            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                root = Path(tmp)
                (root / "workbench-browser-state.json").write_text(
                    json.dumps(
                        {
                            "display_signature": {
                                "screenX": 0,
                                "screenY": 33,
                                "screenAvailLeft": 0,
                                "screenAvailTop": 0,
                                "screenAvailWidth": 1484,
                                "screenAvailHeight": 949,
                                "devicePixelRatio": 1,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                result = gate.open_with_playwright(
                    "http://127.0.0.1:8765/",
                    {
                        "artifact_root": root,
                        "browser_log": root / "workbench-browser.log",
                        "browser_state": root / "workbench-browser-state.json",
                    },
                    "chrome",
                    None,
                    session="eba-workbench",
                    profile=REPO_ROOT / "chrome-profile" / "workbench",
                    replace_existing_session=True,
                )
        finally:
            gate.require_session_aware_cli = original_require_cli  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = original_require_wrapper  # type: ignore[assignment]
            gate.browser_session_status = original_status  # type: ignore[assignment]
            gate.run_browser_command = original_run  # type: ignore[assignment]
            gate.browser_page_metrics = original_metrics  # type: ignore[assignment]

        self.assertFalse(result["reused"])
        self.assertTrue(result["replaced"])
        self.assertTrue(result["window_maximized"])
        self.assertTrue(result["window_focused"])
        self.assertTrue(result["viewport_synced"])
        self.assertEqual(
            commands,
            [
                [sys.executable, "scripts/playwright_cli_browser.py", "close", "--session", "eba-workbench"],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "open",
                    "http://127.0.0.1:8765/",
                    "--session",
                    "eba-workbench",
                    "--browser",
                    "chrome",
                    "--persistent",
                    "--profile",
                    "chrome-profile/workbench",
                    "--config",
                    "scripts/playwright_cli_workbench_config.json",
                ],
                [sys.executable, "scripts/playwright_cli_browser.py", "tab-list", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "window-maximize", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "resize", "1484", "949", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "window-focus", "--session", "eba-workbench"],
            ],
        )

    def test_unregistered_workbench_profile_owner_is_stopped_before_open(self) -> None:
        commands: list[list[str]] = []
        stopped: list[list[int]] = []
        statuses = [
            {
                "session": "eba-workbench",
                "alive": False,
                "status": "not_found",
            },
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
        ]

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_status(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return statuses.pop(0)

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            return Result()

        def fake_metrics(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return {
                "innerWidth": 1484,
                "innerHeight": 916,
                "outerWidth": 1512,
                "outerHeight": 949,
                "screenX": 0,
                "screenY": 33,
                "devicePixelRatio": 1,
                "screenAvailLeft": 0,
                "screenAvailTop": 0,
                "screenAvailWidth": 1484,
                "screenAvailHeight": 949,
            }

        def fake_owner_pids(profile: Path, session: str) -> list[int]:
            self.assertEqual(profile, REPO_ROOT / "chrome-profile" / "workbench")
            self.assertEqual(session, "eba-workbench")
            return [88160, 88162]

        def fake_stop(pids: list[int], log_handle: object) -> None:
            stopped.append(pids)

        original_require_cli = gate.require_session_aware_cli
        original_require_wrapper = gate.require_workbench_browser_wrapper
        original_status = gate.browser_session_status
        original_run = gate.run_browser_command
        original_metrics = gate.browser_page_metrics
        original_owner_pids = gate.workbench_profile_owner_pids
        original_stop = gate.stop_stale_workbench_profile_owners
        try:
            gate.require_session_aware_cli = lambda: "playwright-cli"  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = lambda: gate.BROWSER_WRAPPER  # type: ignore[assignment]
            gate.browser_session_status = fake_status  # type: ignore[assignment]
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            gate.browser_page_metrics = fake_metrics  # type: ignore[assignment]
            gate.workbench_profile_owner_pids = fake_owner_pids  # type: ignore[assignment]
            gate.stop_stale_workbench_profile_owners = fake_stop  # type: ignore[assignment]

            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                root = Path(tmp)
                result = gate.open_with_playwright(
                    "http://127.0.0.1:8765/",
                    {
                        "artifact_root": root,
                        "browser_log": root / "workbench-browser.log",
                        "browser_state": root / "workbench-browser-state.json",
                    },
                    "chrome",
                    None,
                    session="eba-workbench",
                    profile=REPO_ROOT / "chrome-profile" / "workbench",
                )
        finally:
            gate.require_session_aware_cli = original_require_cli  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = original_require_wrapper  # type: ignore[assignment]
            gate.browser_session_status = original_status  # type: ignore[assignment]
            gate.run_browser_command = original_run  # type: ignore[assignment]
            gate.browser_page_metrics = original_metrics  # type: ignore[assignment]
            gate.workbench_profile_owner_pids = original_owner_pids  # type: ignore[assignment]
            gate.stop_stale_workbench_profile_owners = original_stop  # type: ignore[assignment]

        self.assertFalse(result["reused"])
        self.assertEqual([[88160, 88162]], stopped)
        self.assertEqual(
            commands[0],
            [
                sys.executable,
                "scripts/playwright_cli_browser.py",
                "open",
                "http://127.0.0.1:8765/",
                "--session",
                "eba-workbench",
                "--browser",
                "chrome",
                "--persistent",
                "--profile",
                "chrome-profile/workbench",
                "--config",
                "scripts/playwright_cli_workbench_config.json",
            ],
        )

    def test_open_with_playwright_uses_visibility_helper_for_reused_session(self) -> None:
        commands: list[list[str]] = []
        focus_commands: list[list[str]] = []
        statuses = [
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
            {
                "session": "eba-workbench",
                "alive": True,
                "status": "open",
            },
        ]

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_status(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return statuses.pop(0)

        def fake_run(command: list[str], log_handle: object) -> Result:
            commands.append(command)
            return Result()

        def fake_metrics(session: str) -> dict[str, object]:
            self.assertEqual(session, "eba-workbench")
            return {
                "innerWidth": 1484,
                "innerHeight": 916,
                "outerWidth": 1512,
                "outerHeight": 949,
                "screenX": 0,
                "screenY": 33,
                "devicePixelRatio": 1,
                "screenAvailLeft": 0,
                "screenAvailTop": 0,
                "screenAvailWidth": 1484,
                "screenAvailHeight": 949,
            }

        def fake_front(plan: dict[str, object], log_handle: object) -> Result:
            focus_commands.append(plan["window_focus_command"])  # type: ignore[arg-type]
            return Result()

        original_require_cli = gate.require_session_aware_cli
        original_require_wrapper = gate.require_workbench_browser_wrapper
        original_status = gate.browser_session_status
        original_run = gate.run_browser_command
        original_metrics = gate.browser_page_metrics
        original_front = gate.bring_managed_workbench_to_front
        try:
            gate.require_session_aware_cli = lambda: "playwright-cli"  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = lambda: gate.BROWSER_WRAPPER  # type: ignore[assignment]
            gate.browser_session_status = fake_status  # type: ignore[assignment]
            gate.run_browser_command = fake_run  # type: ignore[assignment]
            gate.browser_page_metrics = fake_metrics  # type: ignore[assignment]
            gate.bring_managed_workbench_to_front = fake_front  # type: ignore[assignment]

            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                root = Path(tmp)
                (root / "workbench-browser-state.json").write_text(
                    json.dumps(
                        {
                            "display_signature": {
                                "screenX": 0,
                                "screenY": 33,
                                "screenAvailLeft": 0,
                                "screenAvailTop": 0,
                                "screenAvailWidth": 1484,
                                "screenAvailHeight": 949,
                                "devicePixelRatio": 1,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                result = gate.open_with_playwright(
                    "http://127.0.0.1:8765/",
                    {
                        "artifact_root": root,
                        "browser_log": root / "workbench-browser.log",
                        "browser_state": root / "workbench-browser-state.json",
                    },
                    "chrome",
                    None,
                    session="eba-workbench",
                    profile=REPO_ROOT / "chrome-profile" / "workbench",
                )
        finally:
            gate.require_session_aware_cli = original_require_cli  # type: ignore[assignment]
            gate.require_workbench_browser_wrapper = original_require_wrapper  # type: ignore[assignment]
            gate.browser_session_status = original_status  # type: ignore[assignment]
            gate.run_browser_command = original_run  # type: ignore[assignment]
            gate.browser_page_metrics = original_metrics  # type: ignore[assignment]
            gate.bring_managed_workbench_to_front = original_front  # type: ignore[assignment]

        self.assertTrue(result["window_focused"])
        self.assertEqual(
            commands,
            [
                [sys.executable, "scripts/playwright_cli_browser.py", "goto", "http://127.0.0.1:8765/", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "tab-list", "--session", "eba-workbench"],
            ],
        )
        self.assertEqual(
            focus_commands,
            [
                [sys.executable, "scripts/playwright_cli_browser.py", "window-focus", "--session", "eba-workbench"],
            ],
        )

    def test_browser_wrapper_can_maximize_existing_window_without_open_config(self) -> None:
        from scripts import playwright_cli_browser as browser

        commands: list[list[str]] = []

        def fake_run(args: list[str]) -> int:
            commands.append(args)
            return 0

        original_run = browser._run
        try:
            browser._run = fake_run  # type: ignore[assignment]
            browser.open_browser(
                argparse.Namespace(
                    session="eba",
                    browser="chrome",
                    headed=True,
                    persistent=True,
                    profile=REPO_ROOT / "chrome-profile",
                    url="https://example.com",
                )
            )
            browser.window_maximize(argparse.Namespace(session="eba-workbench"))
        finally:
            browser._run = original_run  # type: ignore[assignment]

        self.assertNotIn("--config", commands[0])
        self.assertEqual(commands[1][:2], ["-s=eba-workbench", "run-code"])
        self.assertIn("Browser.setWindowBounds", commands[1][2])
        self.assertIn("maximized", commands[1][2])

    def test_browser_wrapper_can_focus_existing_window_without_changing_bounds(self) -> None:
        from scripts import playwright_cli_browser as browser

        commands: list[list[str]] = []

        def fake_run(args: list[str]) -> int:
            commands.append(args)
            return 0

        original_run = browser._run
        try:
            browser._run = fake_run  # type: ignore[assignment]
            browser.window_focus(
                argparse.Namespace(session="eba-workbench")
            )
        finally:
            browser._run = original_run  # type: ignore[assignment]

        self.assertEqual(commands[0][:2], ["-s=eba-workbench", "run-code"])
        self.assertIn("bringToFront", commands[0][2])
        self.assertIn("window.focus", commands[0][2])
        self.assertNotIn("Browser.setWindowBounds", commands[0][2])

    def test_browser_session_status_reads_session_aware_cli_list(self) -> None:
        payload = {
            "browsers": [
                {
                    "name": "eba-workbench",
                    "status": "open",
                    "browserType": "chrome",
                    "headed": True,
                    "persistent": True,
                    "userDataDir": str(REPO_ROOT / "chrome-profile" / "workbench"),
                    "compatible": True,
                }
            ]
        }

        status = gate.browser_session_status_from_list(
            json.dumps(payload),
            session="eba-workbench",
        )

        self.assertEqual(status["session"], "eba-workbench")
        self.assertTrue(status["alive"])
        self.assertEqual(status["browser_type"], "chrome")
        self.assertTrue(status["persistent"])
        self.assertEqual(status["profile"], "chrome-profile/workbench")

    def test_workbench_asset_health_fetches_manifest_and_registered_assets(self) -> None:
        expected_manifest = gate.build_workbench_asset_manifest()
        requested_urls: list[str] = []

        class Response:
            status = 200

            def __init__(self, body: bytes = b"asset") -> None:
                self.body = body

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body

        def fake_urlopen(request: object, timeout: float = 1.0) -> Response:
            url = request.full_url if hasattr(request, "full_url") else str(request)
            requested_urls.append(url)
            if url == "http://127.0.0.1:8765/api/workbench-assets":
                return Response(json.dumps(expected_manifest).encode("utf-8"))
            if any(url == f"http://127.0.0.1:8765{asset['url']}" for asset in expected_manifest["assets"]):
                return Response()
            raise AssertionError(f"unexpected URL: {url}")

        original_urlopen = gate.urllib.request.urlopen
        try:
            gate.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]

            asset_health = gate.workbench_asset_health("http://127.0.0.1:8765/")
        finally:
            gate.urllib.request.urlopen = original_urlopen  # type: ignore[assignment]

        self.assertTrue(asset_health["healthy"])
        self.assertEqual(asset_health["status"], "ok")
        self.assertIn("http://127.0.0.1:8765/api/workbench-assets", requested_urls)
        self.assertIn("http://127.0.0.1:8765/assets/artifact-workbench.js", requested_urls)

    def test_workbench_asset_health_rejects_missing_manifest_endpoint(self) -> None:
        def fake_urlopen(request: object, timeout: float = 1.0) -> object:
            url = request.full_url if hasattr(request, "full_url") else str(request)
            raise urllib.error.HTTPError(url, 404, "not found", None, None)

        original_urlopen = gate.urllib.request.urlopen
        try:
            gate.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]

            asset_health = gate.workbench_asset_health("http://127.0.0.1:8765/")
        finally:
            gate.urllib.request.urlopen = original_urlopen  # type: ignore[assignment]

        self.assertFalse(asset_health["healthy"])
        self.assertEqual(asset_health["status"], "asset_manifest_unavailable:404")

    def test_workbench_asset_health_rejects_stale_server_source_fingerprint(self) -> None:
        expected_manifest = gate.build_workbench_asset_manifest()
        stale_manifest = dict(expected_manifest)
        stale_manifest.pop("server_source_fingerprint", None)

        class Response:
            status = 200

            def __init__(self, body: bytes = b"asset") -> None:
                self.body = body

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body

        def fake_urlopen(request: object, timeout: float = 1.0) -> Response:
            url = request.full_url if hasattr(request, "full_url") else str(request)
            if url == "http://127.0.0.1:8765/api/workbench-assets":
                return Response(json.dumps(stale_manifest).encode("utf-8"))
            if any(url == f"http://127.0.0.1:8765{asset['url']}" for asset in expected_manifest["assets"]):
                return Response()
            raise AssertionError(f"unexpected URL: {url}")

        original_urlopen = gate.urllib.request.urlopen
        try:
            gate.urllib.request.urlopen = fake_urlopen  # type: ignore[assignment]

            asset_health = gate.workbench_asset_health("http://127.0.0.1:8765/")
        finally:
            gate.urllib.request.urlopen = original_urlopen  # type: ignore[assignment]

        self.assertFalse(asset_health["healthy"])
        self.assertEqual(asset_health["status"], "server_source_fingerprint_mismatch")

    def test_surface_restarts_owned_server_when_asset_health_is_stale(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text('{"artifacts": []}\n', encoding="utf-8")
            manifest_label = str(manifest.relative_to(REPO_ROOT))
            log_label = str((Path(tmp) / "workbench-server.log").relative_to(REPO_ROOT))
            payloads = [
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 123,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": False, "status": "asset_fingerprint_mismatch"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 456,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
            ]
            start_calls: list[object] = []

            def fake_status(args: object, manifest_path: Path) -> dict[str, object]:
                self.assertEqual(manifest_path, manifest)
                return payloads.pop(0)

            def fake_start(args: object) -> int:
                start_calls.append(args)
                return 0

            original_status_payload = gate.status_payload
            original_command_start = gate.command_start
            original_read_workbench_state = gate.read_workbench_state
            original_stop_owned_pid = gate.stop_owned_pid
            original_wait_for_port_release = gate.wait_for_port_release
            try:
                gate.status_payload = fake_status  # type: ignore[assignment]
                gate.command_start = fake_start  # type: ignore[assignment]
                gate.read_workbench_state = lambda url: {  # type: ignore[assignment]
                    "context": {
                        "manifest": manifest_label,
                        "manifest_fingerprint": gate.manifest_state_fingerprint(manifest),
                    },
                    "collection": {"artifacts": []},
                    "interaction_overlays": [],
                    "updated_at_epoch": 1,
                }
                gate.stop_owned_pid = lambda pid, paths: "stopped"  # type: ignore[assignment]
                gate.wait_for_port_release = lambda host, port: True  # type: ignore[assignment]

                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = gate.command_surface(
                        type(
                            "Args",
                            (),
                            {
                                "manifest": manifest,
                                "host": "127.0.0.1",
                                "port": 8765,
                                "timeout": 10.0,
                                "no_browser": True,
                                "json": False,
                            },
                        )()
                    )
            finally:
                gate.status_payload = original_status_payload  # type: ignore[assignment]
                gate.command_start = original_command_start  # type: ignore[assignment]
                gate.read_workbench_state = original_read_workbench_state  # type: ignore[assignment]
                gate.stop_owned_pid = original_stop_owned_pid  # type: ignore[assignment]
                gate.wait_for_port_release = original_wait_for_port_release  # type: ignore[assignment]

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(start_calls), 1)

    def test_surface_restarts_owned_server_when_manifest_state_fingerprint_is_stale(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text('{"steps": [], "artifacts": []}\n', encoding="utf-8")
            manifest_label = str(manifest.relative_to(REPO_ROOT))
            log_label = str((Path(tmp) / "workbench-server.log").relative_to(REPO_ROOT))
            payloads = [
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 123,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 456,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
            ]
            states = [
                {
                    "context": {
                        "manifest": manifest_label,
                        "manifest_fingerprint": "stale",
                    },
                    "collection": {"artifacts": []},
                    "interaction_overlays": [],
                    "updated_at_epoch": 1,
                },
                {
                    "context": {
                        "manifest": manifest_label,
                        "manifest_fingerprint": gate.manifest_state_fingerprint(manifest),
                    },
                    "collection": {"artifacts": []},
                    "interaction_overlays": [],
                    "updated_at_epoch": 2,
                },
            ]
            start_calls: list[object] = []

            def fake_status(args: object, manifest_path: Path) -> dict[str, object]:
                self.assertEqual(manifest_path, manifest)
                return payloads.pop(0)

            def fake_start(args: object) -> int:
                start_calls.append(args)
                return 0

            original_status_payload = gate.status_payload
            original_command_start = gate.command_start
            original_read_workbench_state = gate.read_workbench_state
            original_stop_owned_pid = gate.stop_owned_pid
            original_wait_for_port_release = gate.wait_for_port_release
            try:
                gate.status_payload = fake_status  # type: ignore[assignment]
                gate.command_start = fake_start  # type: ignore[assignment]
                gate.read_workbench_state = lambda url: states.pop(0)  # type: ignore[assignment]
                gate.stop_owned_pid = lambda pid, paths: "stopped"  # type: ignore[assignment]
                gate.wait_for_port_release = lambda host, port: True  # type: ignore[assignment]

                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exit_code = gate.command_surface(
                        type(
                            "Args",
                            (),
                            {
                                "manifest": manifest,
                                "host": "127.0.0.1",
                                "port": 8765,
                                "timeout": 10.0,
                                "no_browser": True,
                                "json": True,
                            },
                        )()
                    )
            finally:
                gate.status_payload = original_status_payload  # type: ignore[assignment]
                gate.command_start = original_command_start  # type: ignore[assignment]
                gate.read_workbench_state = original_read_workbench_state  # type: ignore[assignment]
                gate.stop_owned_pid = original_stop_owned_pid  # type: ignore[assignment]
                gate.wait_for_port_release = original_wait_for_port_release  # type: ignore[assignment]

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(start_calls), 1)
            self.assertEqual(payloads, [])
            self.assertEqual(states, [])
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["server"]["pid"], 456)

    def test_surface_restarts_owned_server_when_workbench_state_endpoint_is_stale(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text('{"artifacts": []}\n', encoding="utf-8")
            manifest_label = str(manifest.relative_to(REPO_ROOT))
            log_label = str((Path(tmp) / "workbench-server.log").relative_to(REPO_ROOT))
            payloads = [
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 123,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 456,
                    "alive": True,
                    "owned": True,
                    "repo_owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "active_manifest": manifest_label,
                    "log": log_label,
                    "workbench_state_url": "http://127.0.0.1:8765/api/workbench-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
            ]
            start_calls: list[object] = []
            stop_calls: list[object] = []
            read_calls = 0

            def fake_status(args: object, manifest_path: Path) -> dict[str, object]:
                self.assertEqual(manifest_path, manifest)
                return payloads.pop(0)

            def fake_start(args: object) -> int:
                start_calls.append(args)
                return 0

            def fake_read_workbench_state(url: str) -> dict[str, object]:
                nonlocal read_calls
                read_calls += 1
                if read_calls == 1:
                    raise urllib.error.HTTPError(url, 404, "not found", None, None)
                return {
                    "context": {
                        "manifest": manifest_label,
                        "manifest_fingerprint": gate.manifest_state_fingerprint(manifest),
                    },
                    "collection": {"artifacts": []},
                    "interaction_overlays": [],
                    "updated_at_epoch": 1,
                }

            original_status_payload = gate.status_payload
            original_command_start = gate.command_start
            original_read_workbench_state = gate.read_workbench_state
            original_stop_owned_pid = gate.stop_owned_pid
            original_wait_for_port_release = gate.wait_for_port_release
            try:
                gate.status_payload = fake_status  # type: ignore[assignment]
                gate.command_start = fake_start  # type: ignore[assignment]
                gate.read_workbench_state = fake_read_workbench_state  # type: ignore[assignment]
                gate.stop_owned_pid = lambda pid, paths: stop_calls.append((pid, paths)) or "stopped"  # type: ignore[assignment]
                gate.wait_for_port_release = lambda host, port: True  # type: ignore[assignment]

                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = gate.command_surface(
                        type(
                            "Args",
                            (),
                            {
                                "manifest": manifest,
                                "host": "127.0.0.1",
                                "port": 8765,
                                "timeout": 10.0,
                                "no_browser": True,
                                "json": False,
                            },
                        )()
                    )
            finally:
                gate.status_payload = original_status_payload  # type: ignore[assignment]
                gate.command_start = original_command_start  # type: ignore[assignment]
                gate.read_workbench_state = original_read_workbench_state  # type: ignore[assignment]
                gate.stop_owned_pid = original_stop_owned_pid  # type: ignore[assignment]
                gate.wait_for_port_release = original_wait_for_port_release  # type: ignore[assignment]

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(start_calls), 1)
            self.assertEqual([call[0] for call in stop_calls], [123])
            self.assertEqual(read_calls, 2)

    def test_stale_asset_restart_waits_for_owned_port_release(self) -> None:
        (REPO_ROOT / "artifacts").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "artifacts") as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text('{"artifacts": []}\n', encoding="utf-8")
            port_checks = [True, False, False]

            class Process:
                pid = 456

                def poll(self) -> None:
                    return None

                def terminate(self) -> None:
                    raise AssertionError("healthy fake process should not terminate")

            original_read_pid = gate.read_pid
            original_pid_alive = gate.pid_alive
            original_is_owned = gate.is_owned_workbench_server
            original_health = gate.health
            original_asset_health = gate.workbench_asset_health
            original_stop_owned_pid = gate.stop_owned_pid
            original_port_accepts_connection = gate.port_accepts_connection
            original_popen = gate.subprocess.Popen
            original_wait_for_health = gate.wait_for_health
            try:
                gate.read_pid = lambda path: 123  # type: ignore[assignment]
                gate.pid_alive = lambda pid: True  # type: ignore[assignment]
                gate.is_owned_workbench_server = lambda pid, path: True  # type: ignore[assignment]
                gate.health = lambda url: (True, "200")  # type: ignore[assignment]
                gate.workbench_asset_health = lambda url: {  # type: ignore[assignment]
                    "healthy": False,
                    "status": "asset_fingerprint_mismatch",
                }
                gate.stop_owned_pid = lambda pid, paths: "killed"  # type: ignore[assignment]
                gate.port_accepts_connection = lambda host, port: port_checks.pop(0)  # type: ignore[assignment]
                gate.subprocess.Popen = lambda *args, **kwargs: Process()  # type: ignore[assignment]
                gate.wait_for_health = lambda url, timeout: (True, "200")  # type: ignore[assignment]

                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = gate.command_start(
                        argparse.Namespace(
                            manifest=manifest,
                            host="127.0.0.1",
                            port=8765,
                            timeout=1.0,
                            open=False,
                            channel="chrome",
                            viewport_size=None,
                            browser_session="eba-workbench",
                            profile=REPO_ROOT / "chrome-profile" / "workbench",
                            quiet=True,
                        )
                    )
            finally:
                gate.read_pid = original_read_pid  # type: ignore[assignment]
                gate.pid_alive = original_pid_alive  # type: ignore[assignment]
                gate.is_owned_workbench_server = original_is_owned  # type: ignore[assignment]
                gate.health = original_health  # type: ignore[assignment]
                gate.workbench_asset_health = original_asset_health  # type: ignore[assignment]
                gate.stop_owned_pid = original_stop_owned_pid  # type: ignore[assignment]
                gate.port_accepts_connection = original_port_accepts_connection  # type: ignore[assignment]
                gate.subprocess.Popen = original_popen  # type: ignore[assignment]
                gate.wait_for_health = original_wait_for_health  # type: ignore[assignment]

            self.assertEqual(exit_code, 0)
            self.assertEqual(port_checks, [])

    def test_eba_workbench_control_commands_are_authorized_and_stable(self) -> None:
        from scripts.eba_cli import workbench_browser_command
        from scripts.eba_control_plane import ACTIVE_TURN_REQUIRED_COMMANDS, ALLOWED_DEV_COMMANDS

        self.assertIn("workbench", ALLOWED_DEV_COMMANDS)
        self.assertNotIn("workbench", ACTIVE_TURN_REQUIRED_COMMANDS)
        self.assertEqual(
            workbench_browser_command("tabs"),
            [sys.executable, "scripts/playwright_cli_browser.py", "tab-list", "--session", "eba-workbench"],
        )
        self.assertEqual(
            workbench_browser_command("tab-select", "2"),
            [sys.executable, "scripts/playwright_cli_browser.py", "tab-select", "2", "--session", "eba-workbench"],
        )

    def test_eba_workbench_zero_arg_controls_dispatch_without_other_action_fields(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []

        class Result:
            returncode = 0
            stdout = "tabs\n"
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> Result:
            commands.append(command)
            return Result()

        original_run = eba_cli.run
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = eba_cli.command_workbench(
                    Namespace(workbench_action="tabs", session="eba-workbench")
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            commands,
            [[sys.executable, "scripts/playwright_cli_browser.py", "tab-list", "--session", "eba-workbench"]],
        )

    def test_eba_workbench_refresh_summons_active_workbench_surface(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []

        class Result:
            returncode = 0
            stdout = '{"active_manifest":"artifacts/easy-audit/latest/manifest.json"}\n'
            stderr = ""

        class SurfaceResult:
            returncode = 0
            stdout = '{"status":"surface"}\n'
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> object:
            commands.append(command)
            return Result() if len(commands) == 1 else SurfaceResult()

        original_run = eba_cli.run
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = eba_cli.command_workbench(
                    Namespace(workbench_action="refresh", session="eba-workbench", json=True)
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "status",
                    str(eba_cli.DEFAULT_MANIFEST),
                    "--port",
                    "8765",
                ],
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "surface",
                    str(eba_cli.REPO_ROOT / "artifacts/easy-audit/latest/manifest.json"),
                    "--port",
                    "8765",
                    "--timeout",
                    "10",
                    "--json",
                ],
            ],
        )

    def test_eba_demo_without_explicit_target_preserves_active_workbench_manifest(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []
        releases: list[Path] = []

        class StatusResult:
            returncode = 0
            stdout = '{"active_manifest":"artifacts/easy-audit/latest/manifest.json"}\n'
            stderr = ""

        class SurfaceResult:
            returncode = 0
            stdout = '{"status":"surface"}\n'
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> object:
            commands.append(command)
            return StatusResult() if len(commands) == 1 else SurfaceResult()

        original_run = eba_cli.run
        original_release = eba_cli.release_default_demo_server
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            eba_cli.release_default_demo_server = lambda path: releases.append(path)  # type: ignore[assignment]
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = eba_cli.command_demo(
                    Namespace(
                        manifest=None,
                        fixture=None,
                        no_browser=False,
                        json=True,
                    )
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]
            eba_cli.release_default_demo_server = original_release  # type: ignore[assignment]

        active_manifest = eba_cli.REPO_ROOT / "artifacts/easy-audit/latest/manifest.json"
        self.assertEqual(exit_code, 0)
        self.assertEqual(releases, [active_manifest])
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "status",
                    str(eba_cli.DEFAULT_MANIFEST),
                    "--port",
                    "8765",
                ],
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "surface",
                    str(active_manifest),
                    "--port",
                    "8765",
                    "--timeout",
                    "10",
                    "--json",
                ],
            ],
        )

    def test_eba_situation_without_explicit_target_reports_active_workbench_manifest(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        manifests: list[Path] = []
        active_manifest = eba_cli.REPO_ROOT / "artifacts/easy-audit/latest/manifest.json"

        def fake_workbench_status(manifest: Path) -> dict[str, object]:
            manifests.append(manifest)
            return {
                "active_manifest": "artifacts/easy-audit/latest/manifest.json",
                "manifest": str(manifest.relative_to(eba_cli.REPO_ROOT)),
                "owned": True,
            }

        original_current_manifest = eba_cli.current_workbench_manifest
        original_parse_status = eba_cli.parse_status
        original_parse_ahead_behind = eba_cli.parse_ahead_behind
        original_workbench_status = eba_cli.workbench_status
        try:
            eba_cli.current_workbench_manifest = lambda: active_manifest  # type: ignore[assignment]
            eba_cli.parse_status = lambda: {"branch_line": "test", "dirty_files": [], "raw": []}  # type: ignore[assignment]
            eba_cli.parse_ahead_behind = lambda: {"ahead": 0, "behind": 0}  # type: ignore[assignment]
            eba_cli.workbench_status = fake_workbench_status  # type: ignore[assignment]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = eba_cli.command_situation(
                    Namespace(
                        manifest=None,
                        fixture=None,
                        json=True,
                    )
                )
        finally:
            eba_cli.current_workbench_manifest = original_current_manifest  # type: ignore[assignment]
            eba_cli.parse_status = original_parse_status  # type: ignore[assignment]
            eba_cli.parse_ahead_behind = original_parse_ahead_behind  # type: ignore[assignment]
            eba_cli.workbench_status = original_workbench_status  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifests, [active_manifest])
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["artifact_workbench"]["owned"])
        self.assertEqual(
            payload["artifact_workbench"]["manifest"],
            "artifacts/easy-audit/latest/manifest.json",
        )

    def test_eba_workbench_context_dispatches_gate_state(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []
        manifest = Path("artifacts/easy-audit/latest/manifest.json")

        class Result:
            returncode = 0
            stdout = '{"status":"workbench_state"}\n'
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> Result:
            commands.append(command)
            return Result()

        original_run = eba_cli.run
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = eba_cli.command_workbench(
                    Namespace(
                        workbench_action="context",
                        manifest=manifest,
                        fixture=None,
                        json=True,
                    )
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "state",
                    str(manifest),
                    "--port",
                    "8765",
                ]
            ],
        )

    def test_eba_workbench_glance_dispatches_gate_glance(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []
        manifest = Path("artifacts/easy-audit/latest/manifest.json")

        class Result:
            returncode = 0
            stdout = '{"status":"workbench_glance"}\n'
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> Result:
            commands.append(command)
            return Result()

        original_run = eba_cli.run
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = eba_cli.command_workbench(
                    Namespace(
                        workbench_action="glance",
                        manifest=manifest,
                        fixture=None,
                        json=True,
                    )
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "glance",
                    str(manifest),
                    "--port",
                    "8765",
                ]
            ],
        )

    def test_eba_workbench_live_smoke_prepares_surface_and_runs_single_boot_snippet(self) -> None:
        from argparse import Namespace
        from scripts import eba_cli

        commands: list[list[str]] = []
        releases: list[Path] = []
        temp_root = tempfile.TemporaryDirectory(dir=REPO_ROOT)
        self.addCleanup(temp_root.cleanup)
        manifest = Path(temp_root.name) / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        manifest_label = str(manifest.relative_to(REPO_ROOT))

        class Result:
            returncode = 0
            stdout = '{"status":"surface","server":{"asset_health":{"healthy":true}}}\n'
            stderr = ""

        class SmokeResult:
            returncode = 0
            stdout = '### Result\n{"status":"passed","assetCount":20}\n'
            stderr = ""

        def fake_run(command: list[str], *, capture: bool = True, check: bool = False) -> object:
            commands.append(command)
            return Result() if len(commands) == 1 else SmokeResult()

        original_run = eba_cli.run
        original_release = eba_cli.release_default_demo_server
        try:
            eba_cli.run = fake_run  # type: ignore[assignment]
            eba_cli.release_default_demo_server = lambda path: releases.append(path)  # type: ignore[assignment]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = eba_cli.command_workbench(
                    Namespace(
                        workbench_action="live-smoke",
                        manifest=manifest,
                        fixture=None,
                        json=True,
                        session="eba-workbench",
                    )
                )
        finally:
            eba_cli.run = original_run  # type: ignore[assignment]
            eba_cli.release_default_demo_server = original_release  # type: ignore[assignment]

        self.assertEqual(exit_code, 0)
        self.assertEqual(releases, [manifest])
        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    str(eba_cli.WORKBENCH_GATE),
                    "surface",
                    str(manifest),
                    "--port",
                    "8765",
                    "--timeout",
                    "10",
                    "--json",
                ],
                [
                    sys.executable,
                    "scripts/playwright_cli_browser.py",
                    "run-code",
                    "scripts/playwright-snippets/artifact-workbench-live-boot-check.js",
                    "--session",
                    "eba-workbench",
                ],
            ],
        )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["manifest"], manifest_label)
        self.assertEqual(payload["surface"]["status"], "surface")
        self.assertEqual(payload["smoke"]["status"], "passed")
        self.assertEqual(payload["smoke"]["assetCount"], 20)
        self.assertNotIn("smoke_stdout", payload)

    def test_workbench_glance_summarizes_current_annotations_without_projection_blob(self) -> None:
        state = {
            "collection": {
                "manifest": "artifacts/easy-audit/latest/manifest.json",
                "artifacts": [
                    {
                        "id": "l0-source-urls",
                        "name": "Seed source URLs",
                        "type": "json",
                        "kind": "url_list",
                        "path": "artifacts/easy-audit/latest/l0-source-urls.json",
                    },
                    {
                        "id": "l1-careers-screenshot",
                        "name": "Careers page screenshot",
                        "type": "image",
                        "kind": "screenshot",
                        "path": "artifacts/easy-audit/latest/l1-careers-screenshot.png",
                    },
                    {
                        "id": "l4-final-report",
                        "name": "Final employer brand audit",
                        "type": "html",
                        "kind": "report",
                        "path": "artifacts/easy-audit/latest/l4-final-report.html",
                    },
                ],
            },
            "context": {
                "manifest": "artifacts/easy-audit/latest/manifest.json",
                "changed_at_epoch": 123,
                "changed_by": "user",
            },
            "contexts": [
                {
                    "active": True,
                    "label": "Acme Robotics audit",
                    "manifest": "artifacts/easy-audit/latest/manifest.json",
                    "subtitle": "Acme Robotics · complete",
                    "status": "complete",
                }
            ],
            "interaction_overlays": [
                {
                    "id": "overlay-1",
                    "subtype": "annotation",
                    "subject": {"id": "l1-careers-screenshot", "kind": "artifact"},
                    "anchor": {
                        "type": "image_region",
                        "coordinate_space": "natural_image",
                        "rect": {"x": 521, "y": 147, "width": 326, "height": 241},
                    },
                    "body": {"kind": "comment", "text": "this sucks"},
                    "created_at_epoch": 1781564957,
                }
            ],
            "updated_at_epoch": 1781564957,
            "workbench_projection": {"large": "omit me"},
        }

        glance = gate.summarize_workbench_glance(state)

        self.assertEqual(glance["status"], "workbench_glance")
        self.assertEqual(glance["current"]["label"], "Acme Robotics audit")
        self.assertEqual(glance["current_artifact"]["id"], "l1-careers-screenshot")
        self.assertEqual(glance["model"]["artifact_count"], 3)
        self.assertEqual(glance["model"]["annotation_count"], 1)
        self.assertEqual(
            glance["annotations"],
            [
                {
                    "id": "overlay-1",
                    "artifact_id": "l1-careers-screenshot",
                    "artifact_name": "Careers page screenshot",
                    "text": "this sucks",
                    "anchor": {
                        "type": "image_region",
                        "coordinate_space": "natural_image",
                        "rect": {"x": 521, "y": 147, "width": 326, "height": 241},
                    },
                    "created_at_epoch": 1781564957,
                }
            ],
        )
        self.assertNotIn("workbench_projection", glance)

    def test_workbench_state_accepts_bounded_input_overlays_for_projected_inputs(self) -> None:
        from scripts.playwright_cli_workbench_server import clean_interaction_overlays

        clean = clean_interaction_overlays(
            [
                {
                    "id": "input:l0-seed-intake:company",
                    "subtype": "bounded_input",
                    "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                    "anchor": {
                        "type": "workflow_input",
                        "coordinate_space": "workflow_graph",
                        "artifact_id": "l0-intake-flow",
                        "step_id": "l0-seed-intake",
                        "input_id": "company",
                    },
                    "body": {"kind": "input_value", "value": "Acme Robotics"},
                    "created_at_epoch": 1781564957,
                },
                {
                    "id": "input:l0-seed-intake:source_urls",
                    "subtype": "bounded_input",
                    "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                    "anchor": {
                        "type": "workflow_input",
                        "coordinate_space": "workflow_graph",
                        "artifact_id": "l0-intake-flow",
                        "step_id": "l0-seed-intake",
                        "input_id": "source_urls",
                    },
                    "body": {"kind": "input_value", "value": "https://acme.example/careers/jobs/123"},
                    "created_at_epoch": 1781564957,
                },
            ],
            {"l0-intake-flow"},
            bounded_input_definitions=[
                {
                    "id": "input:l0-seed-intake:company",
                    "step_id": "l0-seed-intake",
                    "input_id": "company",
                    "anchor": {
                        "type": "workflow_input",
                        "artifact_id": "l0-intake-flow",
                        "step_id": "l0-seed-intake",
                        "input_id": "company",
                    },
                }
            ],
        )

        self.assertEqual(
            clean,
            [
                {
                    "id": "input:l0-seed-intake:company",
                    "subtype": "bounded_input",
                    "subject": {"kind": "workflow_step", "id": "l0-seed-intake"},
                    "anchor": {
                        "type": "workflow_input",
                        "coordinate_space": "workflow_graph",
                        "artifact_id": "l0-intake-flow",
                        "step_id": "l0-seed-intake",
                        "input_id": "company",
                    },
                    "body": {"kind": "input_value", "value": "Acme Robotics"},
                    "created_at_epoch": 1781564957,
                    "updated_at_epoch": None,
                }
            ],
        )

    def test_workbench_state_accepts_html_element_annotation_anchors(self) -> None:
        from scripts.playwright_cli_workbench_server import clean_interaction_overlays

        clean = clean_interaction_overlays(
            [
                {
                    "id": "overlay-html-demo",
                    "subtype": "annotation",
                    "subject": {"kind": "artifact", "id": "l4-final-report"},
                    "anchor": {
                        "type": "html_element",
                        "coordinate_space": "html_document",
                        "selector_candidates": ["h1", "#executive-readout h1"],
                        "tag": "h1",
                        "id": "",
                        "classes": ["hero-title"],
                        "role": "",
                        "accessible_name": "Acme Robotics",
                        "text": "Acme Robotics",
                        "rect": {"x": 53, "y": 125, "width": 782, "height": 48},
                        "ancestor_trail": [
                            {"tag": "header", "id": "executive-readout", "classes": []},
                            {"tag": "main", "id": "", "classes": []},
                        ],
                        "source_url": "artifacts/easy-audit/latest/l4-final-report.html",
                    },
                    "body": {"kind": "comment", "text": "HTML annotation demo"},
                    "created_at_epoch": 1781665745,
                }
            ],
            {"l4-final-report"},
        )

        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["anchor"]["type"], "html_element")
        self.assertEqual(clean[0]["anchor"]["selector_candidates"], ["h1", "#executive-readout h1"])
        self.assertEqual(clean[0]["anchor"]["rect"], {"x": 53, "y": 125, "width": 782, "height": 48})
        self.assertEqual(clean[0]["body"]["text"], "HTML annotation demo")


if __name__ == "__main__":
    unittest.main()
