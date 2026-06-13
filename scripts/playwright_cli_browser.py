#!/usr/bin/env python3
"""Thin repository wrapper for Playwright CLI browser operations.

This script intentionally shells out to `playwright-cli`; it does not use the
Python Playwright API. ADR-008 makes Playwright CLI the browser boundary so
agents have one explicit path for navigation, setup, screenshots, and cleanup.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION = "eba"
DEFAULT_PROFILE = REPO_ROOT / "chrome-profile"


def _require_cli() -> str:
    exe = shutil.which("playwright-cli")
    if not exe:
        raise SystemExit(
            "playwright-cli not found on PATH. Install/activate the Playwright CLI before browser automation."
        )
    return exe


def _run(args: list[str]) -> int:
    exe = _require_cli()
    cmd = [exe] + args
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if "### Error" in completed.stdout or "### Error" in completed.stderr:
        return 1
    return completed.returncode


def _session_prefix(session: str) -> list[str]:
    return [f"-s={session}"]


def open_browser(args: argparse.Namespace) -> int:
    cmd = _session_prefix(args.session) + [
        "open",
        "--browser",
        args.browser,
    ]
    if args.headed:
        cmd.append("--headed")
    if args.persistent:
        cmd.append("--persistent")
        cmd.extend(["--profile", str(args.profile)])
    if args.url:
        cmd.append(args.url)
    return _run(cmd)


def goto(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["goto", args.url])


def resize(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["resize", str(args.width), str(args.height)])


def snapshot(args: argparse.Namespace) -> int:
    cmd = _session_prefix(args.session) + ["snapshot", "--boxes", "--filename", str(args.output)]
    if args.target:
        cmd.append(args.target)
    return _run(cmd)


def screenshot(args: argparse.Namespace) -> int:
    cmd = _session_prefix(args.session) + ["screenshot", "--filename", str(args.output)]
    if args.full_page:
        cmd.append("--full-page")
    if args.target:
        cmd.append(args.target)
    return _run(cmd)


def run_code(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["run-code", "--filename", str(args.file)])


def state_save(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["state-save", str(args.output)])


def state_load(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["state-load", str(args.file)])


def close(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["close"])


def close_all(_: argparse.Namespace) -> int:
    return _run(["close-all"])


def kill_all(_: argparse.Namespace) -> int:
    return _run(["kill-all"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repository wrapper around playwright-cli (ADR-008 browser boundary)."
    )
    parser.set_defaults(func=None)
    sub = parser.add_subparsers(dest="command", required=True)

    def with_session(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--session", default=DEFAULT_SESSION, help="Playwright CLI session name")
        return p

    p = with_session(sub.add_parser("open", help="Open a browser session"))
    p.add_argument("url", nargs="?", help="Initial URL")
    p.add_argument("--browser", default="chrome", choices=["chrome", "firefox", "webkit", "msedge"])
    p.add_argument("--headed", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--persistent", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    p.set_defaults(func=open_browser)

    p = with_session(sub.add_parser("goto", help="Navigate current session"))
    p.add_argument("url")
    p.set_defaults(func=goto)

    p = with_session(sub.add_parser("resize", help="Resize browser window"))
    p.add_argument("width", type=int)
    p.add_argument("height", type=int)
    p.set_defaults(func=resize)

    p = with_session(sub.add_parser("snapshot", help="Write accessibility snapshot with element boxes"))
    p.add_argument("output", type=Path)
    p.add_argument("--target")
    p.set_defaults(func=snapshot)

    p = with_session(sub.add_parser("screenshot", help="Write viewport/full-page/element screenshot"))
    p.add_argument("output", type=Path)
    p.add_argument("--target")
    p.add_argument("--full-page", action="store_true")
    p.set_defaults(func=screenshot)

    p = with_session(sub.add_parser("run-code", help="Run checked-in Playwright code snippet"))
    p.add_argument("file", type=Path)
    p.set_defaults(func=run_code)

    p = with_session(sub.add_parser("state-save", help="Save browser storage state"))
    p.add_argument("output", type=Path)
    p.set_defaults(func=state_save)

    p = with_session(sub.add_parser("state-load", help="Load browser storage state"))
    p.add_argument("file", type=Path)
    p.set_defaults(func=state_load)

    p = with_session(sub.add_parser("close", help="Close current browser session"))
    p.set_defaults(func=close)

    p = sub.add_parser("close-all", help="Close all Playwright CLI sessions")
    p.set_defaults(func=close_all)

    p = sub.add_parser("kill-all", help="Kill stale Playwright CLI sessions")
    p.set_defaults(func=kill_all)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
