from __future__ import annotations

import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import playwright_cli_workbench_gate as gate


class WorkflowArtifactWorkbenchBrowserControlTests(unittest.TestCase):
    def test_browser_control_tests_are_part_of_validation_surface(self) -> None:
        from scripts.eba_cli import validation_commands

        self.assertIn(
            [sys.executable, "tests/test_workflow_artifact_workbench_browser_control.py"],
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
            ["node", "--check", "scripts/artifact_primitives/workflow_sidebar.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/artifact_primitives/interaction_overlay.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/workflow_sidebar_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/interaction_overlay_primitive_check.js"],
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
        self.assertIn("/assets/artifact-primitives/document_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_interactions.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/image_viewer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/workflow_sidebar.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/interaction_overlay.js", WORKBENCH_ASSETS)

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
            ],
        )
        self.assertIsNone(plan["initial_resize_command"])

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

    def test_reused_browser_session_syncs_viewport_width_without_reopening(self) -> None:
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
                "innerWidth": 1440,
                "innerHeight": 1000,
                "outerWidth": 1512,
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
        self.assertTrue(result["viewport_synced"])
        self.assertEqual(
            commands,
            [
                [sys.executable, "scripts/playwright_cli_browser.py", "goto", "http://127.0.0.1:8765/", "--session", "eba-workbench"],
                [sys.executable, "scripts/playwright_cli_browser.py", "resize", "1512", "1000", "--session", "eba-workbench"],
            ],
        )

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

    def test_eba_workbench_control_commands_are_authorized_and_stable(self) -> None:
        from scripts.eba_cli import workbench_browser_command
        from scripts.eba_control_plane import ACTIVE_TURN_REQUIRED_COMMANDS, ALLOWED_DEV_COMMANDS

        self.assertIn("workbench", ALLOWED_DEV_COMMANDS)
        self.assertIn("workbench", ACTIVE_TURN_REQUIRED_COMMANDS)
        self.assertEqual(
            workbench_browser_command("refresh"),
            [sys.executable, "scripts/playwright_cli_browser.py", "reload", "--session", "eba-workbench"],
        )
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


if __name__ == "__main__":
    unittest.main()
