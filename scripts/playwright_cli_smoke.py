#!/usr/bin/env python3
"""Run a minimal Playwright CLI browser smoke through the repo wrapper."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "playwright-cli-smoke" / "latest"
DEFAULT_SESSION = "eba-smoke"
DEFAULT_STATE_SESSION_SUFFIX = "state"
EXAMPLE_URL = "https://example.com"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test Playwright CLI browser artifact generation via scripts/playwright_cli_browser.py."
    )
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Named Playwright CLI session")
    parser.add_argument(
        "--state-session",
        help="Second named session for state-load proof; defaults to '<session>-state'",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Deterministic artifact directory to replace on each run",
    )
    parser.add_argument("--width", type=int, default=1280, help="Browser width")
    parser.add_argument("--height", type=int, default=900, help="Browser height")
    return parser.parse_args()


def command_for(session: str, *args: str | int | Path) -> list[str]:
    return [sys.executable, str(WRAPPER), *[str(arg) for arg in args], "--session", session]


def run_step(
    label: str,
    cmd: list[str],
    log_path: Path,
    stdout_path: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"[smoke] {label}")
    print("+ " + " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {label}\n")
        handle.write("+ " + " ".join(cmd) + "\n")
        if completed.stdout:
            handle.write("\n[stdout]\n")
            handle.write(completed.stdout)
            if not completed.stdout.endswith("\n"):
                handle.write("\n")
        if completed.stderr:
            handle.write("\n[stderr]\n")
            handle.write(completed.stderr)
            if not completed.stderr.endswith("\n"):
                handle.write("\n")
        handle.write(f"\n[exit_code] {completed.returncode}\n")

    if stdout_path is not None:
        stdout_path.write_text(completed.stdout, encoding="utf-8")

    cli_reported_error = "### Error" in completed.stdout or "### Error" in completed.stderr
    if check and (completed.returncode != 0 or cli_reported_error):
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")

    return completed


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    state_session = args.state_session or f"{args.session}-{DEFAULT_STATE_SESSION_SUFFIX}"

    if output_dir == REPO_ROOT or REPO_ROOT not in output_dir.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {output_dir}")

    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not found on PATH")

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = output_dir / "example.snapshot.txt"
    viewport_path = output_dir / "example.viewport.png"
    full_page_path = output_dir / "example.full-page.png"
    element_path = output_dir / "example.element-h1.png"
    visible_text_path = output_dir / "example.visible-text.stdout.txt"
    settle_path = output_dir / "example.settle.stdout.txt"
    hide_path = output_dir / "example.hide-obscuring.stdout.txt"
    restore_path = output_dir / "example.restore-page.stdout.txt"
    state_path = output_dir / "example.state.json"
    state_save_path = output_dir / "example.state-save.stdout.txt"
    state_load_path = output_dir / "example.state-load.stdout.txt"
    log_path = output_dir / "playwright-cli-smoke.log"

    failed = False
    primary_opened = False
    state_opened = False
    primary_closed = False
    state_closed = False
    try:
        run_step(
            "open example.com",
            command_for(args.session, "open", EXAMPLE_URL, "--no-persistent"),
            log_path,
        )
        primary_opened = True
        run_step(
            "resize browser",
            command_for(args.session, "resize", args.width, args.height),
            log_path,
        )
        run_step(
            "settle page",
            command_for(args.session, "run-code", SETTLE_SNIPPET),
            log_path,
            stdout_path=settle_path,
        )
        run_step(
            "hide obscuring elements",
            command_for(args.session, "run-code", HIDE_SNIPPET),
            log_path,
            stdout_path=hide_path,
        )
        run_step(
            "write snapshot with boxes",
            command_for(args.session, "snapshot", snapshot_path),
            log_path,
        )
        run_step(
            "write viewport screenshot",
            command_for(args.session, "screenshot", viewport_path),
            log_path,
        )
        run_step(
            "write full-page screenshot",
            command_for(args.session, "screenshot", full_page_path, "--full-page"),
            log_path,
        )
        run_step(
            "write h1 element screenshot",
            command_for(args.session, "screenshot", element_path, "--target", "h1"),
            log_path,
        )
        run_step(
            "extract visible text",
            command_for(args.session, "run-code", TEXT_SNIPPET),
            log_path,
            stdout_path=visible_text_path,
        )
        run_step(
            "restore page",
            command_for(args.session, "run-code", RESTORE_SNIPPET),
            log_path,
            stdout_path=restore_path,
        )
        run_step(
            "save browser state",
            command_for(args.session, "state-save", state_path),
            log_path,
            stdout_path=state_save_path,
        )
        run_step(
            "close primary session",
            command_for(args.session, "close"),
            log_path,
        )
        primary_closed = True
        run_step(
            "open state-load session",
            command_for(state_session, "open", "--no-persistent"),
            log_path,
        )
        state_opened = True
        run_step(
            "load browser state",
            command_for(state_session, "state-load", state_path),
            log_path,
            stdout_path=state_load_path,
        )
        run_step(
            "navigate state-load session",
            command_for(state_session, "goto", EXAMPLE_URL),
            log_path,
        )
    except RuntimeError as exc:
        failed = True
        print(f"[smoke] {exc}", file=sys.stderr)
    finally:
        if primary_opened and not primary_closed:
            primary_close_result = run_step(
                "close session",
                command_for(args.session, "close"),
                log_path,
                check=False,
            )
            if primary_close_result.returncode == 0:
                primary_closed = True
            else:
                failed = True
        if state_opened and not state_closed:
            state_close_result = run_step(
                "close state-load session",
                command_for(state_session, "close"),
                log_path,
                check=False,
            )
            if state_close_result.returncode == 0:
                state_closed = True
            else:
                failed = True

    print("\n[smoke] artifact paths")
    for path in [
        snapshot_path,
        viewport_path,
        full_page_path,
        element_path,
        visible_text_path,
        settle_path,
        hide_path,
        restore_path,
        state_path,
        state_save_path,
        state_load_path,
        log_path,
    ]:
        status = "exists" if path.exists() else "missing"
        print(f"- {path} ({status})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
