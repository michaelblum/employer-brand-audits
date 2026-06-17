#!/usr/bin/env python3
"""Manage the local Playwright CLI artifact viewer server."""

import argparse
import json
import os
import re
import shlex
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from playwright_cli_workbench_server import (
        WORKBENCH_ASSET_MANIFEST_PATH,
        WORKBENCH_STATE_PATH,
        build_workbench_asset_manifest,
        manifest_state_fingerprint,
    )
except ModuleNotFoundError:
    from scripts.playwright_cli_workbench_server import (
        WORKBENCH_ASSET_MANIFEST_PATH,
        WORKBENCH_STATE_PATH,
        build_workbench_asset_manifest,
        manifest_state_fingerprint,
    )


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)
SERVER_SCRIPT = REPO_ROOT / "scripts" / "playwright_cli_workbench_server.py"
BROWSER_WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
PID_NAME = "workbench-server.pid"
LOG_NAME = "workbench-server.log"
STATE_NAME = "workbench-server-state.json"
BROWSER_STATE_NAME = "workbench-browser-state.json"
BROWSER_LOG_NAME = "workbench-browser.log"
DEFAULT_BROWSER_SESSION = "eba-workbench"
DEFAULT_BROWSER_PROFILE = REPO_ROOT / "chrome-profile" / "workbench"
DEFAULT_BROWSER_CONFIG = REPO_ROOT / "scripts" / "playwright_cli_workbench_config.json"
TAB_LIST_LINE_RE = re.compile(
    r"^- (?P<index>\d+): (?P<current>\(current\) )?\[(?P<title>.*)\]\((?P<url>.*)\)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start, inspect, stop, open, or read a Playwright CLI artifact viewer."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("start", "status", "stop", "open", "state", "glance", "surface"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
        if command in {"start", "status", "state", "glance", "surface"}:
            subparser.add_argument("--host", default=DEFAULT_HOST)
            subparser.add_argument("--port", type=int, default=DEFAULT_PORT)
        if command in {"start", "surface"}:
            subparser.add_argument("--open", action="store_true")
            subparser.add_argument("--timeout", type=float, default=10.0)
        if command in {"start", "open", "surface"}:
            subparser.add_argument(
                "--browser-session",
                default=DEFAULT_BROWSER_SESSION,
                help="Named Playwright CLI session for the workbench browser",
            )
            subparser.add_argument(
                "--profile",
                type=Path,
                default=DEFAULT_BROWSER_PROFILE,
                help="Persistent browser profile for the workbench browser",
            )
            subparser.add_argument(
                "--channel",
                default="chrome",
                help="Browser channel for the repo Playwright CLI wrapper",
            )
            subparser.add_argument(
                "--viewport-size",
                default=None,
                help=(
                    "Optional emulated browser viewport as WIDTH,HEIGHT. "
                    "Omit for the human workbench so page width follows the Chrome window."
                ),
            )
        if command == "surface":
            subparser.add_argument(
                "--no-browser",
                action="store_true",
                help="Start/reuse the workbench and print model URLs without opening Chrome",
            )
            subparser.add_argument(
                "--json",
                action="store_true",
                help="Print a single JSON payload for agents",
            )

    return parser.parse_args()


def safe_manifest_path(path: Path) -> Path:
    manifest_path = path.resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if manifest_path.name != "manifest.json":
        raise SystemExit(f"Expected an aggregate manifest.json path: {manifest_path}")
    if REPO_ROOT not in manifest_path.parents:
        raise SystemExit(f"Manifest must be inside the repository: {manifest_path}")
    return manifest_path


def paths_for(manifest_path: Path) -> dict[str, Path]:
    artifact_root = manifest_path.parent
    return {
        "artifact_root": artifact_root,
        "pid": artifact_root / PID_NAME,
        "log": artifact_root / LOG_NAME,
        "state": artifact_root / STATE_NAME,
        "browser_state": artifact_root / BROWSER_STATE_NAME,
        "browser_log": artifact_root / BROWSER_LOG_NAME,
    }


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def update_json_file(path: Path, mutator: Any) -> bool:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    before = json.dumps(value, sort_keys=True)
    mutator(value)
    after = json.dumps(value, sort_keys=True)
    if before == after:
        return False
    write_json_atomic(path, value)
    return True


def sanitize_workbench_browser_profile(profile: Path) -> list[str]:
    """Clear Chrome restore/first-run state before relaunching the workbench."""
    changed: list[str] = []

    def clean_preferences(value: dict[str, Any]) -> None:
        profile_state = value.setdefault("profile", {})
        if isinstance(profile_state, dict):
            profile_state["exit_type"] = "Normal"
            profile_state["exited_cleanly"] = True
        sessions = value.setdefault("sessions", {})
        if isinstance(sessions, dict):
            sessions["event_log"] = []
        browser = value.setdefault("browser", {})
        if isinstance(browser, dict):
            browser["has_seen_welcome_page"] = True

    def clean_local_state(value: dict[str, Any]) -> None:
        metrics = value.setdefault("user_experience_metrics", {})
        if not isinstance(metrics, dict):
            return
        stability = metrics.setdefault("stability", {})
        if isinstance(stability, dict):
            stability["exited_cleanly"] = True

    preference_path = profile / "Default" / "Preferences"
    local_state_path = profile / "Local State"
    if update_json_file(preference_path, clean_preferences):
        changed.append(relative_path(preference_path))
    if update_json_file(local_state_path, clean_local_state):
        changed.append(relative_path(local_state_path))
    return changed


def read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_command(pid: int) -> str:
    completed = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def process_table() -> list[tuple[int, str]]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    rows: list[tuple[int, str]] = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        rows.append((pid, parts[1]))
    return rows


def workbench_profile_owner_pids(profile: Path, session: str) -> list[int]:
    absolute_profile = str(profile.resolve())
    relative_profile = relative_path(profile)
    current_pid = os.getpid()
    pids: list[int] = []
    for pid, command in process_table():
        if pid == current_pid:
            continue
        owns_profile = (
            f"--user-data-dir={absolute_profile}" in command
            or f"--profile={absolute_profile}" in command
            or f"--profile={relative_profile}" in command
            or f"--profile {absolute_profile}" in command
            or f"--profile {relative_profile}" in command
        )
        owns_daemon_session = "cliDaemon.js" in command and session in command
        if owns_profile or (owns_daemon_session and relative_profile in command):
            pids.append(pid)
    return sorted(set(pids))


def stop_stale_workbench_profile_owners(pids: list[int], log_handle: Any) -> None:
    if not pids:
        return
    log_handle.write("\n## stop stale workbench profile owners " + ", ".join(map(str, pids)) + "\n")
    log_handle.flush()
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError:
                log_handle.write(f"permission denied killing stale profile owner {pid}\n")
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if not any(pid_alive(pid) for pid in pids):
                return
            time.sleep(0.1)


def workbench_server_manifest_from_command(command: str) -> Path | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    for index, part in enumerate(parts):
        if part == str(SERVER_SCRIPT) or part.endswith("playwright_cli_workbench_server.py"):
            if index + 1 >= len(parts):
                return None
            candidate = Path(parts[index + 1]).expanduser().resolve()
            if candidate.name == "manifest.json" and REPO_ROOT in candidate.parents:
                return candidate
    return None


def active_workbench_server_manifest(pid: int) -> Path | None:
    command = process_command(pid)
    return workbench_server_manifest_from_command(command)


def is_repo_workbench_server(pid: int) -> bool:
    command = process_command(pid)
    return (
        "playwright_cli_workbench_server.py" in command
        and workbench_server_manifest_from_command(command) is not None
    )


def is_owned_workbench_server(pid: int, manifest_path: Path) -> bool:
    active_manifest = active_workbench_server_manifest(pid)
    return (
        active_manifest is not None
        and active_manifest == manifest_path.resolve()
        and is_repo_workbench_server(pid)
    )


def remove_stale_state(paths: dict[str, Path]) -> None:
    for key in ("pid", "state"):
        paths[key].unlink(missing_ok=True)


def stop_owned_pid(pid: int, paths: dict[str, Path]) -> str:
    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if not pid_alive(pid):
            remove_stale_state(paths)
            return "stopped"
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    remove_stale_state(paths)
    return "killed"


def health(url: str, timeout: float = 1.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500, str(response.status)
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 500, str(exc.code)
    except OSError as exc:
        return False, exc.__class__.__name__


def fetch_json_url(url: str, timeout: float = 1.0) -> tuple[dict[str, Any] | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None, str(response.status)
            return json.loads(response.read().decode("utf-8")), str(response.status)
    except urllib.error.HTTPError as exc:
        return None, str(exc.code)
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError as exc:
        return None, exc.__class__.__name__


def asset_url_status(url: str, timeout: float = 1.0) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return str(response.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except OSError as exc:
        return exc.__class__.__name__


def workbench_asset_health(url: str, timeout: float = 1.0) -> dict[str, Any]:
    root_url = url.rstrip("/")
    expected = build_workbench_asset_manifest()
    manifest_url = f"{root_url}{WORKBENCH_ASSET_MANIFEST_PATH}"
    expected_assets = expected.get("assets", [])
    local_assets = [expected.get("index"), *expected_assets] if isinstance(expected_assets, list) else [expected.get("index")]
    local_missing = [
        asset.get("url")
        for asset in local_assets
        if isinstance(asset, dict) and not asset.get("exists")
    ]
    if local_missing:
        return {
            "healthy": False,
            "status": "expected_asset_missing",
            "manifest_url": manifest_url,
            "missing_assets": local_missing,
            "expected_fingerprint": expected.get("fingerprint"),
        }

    actual, manifest_status = fetch_json_url(manifest_url, timeout=timeout)
    if actual is None:
        return {
            "healthy": False,
            "status": f"asset_manifest_unavailable:{manifest_status}",
            "manifest_url": manifest_url,
            "expected_fingerprint": expected.get("fingerprint"),
            "actual_fingerprint": None,
        }
    if actual.get("fingerprint") != expected.get("fingerprint"):
        return {
            "healthy": False,
            "status": "asset_fingerprint_mismatch",
            "manifest_url": manifest_url,
            "expected_fingerprint": expected.get("fingerprint"),
            "actual_fingerprint": actual.get("fingerprint"),
        }
    if actual.get("server_source_fingerprint") != expected.get("server_source_fingerprint"):
        return {
            "healthy": False,
            "status": "server_source_fingerprint_mismatch",
            "manifest_url": manifest_url,
            "expected_server_source_fingerprint": expected.get("server_source_fingerprint"),
            "actual_server_source_fingerprint": actual.get("server_source_fingerprint"),
            "expected_fingerprint": expected.get("fingerprint"),
            "actual_fingerprint": actual.get("fingerprint"),
        }

    failed_assets = []
    for asset in expected_assets if isinstance(expected_assets, list) else []:
        if not isinstance(asset, dict):
            continue
        asset_path = str(asset.get("url") or "")
        if not asset_path:
            continue
        asset_status = asset_url_status(f"{root_url}{asset_path}", timeout=timeout)
        if asset_status != "200":
            failed_assets.append({"url": asset_path, "status": asset_status})
    if failed_assets:
        return {
            "healthy": False,
            "status": f"asset_url_unavailable:{failed_assets[0]['status']}",
            "manifest_url": manifest_url,
            "expected_fingerprint": expected.get("fingerprint"),
            "actual_fingerprint": actual.get("fingerprint"),
            "failed_assets": failed_assets,
        }
    return {
        "healthy": True,
        "status": "ok",
        "manifest_url": manifest_url,
        "asset_count": expected.get("asset_count"),
        "fingerprint": expected.get("fingerprint"),
        "server_source_fingerprint": expected.get("server_source_fingerprint"),
    }


def port_accepts_connection(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def listening_pid(host: str, port: int) -> int | None:
    completed = subprocess.run(
        ["lsof", "-nP", f"-iTCP@{host}:{port}", "-sTCP:LISTEN", "-t"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        try:
            return int(line.strip())
        except ValueError:
            continue
    return None


def wait_for_port_release(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not port_accepts_connection(host, port):
            return True
        time.sleep(0.1)
    return not port_accepts_connection(host, port)


def wait_for_health(url: str, timeout: float) -> tuple[bool, str]:
    deadline = time.time() + timeout
    last_status = "not_checked"
    while time.time() < deadline:
        healthy, status = health(url)
        if healthy:
            return True, status
        last_status = status
        time.sleep(0.15)
    return False, last_status


def command_quiet(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "quiet", False))


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def parse_viewport_size(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split(",", 1)]
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise SystemExit(f"Expected viewport size as WIDTH,HEIGHT: {value}")
    return parts[0], parts[1]


def require_workbench_browser_wrapper() -> Path:
    if not BROWSER_WRAPPER.exists():
        raise SystemExit(
            f"Repo Playwright CLI wrapper not found: {relative_path(BROWSER_WRAPPER)}. "
            "Repair scripts/playwright_cli_browser.py or run surface --no-browser."
        )
    completed = subprocess.run(
        [sys.executable, str(BROWSER_WRAPPER), "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "Repo Playwright CLI wrapper failed health check. "
            f"command={sys.executable} {BROWSER_WRAPPER} --help\n{completed.stderr or completed.stdout}"
        )
    return BROWSER_WRAPPER


def require_session_aware_cli() -> str:
    exe = shutil.which("playwright-cli")
    if not exe:
        raise SystemExit(
            "playwright-cli not found on PATH. Install/activate the session-aware Playwright CLI "
            "or run surface --no-browser."
        )
    completed = subprocess.run(
        [exe, "list", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "playwright-cli exists but does not expose the required named-session API. "
            "Expected `playwright-cli list --json` to work; do not use ordinary Playwright for "
            f"the workbench browser.\n{completed.stderr or completed.stdout}"
        )
    return exe


def build_workbench_browser_plan(
    url: str,
    *,
    session: str,
    browser: str,
    viewport_size: str | None,
    profile: Path = DEFAULT_BROWSER_PROFILE,
    config: Path = DEFAULT_BROWSER_CONFIG,
) -> dict[str, Any]:
    wrapper = relative_path(BROWSER_WRAPPER)
    profile_path = relative_path(profile)
    config_path = relative_path(config)
    common = ["--session", session]
    initial_resize_command = None
    if viewport_size:
        width, height = parse_viewport_size(viewport_size)
        initial_resize_command = [
            sys.executable,
            wrapper,
            "resize",
            width,
            height,
            *common,
        ]
    return {
        "session": session,
        "profile": profile_path,
        "config": config_path,
        "browser": browser,
        "url": url,
        "viewport_size": viewport_size,
        "open_command": [
            sys.executable,
            wrapper,
            "open",
            url,
            *common,
            "--browser",
            browser,
            "--persistent",
            "--profile",
            profile_path,
            "--config",
            config_path,
        ],
        "window_maximize_command": [
            sys.executable,
            wrapper,
            "window-maximize",
            *common,
        ],
        "window_focus_command": [
            sys.executable,
            wrapper,
            "window-focus",
            *common,
        ],
        "close_command": [
            sys.executable,
            wrapper,
            "close",
            *common,
        ],
        "goto_command": [
            sys.executable,
            wrapper,
            "goto",
            url,
            *common,
        ],
        "initial_resize_command": initial_resize_command,
    }


def tab_list_command(session: str) -> list[str]:
    return [
        sys.executable,
        relative_path(BROWSER_WRAPPER),
        "tab-list",
        "--session",
        session,
    ]


def tab_select_command(session: str, index: int) -> list[str]:
    return [
        sys.executable,
        relative_path(BROWSER_WRAPPER),
        "tab-select",
        str(index),
        "--session",
        session,
    ]


def tab_close_command(session: str, index: int) -> list[str]:
    return [
        sys.executable,
        relative_path(BROWSER_WRAPPER),
        "tab-close",
        str(index),
        "--session",
        session,
    ]


def parse_browser_tabs(stdout: str) -> list[dict[str, Any]]:
    tabs: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        match = TAB_LIST_LINE_RE.match(line.strip())
        if not match:
            continue
        tabs.append(
            {
                "index": int(match.group("index")),
                "current": bool(match.group("current")),
                "title": match.group("title"),
                "url": match.group("url"),
            }
        )
    return tabs


def normalized_tab_url(url: str) -> tuple[str, str, str, str] | None:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    path = parsed.path.rstrip("/") or "/"
    return (parsed.scheme, parsed.netloc, path, parsed.query)


def tab_matches_url(tab_url: str, target_url: str) -> bool:
    return normalized_tab_url(tab_url) == normalized_tab_url(target_url)


def is_blank_tab(tab_url: str) -> bool:
    return tab_url in {"about:blank", "chrome://newtab/"}


def clean_workbench_tabs(url: str, *, session: str, log_handle: Any) -> dict[str, Any]:
    list_result = run_browser_command(tab_list_command(session), log_handle)
    if list_result.returncode != 0:
        return {
            "status": "tab_list_failed",
            "closed_indexes": [],
            "kept_index": None,
            "tab_count": None,
        }
    tabs = parse_browser_tabs(list_result.stdout)
    matching_tabs = [tab for tab in tabs if tab_matches_url(str(tab.get("url") or ""), url)]
    if not matching_tabs:
        return {
            "status": "no_matching_workbench_tab",
            "closed_indexes": [],
            "kept_index": None,
            "tab_count": len(tabs),
        }
    keep_tab = next((tab for tab in matching_tabs if tab.get("current")), matching_tabs[0])
    keep_index = int(keep_tab["index"])
    if not keep_tab.get("current"):
        select_result = run_browser_command(tab_select_command(session, keep_index), log_handle)
        if select_result.returncode != 0:
            return {
                "status": "tab_select_failed",
                "closed_indexes": [],
                "kept_index": keep_index,
                "tab_count": len(tabs),
            }
    close_indexes = sorted(
        [
            int(tab["index"])
            for tab in tabs
            if int(tab["index"]) != keep_index
            and (
                is_blank_tab(str(tab.get("url") or ""))
                or tab_matches_url(str(tab.get("url") or ""), url)
            )
        ],
        reverse=True,
    )
    closed_indexes = []
    for index in close_indexes:
        close_result = run_browser_command(tab_close_command(session, index), log_handle)
        if close_result.returncode != 0:
            return {
                "status": "tab_close_failed",
                "closed_indexes": closed_indexes,
                "failed_index": index,
                "kept_index": keep_index,
                "tab_count": len(tabs),
            }
        closed_indexes.append(index)
    return {
        "status": "cleaned",
        "closed_indexes": closed_indexes,
        "kept_index": keep_index,
        "tab_count": len(tabs),
    }


def browser_session_status_from_list(stdout: str, *, session: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "session": session,
            "alive": False,
            "status": "invalid_json",
        }
    browsers = payload.get("browsers") if isinstance(payload, dict) else None
    if not isinstance(browsers, list):
        return {
            "session": session,
            "alive": False,
            "status": "missing_browsers",
        }
    for browser in browsers:
        if not isinstance(browser, dict) or browser.get("name") != session:
            continue
        profile = browser.get("userDataDir")
        profile_path = relative_path(Path(profile)) if profile else None
        status = str(browser.get("status") or "unknown")
        return {
            "session": session,
            "alive": status == "open",
            "status": status,
            "browser_type": browser.get("browserType"),
            "headed": browser.get("headed"),
            "persistent": browser.get("persistent"),
            "profile": profile_path,
            "compatible": browser.get("compatible"),
        }
    return {
        "session": session,
        "alive": False,
        "status": "not_found",
        "profile": relative_path(DEFAULT_BROWSER_PROFILE),
    }


def browser_session_status(session: str) -> dict[str, Any]:
    exe = shutil.which("playwright-cli")
    if not exe:
        return {
            "session": session,
            "alive": False,
            "status": "playwright_cli_missing",
            "profile": relative_path(DEFAULT_BROWSER_PROFILE),
        }
    completed = subprocess.run(
        [exe, "list", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "session": session,
            "alive": False,
            "status": "session_api_unavailable",
            "stderr": completed.stderr.strip(),
            "profile": relative_path(DEFAULT_BROWSER_PROFILE),
        }
    return browser_session_status_from_list(completed.stdout, session=session)


def run_browser_command(command: list[str], log_handle: Any) -> subprocess.CompletedProcess[str]:
    log_handle.write("+ " + " ".join(command) + "\n")
    log_handle.flush()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        log_handle.write("\n[stdout]\n")
        log_handle.write(completed.stdout)
        if not completed.stdout.endswith("\n"):
            log_handle.write("\n")
    if completed.stderr:
        log_handle.write("\n[stderr]\n")
        log_handle.write(completed.stderr)
        if not completed.stderr.endswith("\n"):
            log_handle.write("\n")
    log_handle.write(f"\n[exit_code] {completed.returncode}\n")
    log_handle.flush()
    return completed


def browser_page_metrics(session: str) -> dict[str, Any]:
    exe = require_session_aware_cli()
    completed = subprocess.run(
        [
            exe,
            f"-s={session}",
            "--json",
            "eval",
            (
                "() => ({"
                "innerWidth: window.innerWidth,"
                "innerHeight: window.innerHeight,"
                "outerWidth: window.outerWidth,"
                "outerHeight: window.outerHeight,"
                "screenX: window.screenX,"
                "screenY: window.screenY,"
                "devicePixelRatio: window.devicePixelRatio,"
                "screenWidth: window.screen.width,"
                "screenHeight: window.screen.height,"
                "screenAvailWidth: window.screen.availWidth,"
                "screenAvailHeight: window.screen.availHeight,"
                "screenAvailLeft: Number.isFinite(window.screen.availLeft) ? window.screen.availLeft : 0,"
                "screenAvailTop: Number.isFinite(window.screen.availTop) ? window.screen.availTop : 0"
                "})"
            ),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {"error": completed.stderr.strip() or completed.stdout.strip()}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "stdout": completed.stdout.strip()}
    result = payload.get("result")
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return {"error": "invalid_result_json", "result": result}
        if isinstance(parsed, dict):
            return parsed
    if isinstance(result, dict):
        return result
    return {"error": "missing_result", "payload": payload}


def metric_number(metrics: dict[str, Any], key: str) -> float:
    value = metrics[key]
    if isinstance(value, bool):
        raise ValueError(key)
    return float(value)


def browser_display_signature(metrics: dict[str, Any]) -> dict[str, float] | None:
    keys = (
        "screenX",
        "screenY",
        "screenAvailLeft",
        "screenAvailTop",
        "screenAvailWidth",
        "screenAvailHeight",
        "devicePixelRatio",
    )
    try:
        return {key: metric_number(metrics, key) for key in keys}
    except (KeyError, TypeError, ValueError):
        return None


def viewport_target_from_metrics(metrics: dict[str, Any]) -> tuple[int, int] | None:
    try:
        avail_width = metric_number(metrics, "screenAvailWidth")
        avail_height = metric_number(metrics, "screenAvailHeight")
        if avail_width > 0 and avail_height > 0:
            return int(round(avail_width)), int(round(avail_height))
    except (KeyError, TypeError, ValueError):
        pass
    try:
        return (
            int(metric_number(metrics, "outerWidth")),
            int(metric_number(metrics, "outerHeight")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def viewport_sync_command(session: str, metrics: dict[str, Any]) -> list[str] | None:
    try:
        inner_width = int(metric_number(metrics, "innerWidth"))
        inner_height = int(metric_number(metrics, "innerHeight"))
    except (KeyError, TypeError, ValueError):
        return None
    target = viewport_target_from_metrics(metrics)
    if target is None:
        return None
    target_width, target_height = target
    if inner_width <= 0 or inner_height <= 0 or target_width <= 0 or target_height <= 0:
        return None
    if abs(inner_width - target_width) <= 1 and abs(inner_height - target_height) <= 1:
        return None
    return [
        sys.executable,
        relative_path(BROWSER_WRAPPER),
        "resize",
        str(target_width),
        str(target_height),
        "--session",
        session,
    ]


def open_or_reuse_managed_workbench(
    plan: dict[str, Any],
    before: dict[str, Any],
    log_handle: Any,
) -> tuple[str, subprocess.CompletedProcess[str]]:
    action_command = plan["goto_command"] if before.get("alive") else plan["open_command"]
    action = "goto" if before.get("alive") else "open"
    log_handle.write(f"\n## {action} {int(time.time())} {plan['url']}\n")
    return action, run_browser_command(action_command, log_handle)


def close_reused_managed_workbench(
    plan: dict[str, Any],
    before: dict[str, Any],
    log_handle: Any,
) -> subprocess.CompletedProcess[str] | None:
    if not before.get("alive"):
        return None
    log_handle.write(f"\n## close {int(time.time())} {plan['session']}\n")
    return run_browser_command(plan["close_command"], log_handle)


def apply_explicit_initial_viewport_resize(
    plan: dict[str, Any],
    action: str,
    log_handle: Any,
) -> subprocess.CompletedProcess[str] | None:
    if action != "open" or plan["initial_resize_command"] is None:
        return None
    return run_browser_command(plan["initial_resize_command"], log_handle)


def sync_managed_workbench_viewport_to_display(
    *,
    session: str,
    plan: dict[str, Any],
    action: str,
    previous_browser_state: dict[str, Any],
    log_handle: Any,
) -> dict[str, Any]:
    """Maximize/sync only when display state says the fixed viewport is stale."""
    viewport_metrics = browser_page_metrics(session)
    display_signature = browser_display_signature(viewport_metrics)
    viewport_target = None
    window_maximize_result = None
    viewport_sync_result = None
    previous_signature = (
        previous_browser_state.get("display_signature")
        if isinstance(previous_browser_state, dict)
        else None
    )
    should_reset_window = (
        action == "open"
        or previous_signature is None
        or (
            display_signature is not None
            and previous_signature != display_signature
        )
    )
    if should_reset_window:
        window_maximize_result = run_browser_command(
            plan["window_maximize_command"],
            log_handle,
        )
        if window_maximize_result.returncode == 0:
            viewport_metrics = browser_page_metrics(session)
            display_signature = browser_display_signature(viewport_metrics)
        sync_command = viewport_sync_command(session, viewport_metrics)
        viewport_target = viewport_target_from_metrics(viewport_metrics)
        if sync_command is not None:
            viewport_sync_result = run_browser_command(sync_command, log_handle)
            if viewport_sync_result.returncode == 0:
                viewport_metrics = browser_page_metrics(session)
                display_signature = browser_display_signature(viewport_metrics)
                viewport_target = viewport_target_from_metrics(viewport_metrics)
    else:
        viewport_target = viewport_target_from_metrics(viewport_metrics)
    return {
        "display_signature": display_signature,
        "viewport_metrics": viewport_metrics,
        "viewport_target": viewport_target,
        "window_maximize_result": window_maximize_result,
        "viewport_sync_result": viewport_sync_result,
    }


def bring_managed_workbench_to_front(
    plan: dict[str, Any],
    log_handle: Any,
) -> subprocess.CompletedProcess[str]:
    # Keep focus separate from resize/maximize. This path must not move or resize
    # the human-positioned workbench window.
    return run_browser_command(plan["window_focus_command"], log_handle)


def open_with_playwright(
    url: str,
    paths: dict[str, Path],
    channel: str,
    viewport_size: str | None,
    *,
    session: str = DEFAULT_BROWSER_SESSION,
    profile: Path = DEFAULT_BROWSER_PROFILE,
    replace_existing_session: bool = False,
) -> dict[str, Any]:
    require_session_aware_cli()
    require_workbench_browser_wrapper()
    paths["artifact_root"].mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, exist_ok=True)
    plan = build_workbench_browser_plan(
        url,
        session=session,
        browser=channel,
        viewport_size=viewport_size,
        profile=profile,
    )
    before = browser_session_status(session)
    previous_browser_state = read_json(paths["browser_state"], {})
    resize_result = None
    window_maximize_result = None
    window_focus_result = None
    viewport_sync_result = None
    close_result = None
    viewport_metrics = None
    display_signature = None
    viewport_target = None
    profile_sanitized: list[str] = []
    stale_profile_owners: list[int] = []
    tab_cleanup_result = None
    with paths["browser_log"].open("a", encoding="utf-8") as log_handle:
        effective_before = before
        if replace_existing_session:
            close_result = close_reused_managed_workbench(plan, before, log_handle)
            if close_result is not None and close_result.returncode == 0:
                effective_before = {**before, "alive": False}
        if close_result is not None and close_result.returncode != 0:
            action = "close"
            action_result = close_result
        else:
            if not effective_before.get("alive"):
                stale_profile_owners = workbench_profile_owner_pids(profile, session)
                stop_stale_workbench_profile_owners(stale_profile_owners, log_handle)
                profile_sanitized = sanitize_workbench_browser_profile(profile)
                if profile_sanitized:
                    log_handle.write(
                        "\n## sanitized browser profile "
                        + ", ".join(profile_sanitized)
                        + "\n"
                    )
                    log_handle.flush()
            action, action_result = open_or_reuse_managed_workbench(
                plan,
                effective_before,
                log_handle,
            )
        if action_result.returncode == 0:
            tab_cleanup_result = clean_workbench_tabs(
                plan["url"],
                session=session,
                log_handle=log_handle,
            )
        resize_result = apply_explicit_initial_viewport_resize(plan, action, log_handle)
        if viewport_size is None and action_result.returncode == 0:
            sync_state = sync_managed_workbench_viewport_to_display(
                session=session,
                plan=plan,
                action=action,
                previous_browser_state=previous_browser_state,
                log_handle=log_handle,
            )
            viewport_metrics = sync_state["viewport_metrics"]
            display_signature = sync_state["display_signature"]
            viewport_target = sync_state["viewport_target"]
            window_maximize_result = sync_state["window_maximize_result"]
            viewport_sync_result = sync_state["viewport_sync_result"]
        if action_result.returncode == 0:
            window_focus_result = bring_managed_workbench_to_front(plan, log_handle)
    if action_result.returncode != 0:
        raise SystemExit(
            f"Workbench browser {action} failed. See {relative_path(paths['browser_log'])}."
        )
    if resize_result is not None and resize_result.returncode != 0:
        raise SystemExit(
            f"Workbench browser resize failed. See {relative_path(paths['browser_log'])}."
        )
    if window_maximize_result is not None and window_maximize_result.returncode != 0:
        raise SystemExit(
            f"Workbench browser window maximize failed. See {relative_path(paths['browser_log'])}."
        )
    if viewport_sync_result is not None and viewport_sync_result.returncode != 0:
        raise SystemExit(
            f"Workbench browser viewport sync failed. See {relative_path(paths['browser_log'])}."
        )
    if window_focus_result is not None and window_focus_result.returncode != 0:
        raise SystemExit(
            f"Workbench browser focus failed. See {relative_path(paths['browser_log'])}."
        )
    after = browser_session_status(session)
    write_json_atomic(
        paths["browser_state"],
        {
            "session": session,
            "profile": plan["profile"],
            "status": after,
            "display_signature": display_signature,
            "viewport_target": viewport_target,
            "viewport_metrics": viewport_metrics,
            "updated_at_epoch": int(time.time()),
        },
    )
    return {
        "opened": True,
        "method": "repo-playwright-cli",
        "session": session,
        "reused": bool(before.get("alive")) and close_result is None,
        "replaced": close_result is not None,
        "resized": resize_result is not None,
        "window_maximized": window_maximize_result is not None,
        "window_focused": window_focus_result is not None,
        "viewport_synced": viewport_sync_result is not None,
        "viewport_metrics": viewport_metrics,
        "display_signature": display_signature,
        "viewport_target": viewport_target,
        "profile_sanitized": profile_sanitized,
        "stale_profile_owners_stopped": stale_profile_owners,
        "tab_cleanup": tab_cleanup_result,
        "status": after,
        "log": str(paths["browser_log"].relative_to(REPO_ROOT)),
        "channel": channel,
        "viewport_size": viewport_size,
        "profile": plan["profile"],
    }


def read_workbench_state(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))


def workbench_state_matches_manifest(state: dict[str, Any], manifest_path: Path) -> bool:
    context = state.get("context") if isinstance(state, dict) else {}
    if not isinstance(context, dict):
        return False
    try:
        expected_manifest = str(manifest_path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return False
    return (
        context.get("manifest") == expected_manifest
        and context.get("manifest_fingerprint") == manifest_state_fingerprint(manifest_path)
    )


def summarize_workbench_state(state: dict[str, Any]) -> dict[str, Any]:
    collection = state.get("collection", {}) if isinstance(state, dict) else {}
    artifacts = collection.get("artifacts", []) if isinstance(collection, dict) else []
    overlays = state.get("interaction_overlays", []) if isinstance(state, dict) else []
    types: dict[str, int] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("type") or artifact.get("mime_type") or "unknown")
        types[artifact_type] = types.get(artifact_type, 0) + 1
    return {
        "artifact_count": len(artifacts),
        "artifact_types": types,
        "interaction_overlay_count": len(overlays) if isinstance(overlays, list) else 0,
        "annotation_count": sum(
            1
            for overlay in overlays
            if isinstance(overlay, dict) and overlay.get("subtype") == "annotation"
        ) if isinstance(overlays, list) else 0,
        "updated_at_epoch": state.get("updated_at_epoch"),
    }


def summarize_workbench_glance(state: dict[str, Any]) -> dict[str, Any]:
    collection = state.get("collection", {}) if isinstance(state, dict) else {}
    artifacts = collection.get("artifacts", []) if isinstance(collection, dict) else []
    artifact_by_id = {
        str(artifact.get("id")): artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("id")
    }
    view = state.get("view", {}) if isinstance(state, dict) else {}
    active_artifact_id = str(view.get("active_artifact_id") or "") if isinstance(view, dict) else ""
    overlays = state.get("interaction_overlays", []) if isinstance(state, dict) else []
    annotation_artifact_ids = []
    if isinstance(overlays, list):
        for overlay in overlays:
            if not isinstance(overlay, dict) or overlay.get("subtype") != "annotation":
                continue
            subject = overlay.get("subject") if isinstance(overlay.get("subject"), dict) else {}
            artifact_id = str(subject.get("id") or "")
            if artifact_id:
                annotation_artifact_ids.append(artifact_id)
    if not active_artifact_id and annotation_artifact_ids:
        active_artifact_id = annotation_artifact_ids[-1]
    current_artifact = artifact_by_id.get(active_artifact_id)
    if current_artifact is None and artifacts:
        current_artifact = artifacts[0]
        active_artifact_id = str(current_artifact.get("id") or "")
    contexts = state.get("contexts", []) if isinstance(state, dict) else []
    active_context = next(
        (
            context
            for context in contexts
            if isinstance(context, dict) and context.get("active")
        ),
        None,
    )
    context = state.get("context", {}) if isinstance(state, dict) else {}
    annotations = []
    if isinstance(overlays, list):
        for overlay in overlays:
            if not isinstance(overlay, dict) or overlay.get("subtype") != "annotation":
                continue
            subject = overlay.get("subject") if isinstance(overlay.get("subject"), dict) else {}
            artifact_id = str(subject.get("id") or "")
            artifact = artifact_by_id.get(artifact_id, {})
            body = overlay.get("body") if isinstance(overlay.get("body"), dict) else {}
            annotations.append(
                {
                    "id": overlay.get("id"),
                    "artifact_id": artifact_id,
                    "artifact_name": artifact.get("name"),
                    "text": body.get("text"),
                    "anchor": overlay.get("anchor"),
                    "created_at_epoch": overlay.get("created_at_epoch"),
                }
            )
    return {
        "status": "workbench_glance",
        "current": {
            "manifest": context.get("manifest") if isinstance(context, dict) else collection.get("manifest"),
            "label": active_context.get("label") if isinstance(active_context, dict) else None,
            "subtitle": active_context.get("subtitle") if isinstance(active_context, dict) else None,
            "changed_by": context.get("changed_by") if isinstance(context, dict) else None,
            "changed_at_epoch": context.get("changed_at_epoch") if isinstance(context, dict) else None,
        },
        "current_artifact": (
            {
                "id": current_artifact.get("id"),
                "name": current_artifact.get("name"),
                "type": current_artifact.get("type"),
                "kind": current_artifact.get("kind"),
                "path": current_artifact.get("path"),
                "active_index": (
                    view.get("active_index")
                    if isinstance(view, dict) and view.get("active_index") is not None
                    else artifacts.index(current_artifact)
                ),
            }
            if isinstance(current_artifact, dict)
            else None
        ),
        "model": summarize_workbench_state(state),
        "annotations": annotations,
        "updated_at_epoch": state.get("updated_at_epoch") if isinstance(state, dict) else None,
    }


def command_start(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    paths = paths_for(manifest_path)
    url = f"http://{args.host}:{args.port}/"
    pid = read_pid(paths["pid"])

    if pid is not None and pid_alive(pid):
        if not is_owned_workbench_server(pid, manifest_path):
            raise SystemExit(f"Refusing to manage non-workbench-server PID {pid}")
        healthy, status = health(url)
        if not healthy:
            raise SystemExit(f"Recorded workbench server PID {pid} is alive but unhealthy: {status}")
        asset_health = workbench_asset_health(url)
        if not asset_health["healthy"]:
            stop_status = stop_owned_pid(pid, paths)
            wait_for_port_release(args.host, args.port)
            if not command_quiet(args):
                print(
                    "Restarting artifact viewer because workbench assets are stale: "
                    f"{asset_health['status']} ({stop_status} PID {pid})"
                )
            pid = None
        else:
            if args.open:
                open_with_playwright(
                    url,
                    paths,
                    args.channel,
                    args.viewport_size,
                    session=args.browser_session,
                    profile=args.profile,
                    replace_existing_session=True,
                )
            if not command_quiet(args):
                print(f"Artifact viewer already running: {url}")
                print(f"pid={pid}")
                print(f"health={status}")
                print(f"asset_health={asset_health['status']}")
                print(f"workbench_state={url}{WORKBENCH_STATE_PATH.removeprefix('/')}")
                print(f"workbench_projection={url}api/workbench-projection")
            return 0

    if pid is not None:
        remove_stale_state(paths)

    if port_accepts_connection(args.host, args.port):
        port_pid = listening_pid(args.host, args.port)
        if port_pid is None or not is_repo_workbench_server(port_pid):
            raise SystemExit(
                f"Port {args.host}:{args.port} is already in use and is not a repo workbench server. "
                "Stop the unrelated listener or choose another port."
            )
        active_manifest = active_workbench_server_manifest(port_pid)
        if active_manifest == manifest_path.resolve():
            paths["pid"].write_text(f"{port_pid}\n", encoding="utf-8")
            return command_start(args)
        stop_paths = paths_for(active_manifest) if active_manifest else paths
        stop_status = stop_owned_pid(port_pid, stop_paths)
        wait_for_port_release(args.host, args.port)
        if not command_quiet(args):
            previous = active_manifest.relative_to(REPO_ROOT) if active_manifest else "unknown"
            print(
                "Commandeering repo workbench server from "
                f"{previous} ({stop_status} PID {port_pid})"
            )

    paths["artifact_root"].mkdir(parents=True, exist_ok=True)
    log_handle = paths["log"].open("a", encoding="utf-8")
    log_handle.write(f"\n## start {int(time.time())}\n")
    log_handle.flush()
    process = subprocess.Popen(
        [
            sys.executable,
            str(SERVER_SCRIPT),
            str(manifest_path),
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )
    log_handle.close()
    paths["pid"].write_text(f"{process.pid}\n", encoding="utf-8")
    write_json_atomic(
        paths["state"],
        {
            "pid": process.pid,
            "url": url,
            "host": args.host,
            "port": args.port,
            "manifest": str(manifest_path.relative_to(REPO_ROOT)),
            "log": str(paths["log"].relative_to(REPO_ROOT)),
            "workbench_state_url": f"{url}{WORKBENCH_STATE_PATH.removeprefix('/')}",
            "workbench_projection_url": f"{url}api/workbench-projection",
            "started_at_epoch": int(time.time()),
        },
    )

    healthy, status = wait_for_health(url, args.timeout)
    if not healthy:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
        remove_stale_state(paths)
        print(f"Artifact viewer failed health check: {status}", file=sys.stderr)
        print(f"pid={process.pid}", file=sys.stderr)
        print(f"log={paths['log']}", file=sys.stderr)
        return 1

    if args.open:
        open_with_playwright(
            url,
            paths,
            args.channel,
            args.viewport_size,
            session=args.browser_session,
            profile=args.profile,
            replace_existing_session=True,
        )
    if not command_quiet(args):
        print(f"Artifact viewer running: {url}")
        print(f"pid={process.pid}")
        print(f"health={status}")
        print(f"log={paths['log']}")
        print(f"workbench_state={url}{WORKBENCH_STATE_PATH.removeprefix('/')}")
        print(f"workbench_projection={url}api/workbench-projection")
    return 0


def status_payload(args: argparse.Namespace, manifest_path: Path) -> dict[str, Any]:
    paths = paths_for(manifest_path)
    state = read_json(paths["state"], {}) or {}
    pid = read_pid(paths["pid"])
    host = state.get("host", getattr(args, "host", DEFAULT_HOST))
    port = int(state.get("port", getattr(args, "port", DEFAULT_PORT)))
    url = state.get("url", f"http://{host}:{port}/")
    port_pid = listening_pid(host, port) if pid is None and port_accepts_connection(host, port) else None
    effective_pid = pid if pid is not None else port_pid
    active_manifest = active_workbench_server_manifest(effective_pid) if effective_pid else None
    alive = bool(pid is not None and pid_alive(pid))
    repo_owned = bool(effective_pid is not None and pid_alive(effective_pid) and is_repo_workbench_server(effective_pid))
    owned = bool(effective_pid is not None and repo_owned and active_manifest == manifest_path.resolve())
    port_alive = bool(effective_pid is not None and pid_alive(effective_pid))
    healthy, health_status = health(url) if port_alive or port_accepts_connection(host, port) else (False, "not_listening")
    asset_health = (
        workbench_asset_health(url)
        if repo_owned and healthy
        else {"healthy": False, "status": "not_checked"}
    )
    return {
        "url": url,
        "pid": effective_pid,
        "alive": port_alive,
        "owned": owned,
        "repo_owned": repo_owned,
        "commandeerable": bool(repo_owned and not owned),
        "active_manifest": str(active_manifest.relative_to(REPO_ROOT)) if active_manifest else None,
        "health": health_status if healthy else f"unhealthy:{health_status}",
        "asset_health": asset_health,
        "asset_manifest_url": f"{url.rstrip('/')}{WORKBENCH_ASSET_MANIFEST_PATH}",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "log": str(paths["log"].relative_to(REPO_ROOT)),
        "workbench_state_url": f"{url.rstrip('/')}{WORKBENCH_STATE_PATH}",
        "workbench_projection_url": f"{url.rstrip('/')}/api/workbench-projection",
        "browser_session": browser_session_status(DEFAULT_BROWSER_SESSION),
    }


def command_status(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    payload = status_payload(args, manifest_path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_stop(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    paths = paths_for(manifest_path)
    pid = read_pid(paths["pid"])
    if pid is None:
        remove_stale_state(paths)
        print("Artifact viewer is not running")
        return 0
    if not pid_alive(pid):
        remove_stale_state(paths)
        print(f"Removed stale artifact viewer PID {pid}")
        return 0
    if not is_owned_workbench_server(pid, manifest_path):
        raise SystemExit(f"Refusing to stop non-workbench-server PID {pid}")

    stop_status = stop_owned_pid(pid, paths)
    if stop_status == "stopped":
        print(f"Stopped artifact viewer PID {pid}")
    else:
        print(f"Killed unresponsive artifact viewer PID {pid}")
    return 0


def command_open(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    paths = paths_for(manifest_path)
    state = read_json(paths["state"], {}) or {}
    url = state.get("url", f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/")
    healthy, status = health(url)
    if not healthy:
        raise SystemExit(f"Artifact viewer is not healthy at {url}: {status}")
    browser = open_with_playwright(
        url,
        paths,
        args.channel,
        args.viewport_size,
        session=args.browser_session,
        profile=args.profile,
        replace_existing_session=True,
    )
    print(f"Opened {url} in session={browser['session']} method={browser['method']}")
    return 0


def command_state(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    payload = status_payload(args, manifest_path)
    if not payload["alive"] or not payload["repo_owned"]:
        raise SystemExit("Artifact workbench is not running under this repo")
    url = payload["workbench_state_url"]
    healthy, status = health(url)
    if not healthy:
        raise SystemExit(f"Workbench state is not healthy at {url}: {status}")
    with urllib.request.urlopen(url, timeout=2.0) as response:
        sys.stdout.write(response.read().decode("utf-8"))
    return 0


def command_glance(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    payload = status_payload(args, manifest_path)
    if not payload["alive"] or not payload["repo_owned"]:
        raise SystemExit("Artifact workbench is not running under this repo")
    url = payload["workbench_state_url"]
    healthy, status = health(url)
    if not healthy:
        raise SystemExit(f"Workbench state is not healthy at {url}: {status}")
    state = read_workbench_state(url)
    glance = summarize_workbench_glance(state)
    glance["url"] = payload["url"]
    glance["workbench_state_url"] = payload["workbench_state_url"]
    print(json.dumps(glance, indent=2, sort_keys=True))
    return 0


def restart_surface_server(
    args: argparse.Namespace,
    manifest_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    pid = payload.get("pid")
    if isinstance(pid, int) and payload.get("repo_owned"):
        active_manifest_value = payload.get("active_manifest") or payload.get("manifest")
        active_manifest = (
            safe_manifest_path(REPO_ROOT / active_manifest_value)
            if active_manifest_value
            else manifest_path
        )
        stop_owned_pid(pid, paths_for(active_manifest))
        wait_for_port_release(args.host, args.port)
    start_args = argparse.Namespace(
        manifest=manifest_path,
        host=args.host,
        port=args.port,
        open=False,
        timeout=args.timeout,
        quiet=True,
    )
    start_result = command_start(start_args)
    if start_result != 0:
        return payload, start_result
    next_payload = status_payload(args, manifest_path)
    if not next_payload["alive"] or not next_payload["owned"] or next_payload["health"] != "200":
        raise SystemExit("Artifact workbench failed to reach healthy managed state")
    if not next_payload.get("asset_health", {}).get("healthy"):
        raise SystemExit("Artifact workbench assets failed to reach healthy managed state")
    return next_payload, 0


def command_surface(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    paths = paths_for(manifest_path)
    payload = status_payload(args, manifest_path)
    if (
        not payload["alive"]
        or not payload["owned"]
        or payload["health"] != "200"
        or not payload.get("asset_health", {}).get("healthy")
    ):
        payload, start_result = restart_surface_server(args, manifest_path, payload)
        if start_result != 0:
            return start_result

    try:
        state = read_workbench_state(payload["workbench_state_url"])
    except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError):
        payload, start_result = restart_surface_server(args, manifest_path, payload)
        if start_result != 0:
            return start_result
        state = read_workbench_state(payload["workbench_state_url"])
    if not workbench_state_matches_manifest(state, manifest_path):
        payload, start_result = restart_surface_server(args, manifest_path, payload)
        if start_result != 0:
            return start_result
        state = read_workbench_state(payload["workbench_state_url"])
        if not workbench_state_matches_manifest(state, manifest_path):
            raise SystemExit("Artifact workbench state is stale after managed restart")
    result: dict[str, Any] = {
        "url": payload["url"],
        "workbench_state_url": payload["workbench_state_url"],
        "workbench_projection_url": payload["workbench_projection_url"],
        "server": {
            "pid": payload["pid"],
            "health": payload["health"],
            "asset_health": payload["asset_health"],
            "owned": payload["owned"],
            "repo_owned": payload["repo_owned"],
            "active_manifest": payload["active_manifest"],
            "log": payload["log"],
        },
        "manifest": payload["manifest"],
        "model": summarize_workbench_state(state),
    }

    if args.no_browser:
        result["browser"] = {"opened": False, "method": "none"}
    else:
        result["browser"] = open_with_playwright(
            payload["url"],
            paths,
            args.channel,
            args.viewport_size,
            session=args.browser_session,
            profile=args.profile,
            replace_existing_session=True,
        )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Artifact workbench: {result['url']}")
        print(f"workbench_state={result['workbench_state_url']}")
        print(f"workbench_projection={result['workbench_projection_url']}")
        print(f"server_pid={result['server']['pid']} health={result['server']['health']}")
        print(
            "model="
            + json.dumps(result["model"], sort_keys=True)
        )
        browser = result["browser"]
        if browser["opened"]:
            print(
                f"browser={browser['method']} session={browser['session']} "
                f"reused={str(browser['reused']).lower()} log={browser['log']} "
                f"channel={browser['channel']} profile={browser['profile']}"
            )
        else:
            print("browser=not_opened")
    return 0


def main() -> int:
    args = parse_args()
    commands = {
        "start": command_start,
        "status": command_status,
        "stop": command_stop,
        "open": command_open,
        "state": command_state,
        "glance": command_glance,
        "surface": command_surface,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
