#!/usr/bin/env python3
"""Exercise Playwright CLI browser capture against one real public page."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "playwright-cli-public-page" / "latest"
DEFAULT_SESSION = "eba-public-page"
DEFAULT_URL = "https://www.mozilla.org/en-US/careers/"
DEFAULT_TARGET = "main"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test Playwright CLI browser artifacts on a stable public careers/about page."
    )
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Named Playwright CLI session")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Public page URL to open; avoid anti-bot-heavy job-board surfaces for this smoke",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help="Selector or snapshot element ref for the element screenshot",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Deterministic artifact directory to replace on each run",
    )
    parser.add_argument("--width", type=int, default=1365, help="Browser width")
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
    print(f"[public-page-smoke] {label}")
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

    log_path = output_dir / "playwright-cli-public-page-smoke.log"
    url_path = output_dir / "public-page.url.txt"
    snapshot_path = output_dir / "public-page.snapshot.txt"
    viewport_path = output_dir / "public-page.viewport.png"
    full_page_path = output_dir / "public-page.full-page.png"
    element_path = output_dir / "public-page.element.png"
    visible_text_path = output_dir / "public-page.visible-text.stdout.txt"
    settle_path = output_dir / "public-page.settle.stdout.txt"
    hide_path = output_dir / "public-page.hide-obscuring.stdout.txt"
    restore_path = output_dir / "public-page.restore-page.stdout.txt"

    url_path.write_text(f"{args.url}\n", encoding="utf-8")

    failed = False
    opened = False
    closed = False
    try:
        run_step(
            "open public page",
            command_for(args.session, "open", args.url, "--no-persistent"),
            log_path,
        )
        opened = True
        run_step(
            "resize desktop viewport",
            command_for(args.session, "resize", args.width, args.height),
            log_path,
        )
        run_step(
            "settle public page",
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
            "extract visible text",
            command_for(args.session, "run-code", TEXT_SNIPPET),
            log_path,
            stdout_path=visible_text_path,
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
            f"write element screenshot for {args.target}",
            command_for(args.session, "screenshot", element_path, "--target", args.target),
            log_path,
        )
        run_step(
            "restore page",
            command_for(args.session, "run-code", RESTORE_SNIPPET),
            log_path,
            stdout_path=restore_path,
        )
    except RuntimeError as exc:
        failed = True
        print(f"[public-page-smoke] {exc}", file=sys.stderr)
    finally:
        if opened and not closed:
            close_result = run_step(
                "close session",
                command_for(args.session, "close"),
                log_path,
                check=False,
            )
            if close_result.returncode == 0:
                closed = True
            else:
                failed = True

    print("\n[public-page-smoke] artifact paths")
    for path in [
        url_path,
        snapshot_path,
        visible_text_path,
        viewport_path,
        full_page_path,
        element_path,
        settle_path,
        hide_path,
        restore_path,
        log_path,
    ]:
        status = "exists" if path.exists() else "missing"
        print(f"- {path} ({status})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
