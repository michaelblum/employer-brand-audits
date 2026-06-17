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
    from scripts.easy_audit_fixture import generate_easy_audit_fixture
    from scripts.eba_control_plane import (
        ControlPlaneError,
        assert_dev_command_allowed,
        begin_turn,
        end_turn,
        print_json as print_control_plane_json,
    )
    from scripts.eba_signature import append_signature_footer, current_eba_signature, signature_payload
    from scripts.url_stage_capture import DEFAULT_OUTPUT_ROOT, capture_url_stage, slugify_stage_name
except ModuleNotFoundError:
    from easy_audit_fixture import generate_easy_audit_fixture
    from eba_control_plane import (
        ControlPlaneError,
        assert_dev_command_allowed,
        begin_turn,
        end_turn,
        print_json as print_control_plane_json,
    )
    from eba_signature import append_signature_footer, current_eba_signature, signature_payload
    from url_stage_capture import DEFAULT_OUTPUT_ROOT, capture_url_stage, slugify_stage_name


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)
WORKBENCH_GATE = REPO_ROOT / "scripts" / "playwright_cli_workbench_gate.py"
BROWSER_WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
WORKBENCH_LIVE_BOOT_SMOKE = (
    REPO_ROOT / "scripts" / "playwright-snippets" / "artifact-workbench-live-boot-check.js"
)
THREAD_WORKBENCH = (
    Path.home() / ".codex" / "skills" / "codex-thread-workbench" / "scripts" / "thread_workbench.py"
)
WORKBENCH_BROWSER_SESSION = "eba-workbench"
WORKBENCH_PORT = "8765"
COMPILE_TARGETS = [
    "scripts/easy_audit_fixture.py",
    "scripts/easy_audit_site_capture_smoke.py",
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
    "scripts/eba_cli.py",
    "scripts/eba_commit_msg_hook.py",
    "scripts/eba_signature.py",
]
FIXTURE_GENERATORS = {
    "easy-audit": generate_easy_audit_fixture,
}


def run(args: list[str], *, check: bool = False, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=capture,
        check=check,
    )


def run_with_stdin(args: list[str], input_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
    )


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def parse_playwright_cli_result(stdout: str) -> Any | None:
    marker = "### Result"
    marker_index = stdout.find(marker)
    if marker_index < 0:
        return None
    result_lines = stdout[marker_index + len(marker) :].splitlines()
    result_text = next((line.strip() for line in result_lines if line.strip()), "")
    if not result_text:
        return None
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        return result_text


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


def workbench_status(manifest: Path) -> dict[str, Any] | None:
    if not manifest.exists():
        return None
    result = run([
        sys.executable,
        str(WORKBENCH_GATE),
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


def resolve_manifest(args: argparse.Namespace) -> Path:
    fixture = getattr(args, "fixture", None)
    manifest = getattr(args, "manifest", None)
    if fixture:
        try:
            return FIXTURE_GENERATORS[fixture]()
        except KeyError as exc:
            names = ", ".join(sorted(FIXTURE_GENERATORS))
            raise SystemExit(f"Unknown fixture: {fixture}. Available fixtures: {names}") from exc
    return manifest or DEFAULT_MANIFEST


def resolve_current_workbench_manifest(args: argparse.Namespace) -> Path:
    if getattr(args, "fixture", None) or getattr(args, "manifest", None) is not None:
        return resolve_manifest(args)
    active_manifest = current_workbench_manifest()
    if active_manifest.exists():
        return active_manifest
    return DEFAULT_MANIFEST


def workbench_gate_json(command: str, manifest: Path) -> dict[str, Any] | None:
    result = run([
        sys.executable,
        str(WORKBENCH_GATE),
        command,
        str(manifest),
        "--port",
        "8765",
    ])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def release_default_demo_server(target_manifest: Path) -> None:
    default_manifest = DEFAULT_MANIFEST.resolve()
    if target_manifest.resolve() == default_manifest or not default_manifest.exists():
        return
    status = workbench_gate_json("status", default_manifest)
    if not status or not status.get("alive") or not status.get("owned") or status.get("health") != "200":
        return
    run([
        sys.executable,
        str(WORKBENCH_GATE),
        "stop",
        str(default_manifest),
    ])


def command_situation(args: argparse.Namespace) -> int:
    manifest = resolve_current_workbench_manifest(args)
    status = parse_status()
    payload = {
        "repo": str(REPO_ROOT),
        "git": {
            **status,
            **parse_ahead_behind(),
        },
        "artifact_workbench": workbench_status(manifest),
        "command_surface": {
            "validate": "./eba dev validate",
            "demo": "./eba dev demo",
            "demo_headless": "./eba dev demo --no-browser",
            "stage_url": "./eba dev stage-url <url>",
            "workbench": "./eba dev workbench",
            "trace": "./eba dev trace",
            "gh": "./eba dev gh",
            "hooks": "./eba dev hooks",
            "sig": "./eba sig",
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
        workbench = payload["artifact_workbench"] or {}
        print(f"artifact_workbench={workbench.get('url', 'unavailable')} health={workbench.get('health', 'unknown')}")
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


def command_sig(args: argparse.Namespace) -> int:
    signature = current_eba_signature(REPO_ROOT, worker_id=args.worker_id)
    payload = signature_payload(signature)
    if args.json:
        print_json(payload)
    else:
        print(f"EBA-Sig: {payload['signature']}")
        if payload["head"]:
            print(f"head={payload['head']}")
    return 0


def validation_commands() -> list[list[str]]:
    commands = [
        [sys.executable, "-m", "py_compile", *COMPILE_TARGETS],
        [sys.executable, "tests/test_workbench_bounded_input.py"],
        [sys.executable, "tests/test_easy_audit_fixture.py"],
        [sys.executable, "tests/test_artifact_workbench_browser_control.py"],
        [sys.executable, "tests/test_url_stage_capture.py"],
        [sys.executable, "scripts/workbench_projection_shape_check.py"],
        ["node", "--check", "scripts/artifact_primitives/mermaid_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/markdown_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/markdown_interactions.js"],
        ["node", "--check", "scripts/artifact_primitives/image_viewer.js"],
        ["node", "--check", "scripts/artifact_primitives/document_renderer.js"],
        ["node", "--check", "scripts/artifact_primitives/html_renderer.js"],
        ["node", "--check", "scripts/artifacts/core/artifact_common.js"],
        ["node", "--check", "scripts/artifacts/types/image_artifact.js"],
        ["node", "--check", "scripts/artifacts/types/markdown_artifact.js"],
        ["node", "--check", "scripts/artifacts/types/html_artifact.js"],
        ["node", "--check", "scripts/artifacts/types/document_artifact.js"],
        ["node", "--check", "scripts/artifacts/artifact_registry.js"],
        ["node", "--check", "scripts/artifact_primitives/artifact_renderer.js"],
        ["node", "--check", "scripts/artifacts/navigation/artifact_navigator.js"],
        ["node", "--check", "scripts/artifact_primitives/interaction_overlay.js"],
        ["node", "--check", "scripts/artifact_primitives/target_link.js"],
        ["node", "--check", "scripts/artifact_primitives/interaction_overlay_controller.js"],
        ["node", "tests/markdown_renderer_primitive_check.js"],
        ["node", "tests/document_renderer_primitive_check.js"],
        ["node", "tests/html_renderer_primitive_check.js"],
        ["node", "tests/artifact_registry_check.js"],
        ["node", "tests/artifact_renderer_primitive_check.js"],
        ["node", "tests/artifact_toolbar_check.js"],
        ["node", "tests/artifact_binding_check.js"],
        ["node", "tests/artifact_navigator_check.js"],
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


def command_stage_url(args: argparse.Namespace) -> int:
    slug = slugify_stage_name(args.name or args.url)
    output_dir = args.output_dir or (DEFAULT_OUTPUT_ROOT / slug / "latest")
    manifest_path = capture_url_stage(
        args.url,
        slug=slug,
        output_dir=output_dir,
        session=args.session,
        width=args.width,
        height=args.height,
    )
    payload = {
        "status": "passed",
        "url": args.url,
        "slug": slug,
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "workbench_command": f"./eba dev demo {manifest_path.relative_to(REPO_ROOT)}",
    }
    if args.json:
        print_json(payload)
    else:
        print(f"manifest={payload['manifest']}")
        if not args.no_browser:
            print(f"inspect={payload['workbench_command']}")
    return 0


def command_demo(args: argparse.Namespace) -> int:
    manifest = resolve_current_workbench_manifest(args)
    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 1
    release_default_demo_server(manifest)
    command = [
        sys.executable,
        str(WORKBENCH_GATE),
        "surface",
        str(manifest),
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
        if args.fixture == "easy-audit" or manifest.resolve() == (
            REPO_ROOT / "artifacts" / "easy-audit" / "latest" / "manifest.json"
        ).resolve():
            print("1. Confirm the artifact summary shows the Acme Robotics audit, not the public-page matrix.")
            print("2. Inspect the projected L0-L4 steps and provenance edges in the sidebar.")
            print("3. Open the final report and confirm the designed HTML report renders without edit controls.")
            print("4. Open the JSON/text artifacts and confirm they render as inspectable document views.")
        else:
            print("1. Inspect the artifact summary in the right sidebar.")
            print("2. Toggle page and slot filter chips; previous/next should follow the filtered set.")
            print("3. Open a markdown summary artifact and confirm edit/annotation still works.")
            print("4. Inspect tall/full-page captures; viewer zoom should fit without mutating image bytes.")
    return 0


def workbench_browser_command(
    action: str,
    *values: str,
    session: str = WORKBENCH_BROWSER_SESSION,
) -> list[str]:
    commands = {
        "tabs": ["tab-list"],
        "tab-select": ["tab-select", *values],
        "snapshot": ["snapshot", *values],
        "click": ["click", *values],
        "fill": ["fill", *values],
        "press": ["press", *values],
    }
    try:
        browser_args = commands[action]
    except KeyError as exc:
        raise SystemExit(f"Unsupported workbench action: {action}") from exc
    return [
        sys.executable,
        str(BROWSER_WRAPPER.relative_to(REPO_ROOT)),
        *browser_args,
        "--session",
        session,
    ]


def current_workbench_manifest() -> Path:
    command = [
        sys.executable,
        str(WORKBENCH_GATE),
        "status",
        str(DEFAULT_MANIFEST),
        "--port",
        WORKBENCH_PORT,
    ]
    completed = run(command, capture=True)
    if completed.returncode == 0:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = {}
        manifest = payload.get("active_manifest") or payload.get("manifest")
        if isinstance(manifest, str) and manifest:
            return REPO_ROOT / manifest
    return DEFAULT_MANIFEST


def command_workbench_refresh(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(WORKBENCH_GATE),
        "surface",
        str(current_workbench_manifest()),
        "--port",
        WORKBENCH_PORT,
        "--timeout",
        "10",
    ]
    if getattr(args, "json", False):
        command.append("--json")
    completed = run(command, capture=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


def command_workbench_live_smoke(args: argparse.Namespace) -> int:
    manifest = resolve_manifest(args)
    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 1
    release_default_demo_server(manifest)
    surface_command = [
        sys.executable,
        str(WORKBENCH_GATE),
        "surface",
        str(manifest),
        "--port",
        WORKBENCH_PORT,
        "--timeout",
        "10",
        "--json",
    ]
    surface = run(surface_command, capture=True)
    if surface.returncode != 0:
        if surface.stdout:
            print(surface.stdout, end="")
        if surface.stderr:
            print(surface.stderr, file=sys.stderr, end="")
        return surface.returncode

    smoke_command = [
        sys.executable,
        str(BROWSER_WRAPPER.relative_to(REPO_ROOT)),
        "run-code",
        str(WORKBENCH_LIVE_BOOT_SMOKE.relative_to(REPO_ROOT)),
        "--session",
        args.session,
    ]
    smoke = run(smoke_command, capture=True)
    if getattr(args, "json", False):
        try:
            surface_payload = json.loads(surface.stdout)
        except json.JSONDecodeError:
            surface_payload = {"raw": surface.stdout}
        smoke_payload = parse_playwright_cli_result(smoke.stdout)
        payload = {
            "manifest": str(manifest.relative_to(REPO_ROOT) if manifest.is_absolute() else manifest),
            "smoke": smoke_payload,
            "status": "passed" if smoke.returncode == 0 else "failed",
            "surface": surface_payload,
        }
        if smoke.returncode != 0 or smoke_payload is None:
            payload["smoke_stderr"] = smoke.stderr
            payload["smoke_stdout"] = smoke.stdout
        print_json(payload)
    else:
        if surface.stdout:
            print(surface.stdout, end="")
        if smoke.stdout:
            print(smoke.stdout, end="")
    if smoke.stderr:
        print(smoke.stderr, file=sys.stderr, end="")
    return smoke.returncode


def command_workbench(args: argparse.Namespace) -> int:
    action = args.workbench_action
    if action in {"click", "fill", "press"}:
        assert_dev_command_allowed(REPO_ROOT, "workbench", require_active_turn=True)
    if action == "reset":
        return command_demo(
            argparse.Namespace(
                manifest=args.manifest,
                fixture=args.fixture,
                no_browser=False,
                json=args.json,
            )
        )
    if action == "refresh":
        return command_workbench_refresh(args)
    if action == "live-smoke":
        return command_workbench_live_smoke(args)
    if action in {"context", "glance"}:
        manifest = resolve_manifest(args)
        command = [
            sys.executable,
            str(WORKBENCH_GATE),
            "state" if action == "context" else "glance",
            str(manifest),
            "--port",
            WORKBENCH_PORT,
        ]
        completed = run(command, capture=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        return completed.returncode
    values: list[str] = []
    if action == "tab-select":
        values = [str(args.index)]
    elif action == "snapshot":
        values = [str(args.output)]
    elif action == "click":
        values = [str(args.target)]
        if args.button:
            values.append(str(args.button))
    elif action == "fill":
        values = [str(args.target), str(args.text)]
    elif action == "press":
        values = [str(args.key)]
    command = workbench_browser_command(action, *values, session=args.session)
    completed = run(command, capture=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


def command_hooks(args: argparse.Namespace) -> int:
    if args.hooks_action == "install":
        completed = run(["git", "config", "core.hooksPath", "scripts/git-hooks"])
        if completed.returncode != 0:
            if completed.stderr:
                print(completed.stderr, file=sys.stderr, end="")
            return completed.returncode
        print("core.hooksPath=scripts/git-hooks")
        return 0
    if args.hooks_action == "status":
        completed = run(["git", "config", "--get", "core.hooksPath"])
        value = completed.stdout.strip() if completed.returncode == 0 else ""
        print(value or "(unset)")
        return 0
    raise SystemExit(f"Unsupported hooks action: {args.hooks_action}")


def body_from_args(args: argparse.Namespace) -> str:
    if args.body_file:
        if args.body_file == "-":
            return sys.stdin.read()
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body or ""


def signed_body_from_args(args: argparse.Namespace) -> str:
    signature = current_eba_signature(REPO_ROOT, worker_id=getattr(args, "worker_id", None))
    return append_signature_footer(body_from_args(args), signature.signature)


def command_gh(args: argparse.Namespace) -> int:
    body = signed_body_from_args(args)
    action = args.gh_action
    command: list[str]
    if action == "issue-comment":
        command = ["gh", "issue", "comment", args.issue, "--body-file", "-"]
    elif action == "pr-comment":
        command = ["gh", "pr", "comment", args.pr, "--body-file", "-"]
    elif action == "issue-edit":
        command = ["gh", "issue", "edit", args.issue, "--body-file", "-"]
        if args.title:
            command.extend(["--title", args.title])
    elif action == "pr-edit":
        command = ["gh", "pr", "edit", args.pr, "--body-file", "-"]
        if args.title:
            command.extend(["--title", args.title])
    elif action == "issue-create":
        command = ["gh", "issue", "create", "--title", args.title, "--body-file", "-"]
        for label in args.label or []:
            command.extend(["--label", label])
    elif action == "pr-create":
        command = ["gh", "pr", "create", "--title", args.title, "--body-file", "-"]
        if args.base:
            command.extend(["--base", args.base])
        if args.head:
            command.extend(["--head", args.head])
        for label in args.label or []:
            command.extend(["--label", label])
    else:
        raise SystemExit(f"Unsupported gh action: {action}")

    completed = run_with_stdin(command, body)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


def command_trace(args: argparse.Namespace) -> int:
    if not THREAD_WORKBENCH.exists():
        print(f"Trace workbench script not found: {THREAD_WORKBENCH}", file=sys.stderr)
        return 1
    if args.trace_action == "search":
        terms = list(args.terms)
        if args.worker_id:
            terms.append(args.worker_id)
        if args.turn_id:
            terms.append(args.turn_id)
        for keyword in args.keyword or []:
            terms.append(keyword)
        if not args.all_projects:
            terms.append(str(REPO_ROOT))
        if not terms:
            print("trace search requires at least one worker id, turn id, or keyword", file=sys.stderr)
            return 2
        command = [
            sys.executable,
            str(THREAD_WORKBENCH),
            "search",
            "--search-scope",
            "title-cwd-messages",
            "--search-mode",
            args.search_mode,
            "--max-list",
            str(args.max_list),
            "--since-days",
            str(args.since_days),
        ]
        for term in terms:
            command.extend(["--search-term", term])
    elif args.trace_action == "drill":
        command = [
            sys.executable,
            str(THREAD_WORKBENCH),
            "drill",
            "--thread",
            args.thread,
            "--limit",
            str(args.limit),
            "--context-chars",
            str(args.context_chars),
            "--search-mode",
            args.search_mode,
            "--non-interactive",
        ]
        for query in args.query:
            command.extend(["--query", query])
    else:
        raise SystemExit(f"Unsupported trace action: {args.trace_action}")

    completed = run(command, capture=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Employer Brand Audits project command surface.")
    subparsers = parser.add_subparsers(dest="family", required=True)

    begin = subparsers.add_parser("begin", help="Begin an agent control-plane turn")
    begin.add_argument("--worker-id")
    begin.set_defaults(func=command_begin)

    end = subparsers.add_parser("end", help="End an agent control-plane turn")
    end.add_argument("--worker-id", required=True)
    end.set_defaults(func=command_end)

    sig = subparsers.add_parser("sig", help="Print the active EBA signature")
    sig.add_argument("--worker-id", help="Select a specific active worker")
    sig.add_argument("--json", action="store_true")
    sig.set_defaults(func=command_sig)

    dev = subparsers.add_parser("dev", help="Developer and agent workflow commands")
    dev_subparsers = dev.add_subparsers(dest="command", required=True)

    situation = dev_subparsers.add_parser("situation", help="Print current repo and workbench state")
    situation.add_argument("--json", action="store_true")
    situation.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and inspect a named fixture")
    situation.add_argument("manifest", nargs="?", type=Path)
    situation.set_defaults(func=command_situation)

    validate = dev_subparsers.add_parser("validate", help="Run focused project validation")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=command_validate)

    stage_url = dev_subparsers.add_parser("stage-url", help="Capture a URL as a web snapshot artifact")
    stage_url.add_argument("url")
    stage_url.add_argument("--name", help="Stable human stage name or slug seed")
    stage_url.add_argument("--output-dir", type=Path)
    stage_url.add_argument("--session", default="eba-url-stage")
    stage_url.add_argument("--width", type=int, default=1365)
    stage_url.add_argument("--height", type=int, default=900)
    stage_url.add_argument("--json", action="store_true")
    stage_url.add_argument("--no-browser", action="store_true", help="Do not print a workbench inspection command")
    stage_url.set_defaults(func=command_stage_url)

    demo = dev_subparsers.add_parser("demo", help="Prepare the artifact workbench demo surface")
    demo.add_argument("manifest", nargs="?", type=Path)
    demo.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and demo a named fixture")
    demo.add_argument("--no-browser", action="store_true")
    demo.add_argument("--json", action="store_true")
    demo.set_defaults(func=command_demo)

    workbench = dev_subparsers.add_parser("workbench", help="Control the managed eba-workbench browser session")
    workbench.add_argument("--session", default=WORKBENCH_BROWSER_SESSION)
    workbench_subparsers = workbench.add_subparsers(dest="workbench_action", required=True)

    reset = workbench_subparsers.add_parser("reset", help="Start or reuse the managed workbench session")
    reset.add_argument("manifest", nargs="?", type=Path)
    reset.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and demo a named fixture")
    reset.add_argument("--json", action="store_true")
    reset.set_defaults(func=command_workbench)

    context = workbench_subparsers.add_parser("context", help="Print current workbench context and interaction overlays")
    context.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    context.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and inspect a named fixture")
    context.add_argument("--json", action="store_true")
    context.set_defaults(func=command_workbench)

    glance = workbench_subparsers.add_parser("glance", help="Print a compact live workbench summary")
    glance.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    glance.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and inspect a named fixture")
    glance.add_argument("--json", action="store_true")
    glance.set_defaults(func=command_workbench)

    refresh = workbench_subparsers.add_parser("refresh", help="Replace and raise the current workbench browser")
    refresh.add_argument("--json", action="store_true")
    refresh.set_defaults(func=command_workbench, values=[])

    live_smoke = workbench_subparsers.add_parser("live-smoke", help="Run a bounded live workbench boot smoke")
    live_smoke.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    live_smoke.add_argument("--fixture", choices=sorted(FIXTURE_GENERATORS), help="Generate and smoke a named fixture")
    live_smoke.add_argument("--json", action="store_true")
    live_smoke.set_defaults(func=command_workbench)

    tabs = workbench_subparsers.add_parser("tabs", help="List workbench browser tabs")
    tabs.set_defaults(func=command_workbench, values=[])

    tab_select = workbench_subparsers.add_parser("tab-select", help="Select a workbench browser tab")
    tab_select.add_argument("index")
    tab_select.set_defaults(func=command_workbench)

    snapshot = workbench_subparsers.add_parser("snapshot", help="Write a workbench accessibility snapshot")
    snapshot.add_argument("output")
    snapshot.set_defaults(func=command_workbench)

    click = workbench_subparsers.add_parser("click", help="Click a workbench target from a snapshot")
    click.add_argument("target")
    click.add_argument("button", nargs="?")
    click.set_defaults(func=command_workbench)

    fill = workbench_subparsers.add_parser("fill", help="Fill a workbench target from a snapshot")
    fill.add_argument("target")
    fill.add_argument("text")
    fill.set_defaults(func=command_workbench)

    press = workbench_subparsers.add_parser("press", help="Press a key in the workbench session")
    press.add_argument("key")
    press.set_defaults(func=command_workbench)

    hooks = dev_subparsers.add_parser("hooks", help="Install or inspect local EBA git hooks")
    hooks_subparsers = hooks.add_subparsers(dest="hooks_action", required=True)
    hooks_install = hooks_subparsers.add_parser("install", help="Install local git hooks for this checkout")
    hooks_install.set_defaults(func=command_hooks)
    hooks_status = hooks_subparsers.add_parser("status", help="Print configured git hooks path")
    hooks_status.set_defaults(func=command_hooks)

    trace = dev_subparsers.add_parser("trace", help="Search or drill local session archaeology")
    trace_subparsers = trace.add_subparsers(dest="trace_action", required=True)
    trace_search = trace_subparsers.add_parser("search", help="Search recent local sessions")
    trace_search.add_argument("terms", nargs="*", help="Worker IDs, turn IDs, or keywords")
    trace_search.add_argument("--worker-id")
    trace_search.add_argument("--turn-id")
    trace_search.add_argument("--keyword", action="append", default=[])
    trace_search.add_argument("--since-days", type=float, default=7.0)
    trace_search.add_argument("--max-list", type=int, default=20)
    trace_search.add_argument("--search-mode", choices=["all", "any"], default="all")
    trace_search.add_argument("--all-projects", action="store_true")
    trace_search.set_defaults(func=command_trace)
    trace_drill = trace_subparsers.add_parser("drill", help="Drill into one local session")
    trace_drill.add_argument("--thread", required=True)
    trace_drill.add_argument("--query", action="append", default=[])
    trace_drill.add_argument("--limit", type=int, default=20)
    trace_drill.add_argument("--context-chars", type=int, default=240)
    trace_drill.add_argument("--search-mode", choices=["all", "any"], default="all")
    trace_drill.set_defaults(func=command_trace)

    gh = dev_subparsers.add_parser("gh", help="Mutate GitHub prose with an EBA signature footer")
    gh.add_argument("--worker-id", help="Select a specific active worker for the signature")
    gh_subparsers = gh.add_subparsers(dest="gh_action", required=True)

    def add_body_args(target: argparse.ArgumentParser) -> None:
        body_group = target.add_mutually_exclusive_group(required=True)
        body_group.add_argument("--body")
        body_group.add_argument("--body-file")

    issue_comment = gh_subparsers.add_parser("issue-comment", help="Create a signed issue comment")
    issue_comment.add_argument("issue")
    add_body_args(issue_comment)
    issue_comment.set_defaults(func=command_gh)

    pr_comment = gh_subparsers.add_parser("pr-comment", help="Create a signed PR comment")
    pr_comment.add_argument("pr")
    add_body_args(pr_comment)
    pr_comment.set_defaults(func=command_gh)

    issue_edit = gh_subparsers.add_parser("issue-edit", help="Update a signed issue body")
    issue_edit.add_argument("issue")
    issue_edit.add_argument("--title")
    add_body_args(issue_edit)
    issue_edit.set_defaults(func=command_gh)

    pr_edit = gh_subparsers.add_parser("pr-edit", help="Update a signed PR body")
    pr_edit.add_argument("pr")
    pr_edit.add_argument("--title")
    add_body_args(pr_edit)
    pr_edit.set_defaults(func=command_gh)

    issue_create = gh_subparsers.add_parser("issue-create", help="Create a signed issue")
    issue_create.add_argument("--title", required=True)
    issue_create.add_argument("--label", action="append", default=[])
    add_body_args(issue_create)
    issue_create.set_defaults(func=command_gh)

    pr_create = gh_subparsers.add_parser("pr-create", help="Create a signed PR")
    pr_create.add_argument("--title", required=True)
    pr_create.add_argument("--base")
    pr_create.add_argument("--head")
    pr_create.add_argument("--label", action="append", default=[])
    add_body_args(pr_create)
    pr_create.set_defaults(func=command_gh)

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
