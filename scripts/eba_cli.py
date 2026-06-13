#!/usr/bin/env python3
"""Small project command surface for agent workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.eba_control_plane import (
        ControlPlaneError,
        assert_dev_command_allowed,
        begin_turn,
        end_turn,
        print_json as print_control_plane_json,
    )
except ModuleNotFoundError:
    from eba_control_plane import (
        ControlPlaneError,
        assert_dev_command_allowed,
        begin_turn,
        end_turn,
        print_json as print_control_plane_json,
    )


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)
REVIEW_GATE = REPO_ROOT / "scripts" / "playwright_cli_review_gate.py"
COMPILE_TARGETS = [
    "scripts/image_normalization_bridge.py",
    "scripts/playwright_cli_public_page_matrix_smoke.py",
    "scripts/playwright_cli_public_page_smoke.py",
    "scripts/playwright_cli_capture_modes_smoke.py",
    "scripts/playwright_cli_review_server.py",
    "scripts/playwright_cli_review_gate.py",
    "scripts/workbench_projection.py",
    "scripts/workbench_projection_shape_check.py",
    "scripts/eba_cli.py",
]


def run(args: list[str], *, check: bool = False, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=capture,
        check=check,
    )


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return run(["git", *args])


def parse_status() -> dict[str, Any]:
    result = git(["status", "--short", "--branch"])
    lines = result.stdout.splitlines()
    branch_line = next((line for line in lines if line.startswith("## ")), "## unknown")
    return {
        "branch_line": branch_line[3:],
        "dirty_files": [line for line in lines if not line.startswith("## ")],
        "raw": lines,
    }


def parse_ahead_behind() -> dict[str, int | None]:
    result = git(["rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
    if result.returncode != 0:
        return {"ahead": None, "behind": None}
    parts = result.stdout.strip().split()
    if len(parts) != 2:
        return {"ahead": None, "behind": None}
    return {"behind": int(parts[0]), "ahead": int(parts[1])}


def review_status(manifest: Path) -> dict[str, Any] | None:
    if not manifest.exists():
        return None
    result = run([
        sys.executable,
        str(REVIEW_GATE),
        "status",
        str(manifest),
        "--port",
        "8765",
    ])
    if result.returncode != 0:
        return {
            "status": "failed",
            "stderr": result.stderr.strip(),
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "invalid_json",
            "stdout": result.stdout[:1000],
        }


def command_situation(args: argparse.Namespace) -> int:
    status = parse_status()
    payload = {
        "repo": str(REPO_ROOT),
        "git": {
            **status,
            **parse_ahead_behind(),
        },
        "review_workbench": review_status(args.manifest),
        "command_surface": {
            "validate": "./eba dev validate",
            "demo": "./eba dev demo",
            "demo_headless": "./eba dev demo --no-browser",
        },
        "onboarding": {
            "token": "EBA-AGENTS-SOP-V1",
            "entrypoint": "AGENTS.md",
            "sop": "docs/superpowers/project-sop.md",
            "first_response_gate": [
                "confirm_entrypoint_and_handoff_paths_read",
                "report_onboarding_token",
                "respond_with_salience_alignment",
                "ask_for_concerns_misalignment_or_drift_before_code_changes",
            ],
        },
        "stopping_point_options": [
            "checkpoint_and_push_if_useful",
            "update_issues_labels_epics",
            "recommend_or_write_handoff",
            "offer_self_guided_demo_for_tangible_work",
        ],
    }
    if args.json:
        print_json(payload)
    else:
        print(f"repo={payload['repo']}")
        print(f"branch={status['branch_line']}")
        print(f"dirty_files={len(status['dirty_files'])}")
        print(f"ahead={payload['git']['ahead']} behind={payload['git']['behind']}")
        review = payload["review_workbench"] or {}
        print(f"review_workbench={review.get('url', 'unavailable')} health={review.get('health', 'unknown')}")
        print(f"onboarding_token={payload['onboarding']['token']}")
    return 0


def command_begin(args: argparse.Namespace) -> int:
    payload = begin_turn(REPO_ROOT, args.worker_id)
    print_control_plane_json(payload)
    return 0


def command_end(args: argparse.Namespace) -> int:
    payload = end_turn(REPO_ROOT, args.worker_id)
    print_control_plane_json(payload)
    return 0


def validation_commands() -> list[list[str]]:
    commands = [
        [sys.executable, "-m", "py_compile", *COMPILE_TARGETS],
        [sys.executable, "scripts/workbench_projection_shape_check.py"],
        ["node", "--check", "scripts/artifact_primitives/mermaid_renderer.js"],
        ["node", "--check", "scripts/review_workbench/app.js"],
        ["node", "--check", "scripts/playwright-snippets/review-workbench-composite-artifact-check.js"],
        ["node", "--check", "scripts/playwright-snippets/review-workbench-mermaid-artifact-check.js"],
    ]
    pytest = REPO_ROOT / "mcp-server" / ".venv" / "bin" / "pytest"
    if pytest.exists():
        commands.append([str(pytest), "-q", "mcp-server/tests"])
    commands.append(["git", "diff", "--check"])
    return commands


def command_validate(args: argparse.Namespace) -> int:
    results = []
    for command in validation_commands():
        completed = run(command, capture=True)
        result = {
            "command": " ".join(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        results.append(result)
        if not args.json:
            print(f"$ {result['command']}")
            if result["stdout"]:
                print(result["stdout"])
            if result["stderr"]:
                print(result["stderr"], file=sys.stderr)
        if completed.returncode != 0:
            if args.json:
                print_json({"status": "failed", "results": results})
            return completed.returncode
    if args.json:
        print_json({"status": "passed", "results": results})
    return 0


def command_demo(args: argparse.Namespace) -> int:
    if not args.manifest.exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    command = [
        sys.executable,
        str(REVIEW_GATE),
        "surface",
        str(args.manifest),
        "--port",
        "8765",
        "--timeout",
        "10",
    ]
    if args.no_browser:
        command.append("--no-browser")
    if args.json:
        command.append("--json")
    completed = run(command, capture=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode != 0:
        return completed.returncode
    if not args.json:
        print()
        print("Self-guided demo recipe:")
        print("1. Review the workflow header in the right sidebar.")
        print("2. Toggle page and slot filter chips; previous/next should follow the filtered set.")
        print("3. Open a Review Summary artifact and confirm markdown edit/annotation still works.")
        print("4. Inspect tall/full-page captures; viewer zoom should fit without mutating image bytes.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Employer Brand Audits project command surface.")
    subparsers = parser.add_subparsers(dest="family", required=True)

    begin = subparsers.add_parser("begin", help="Begin an agent control-plane turn")
    begin.add_argument("--worker-id")
    begin.set_defaults(func=command_begin)

    end = subparsers.add_parser("end", help="End an agent control-plane turn")
    end.add_argument("--worker-id", required=True)
    end.set_defaults(func=command_end)

    dev = subparsers.add_parser("dev", help="Developer and agent workflow commands")
    dev_subparsers = dev.add_subparsers(dest="command", required=True)

    situation = dev_subparsers.add_parser("situation", help="Print current repo and workbench state")
    situation.add_argument("--json", action="store_true")
    situation.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    situation.set_defaults(func=command_situation)

    validate = dev_subparsers.add_parser("validate", help="Run focused project validation")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=command_validate)

    demo = dev_subparsers.add_parser("demo", help="Prepare the review workbench demo surface")
    demo.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    demo.add_argument("--no-browser", action="store_true")
    demo.add_argument("--json", action="store_true")
    demo.set_defaults(func=command_demo)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.family == "dev":
            assert_dev_command_allowed(REPO_ROOT, args.command)
        return args.func(args)
    except ControlPlaneError as exc:
        print_control_plane_json(exc.payload)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
