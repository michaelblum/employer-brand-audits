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
    config = getattr(args, "config", None)
    if config:
        cmd.extend(["--config", str(config)])
    if args.url:
        cmd.append(args.url)
    return _run(cmd)


def goto(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["goto", args.url])


def reload_page(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["reload"])


def resize(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["resize", str(args.width), str(args.height)])


def window_maximize(args: argparse.Namespace) -> int:
    code = (
        "async page => {"
        "const cdp = await page.context().newCDPSession(page);"
        "const win = await cdp.send('Browser.getWindowForTarget');"
        "await cdp.send('Browser.setWindowBounds', {"
        "windowId: win.windowId,"
        "bounds: { windowState: 'normal' }"
        "});"
        "await page.waitForTimeout(100);"
        "await cdp.send('Browser.setWindowBounds', {"
        "windowId: win.windowId,"
        "bounds: { windowState: 'maximized' }"
        "});"
        "}"
    )
    return _run(_session_prefix(args.session) + ["run-code", code])


def window_focus(args: argparse.Namespace) -> int:
    # Do not add Browser.setWindowBounds here. Focus must not move or resize the
    # managed workbench window.
    code = (
        "async page => {"
        "await page.bringToFront();"
        "await page.evaluate(() => window.focus());"
        "}"
    )
    return _run(_session_prefix(args.session) + ["run-code", code])


def tab_list(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["tab-list"])


def tab_select(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["tab-select", str(args.index)])


def tab_close(args: argparse.Namespace) -> int:
    cmd = _session_prefix(args.session) + ["tab-close"]
    if args.index is not None:
        cmd.append(str(args.index))
    return _run(cmd)


def click(args: argparse.Namespace) -> int:
    cmd = _session_prefix(args.session) + ["click", args.target]
    if args.button:
        cmd.append(args.button)
    return _run(cmd)


def fill(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["fill", args.target, args.text])


def press(args: argparse.Namespace) -> int:
    return _run(_session_prefix(args.session) + ["press", args.key])


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
    p.add_argument("--config", type=Path)
    p.set_defaults(func=open_browser)

    p = with_session(sub.add_parser("goto", help="Navigate current session"))
    p.add_argument("url")
    p.set_defaults(func=goto)

    p = with_session(sub.add_parser("reload", help="Reload current page"))
    p.set_defaults(func=reload_page)

    p = with_session(sub.add_parser("resize", help="Resize browser window"))
    p.add_argument("width", type=int)
    p.add_argument("height", type=int)
    p.set_defaults(func=resize)

    p = with_session(sub.add_parser("window-maximize", help="Maximize the browser window on its current display"))
    p.set_defaults(func=window_maximize)

    p = with_session(sub.add_parser("window-focus", help="Bring the browser window to the front"))
    p.set_defaults(func=window_focus)

    p = with_session(sub.add_parser("tab-list", help="List browser tabs"))
    p.set_defaults(func=tab_list)

    p = with_session(sub.add_parser("tab-select", help="Select browser tab by index"))
    p.add_argument("index", type=int)
    p.set_defaults(func=tab_select)

    p = with_session(sub.add_parser("tab-close", help="Close browser tab by index"))
    p.add_argument("index", nargs="?", type=int)
    p.set_defaults(func=tab_close)

    p = with_session(sub.add_parser("click", help="Click an element target"))
    p.add_argument("target")
    p.add_argument("button", nargs="?")
    p.set_defaults(func=click)

    p = with_session(sub.add_parser("fill", help="Fill an element target"))
    p.add_argument("target")
    p.add_argument("text")
    p.set_defaults(func=fill)

    p = with_session(sub.add_parser("press", help="Press a key"))
    p.add_argument("key")
    p.set_defaults(func=press)

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
