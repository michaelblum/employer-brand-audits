from __future__ import annotations

import json
import contextlib
import io
import argparse
import sys
import tempfile
import unittest
import urllib.error
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
            ["node", "--check", "scripts/artifact_primitives/artifact_renderer.js"],
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
            ["node", "--check", "scripts/artifact_primitives/interaction_overlay_controller.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/workflow_sidebar_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/document_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/artifact_renderer_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/interaction_overlay_primitive_check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "tests/interaction_overlay_controller_check.js"],
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
            ["node", "--check", "scripts/playwright-snippets/workflow-artifact-workbench-image-artifact-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/workflow-artifact-workbench-markdown-artifact-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/workflow-artifact-workbench-navigation-check.js"],
            validation_commands(),
        )
        self.assertIn(
            ["node", "--check", "scripts/playwright-snippets/workflow-artifact-workbench-annotation-reorder-check.js"],
            validation_commands(),
        )
        self.assertIn("/assets/artifact-primitives/document_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/artifact_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_renderer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/markdown_interactions.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/image_viewer.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/workflow_sidebar.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/interaction_overlay.js", WORKBENCH_ASSETS)
        self.assertIn("/assets/artifact-primitives/interaction_overlay_controller.js", WORKBENCH_ASSETS)

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
        self.assertIn("http://127.0.0.1:8765/assets/workflow-artifact-workbench.js", requested_urls)

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
                    "health": "200",
                    "asset_health": {"healthy": False, "status": "asset_fingerprint_mismatch"},
                    "manifest": manifest_label,
                    "log": log_label,
                    "annotation_state_url": "http://127.0.0.1:8765/api/annotation-state",
                    "workbench_projection_url": "http://127.0.0.1:8765/api/workbench-projection",
                    "browser_session": {"session": "eba-workbench", "alive": True},
                },
                {
                    "url": "http://127.0.0.1:8765/",
                    "pid": 456,
                    "alive": True,
                    "owned": True,
                    "health": "200",
                    "asset_health": {"healthy": True, "status": "ok"},
                    "manifest": manifest_label,
                    "log": log_label,
                    "annotation_state_url": "http://127.0.0.1:8765/api/annotation-state",
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
            original_read_annotation_state = gate.read_annotation_state
            try:
                gate.status_payload = fake_status  # type: ignore[assignment]
                gate.command_start = fake_start  # type: ignore[assignment]
                gate.read_annotation_state = lambda url: {  # type: ignore[assignment]
                    "collection": {"artifacts": []},
                    "annotations": {},
                    "updated_at_epoch": 1,
                }

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
                gate.read_annotation_state = original_read_annotation_state  # type: ignore[assignment]

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(start_calls), 1)

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
