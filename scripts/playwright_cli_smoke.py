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
EXAMPLE_URL = "https://example.com"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test Playwright CLI browser artifact generation via scripts/playwright_cli_browser.py."
    )
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Named Playwright CLI session")
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

    if output_dir == REPO_ROOT or REPO_ROOT not in output_dir.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {output_dir}")

    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not found on PATH")

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = output_dir / "example.snapshot.txt"
    viewport_path = output_dir / "example.viewport.png"
    full_page_path = output_dir / "example.full-page.png"
    visible_text_path = output_dir / "example.visible-text.stdout.txt"
    log_path = output_dir / "playwright-cli-smoke.log"

    failed = False
    try:
        run_step(
            "open example.com",
            command_for(args.session, "open", EXAMPLE_URL, "--no-persistent"),
            log_path,
        )
        run_step(
            "resize browser",
            command_for(args.session, "resize", args.width, args.height),
            log_path,
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
            "extract visible text",
            command_for(args.session, "run-code", TEXT_SNIPPET),
            log_path,
            stdout_path=visible_text_path,
        )
    except RuntimeError as exc:
        failed = True
        print(f"[smoke] {exc}", file=sys.stderr)
    finally:
        close_result = run_step(
            "close session",
            command_for(args.session, "close"),
            log_path,
            check=False,
        )
        if close_result.returncode != 0:
            failed = True

    print("\n[smoke] artifact paths")
    for path in [snapshot_path, viewport_path, full_page_path, visible_text_path, log_path]:
        status = "exists" if path.exists() else "missing"
        print(f"- {path} ({status})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
