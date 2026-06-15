#!/usr/bin/env python3
"""Manage the local Playwright CLI artifact viewer server."""

import argparse
import json
import os
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from playwright_cli_workbench_server import (
        WORKBENCH_ASSET_MANIFEST_PATH,
        build_workbench_asset_manifest,
    )
except ModuleNotFoundError:
    from scripts.playwright_cli_workbench_server import (
        WORKBENCH_ASSET_MANIFEST_PATH,
        build_workbench_asset_manifest,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start, inspect, stop, open, or read a Playwright CLI artifact viewer."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("start", "status", "stop", "open", "state", "surface"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
        if command in {"start", "status", "state", "surface"}:
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


def is_owned_workbench_server(pid: int, manifest_path: Path) -> bool:
    command = process_command(pid)
    return (
        str(SERVER_SCRIPT) in command
        and str(manifest_path) in command
        and "playwright_cli_workbench_server.py" in command
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
    }


def port_accepts_connection(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


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
) -> dict[str, Any]:
    wrapper = relative_path(BROWSER_WRAPPER)
    profile_path = relative_path(profile)
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
        "browser": browser,
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
        ],
        "window_maximize_command": [
            sys.executable,
            wrapper,
            "window-maximize",
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


def open_with_playwright(
    url: str,
    paths: dict[str, Path],
    channel: str,
    viewport_size: str | None,
    *,
    session: str = DEFAULT_BROWSER_SESSION,
    profile: Path = DEFAULT_BROWSER_PROFILE,
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
    action_command = plan["goto_command"] if before.get("alive") else plan["open_command"]
    action = "goto" if before.get("alive") else "open"
    resize_result = None
    window_maximize_result = None
    viewport_sync_result = None
    viewport_metrics = None
    display_signature = None
    viewport_target = None
    with paths["browser_log"].open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"\n## {action} {int(time.time())} {url}\n")
        action_result = run_browser_command(action_command, log_handle)
        if action == "open" and plan["initial_resize_command"] is not None:
            resize_result = run_browser_command(plan["initial_resize_command"], log_handle)
        if viewport_size is None and action_result.returncode == 0:
            viewport_metrics = browser_page_metrics(session)
            display_signature = browser_display_signature(viewport_metrics)
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
        "reused": bool(before.get("alive")),
        "resized": resize_result is not None,
        "window_maximized": window_maximize_result is not None,
        "viewport_synced": viewport_sync_result is not None,
        "viewport_metrics": viewport_metrics,
        "display_signature": display_signature,
        "viewport_target": viewport_target,
        "status": after,
        "log": str(paths["browser_log"].relative_to(REPO_ROOT)),
        "channel": channel,
        "viewport_size": viewport_size,
        "profile": plan["profile"],
    }


def read_annotation_state(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))


def summarize_annotation_state(state: dict[str, Any]) -> dict[str, Any]:
    collection = state.get("collection", {}) if isinstance(state, dict) else {}
    artifacts = collection.get("artifacts", []) if isinstance(collection, dict) else []
    annotations = state.get("annotations", {}) if isinstance(state, dict) else {}
    types: dict[str, int] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("type") or artifact.get("mime_type") or "unknown")
        types[artifact_type] = types.get(artifact_type, 0) + 1
    return {
        "artifact_count": len(artifacts),
        "artifact_types": types,
        "annotation_count": sum(len(value) for value in annotations.values() if isinstance(value, list)),
        "updated_at_epoch": state.get("updated_at_epoch"),
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
                )
            if not command_quiet(args):
                print(f"Artifact viewer already running: {url}")
                print(f"pid={pid}")
                print(f"health={status}")
                print(f"asset_health={asset_health['status']}")
                print(f"annotation_state={url}api/annotation-state")
                print(f"workbench_projection={url}api/workbench-projection")
            return 0

    if pid is not None:
        remove_stale_state(paths)

    if port_accepts_connection(args.host, args.port):
        raise SystemExit(
            f"Port {args.host}:{args.port} is already in use and is not owned by this manager. "
            "Run status/stop for the owning gate or choose another port."
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
            "annotation_state_url": f"{url}api/annotation-state",
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
        )
    if not command_quiet(args):
        print(f"Artifact viewer running: {url}")
        print(f"pid={process.pid}")
        print(f"health={status}")
        print(f"log={paths['log']}")
        print(f"annotation_state={url}api/annotation-state")
        print(f"workbench_projection={url}api/workbench-projection")
    return 0


def status_payload(args: argparse.Namespace, manifest_path: Path) -> dict[str, Any]:
    paths = paths_for(manifest_path)
    state = read_json(paths["state"], {}) or {}
    pid = read_pid(paths["pid"])
    host = state.get("host", getattr(args, "host", DEFAULT_HOST))
    port = int(state.get("port", getattr(args, "port", DEFAULT_PORT)))
    url = state.get("url", f"http://{host}:{port}/")
    alive = bool(pid is not None and pid_alive(pid))
    owned = bool(pid is not None and alive and is_owned_workbench_server(pid, manifest_path))
    healthy, health_status = health(url) if alive or port_accepts_connection(host, port) else (False, "not_listening")
    asset_health = (
        workbench_asset_health(url)
        if owned and healthy
        else {"healthy": False, "status": "not_checked"}
    )
    return {
        "url": url,
        "pid": pid,
        "alive": alive,
        "owned": owned,
        "health": health_status if healthy else f"unhealthy:{health_status}",
        "asset_health": asset_health,
        "asset_manifest_url": f"{url.rstrip('/')}{WORKBENCH_ASSET_MANIFEST_PATH}",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "log": str(paths["log"].relative_to(REPO_ROOT)),
        "annotation_state_url": f"{url.rstrip('/')}/api/annotation-state",
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
    )
    print(f"Opened {url} in session={browser['session']} method={browser['method']}")
    return 0


def command_state(args: argparse.Namespace) -> int:
    manifest_path = safe_manifest_path(args.manifest)
    payload = status_payload(args, manifest_path)
    if not payload["alive"] or not payload["owned"]:
        raise SystemExit("Artifact viewer is not running under this manager")
    url = payload["annotation_state_url"]
    healthy, status = health(url)
    if not healthy:
        raise SystemExit(f"Annotation state is not healthy at {url}: {status}")
    with urllib.request.urlopen(url, timeout=2.0) as response:
        sys.stdout.write(response.read().decode("utf-8"))
    return 0


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
            return start_result
        payload = status_payload(args, manifest_path)
        if not payload["alive"] or not payload["owned"] or payload["health"] != "200":
            raise SystemExit("Artifact workbench failed to reach healthy managed state")
        if not payload.get("asset_health", {}).get("healthy"):
            raise SystemExit("Artifact workbench assets failed to reach healthy managed state")

    state = read_annotation_state(payload["annotation_state_url"])
    result: dict[str, Any] = {
        "url": payload["url"],
        "annotation_state_url": payload["annotation_state_url"],
        "workbench_projection_url": payload["workbench_projection_url"],
        "server": {
            "pid": payload["pid"],
            "health": payload["health"],
            "asset_health": payload["asset_health"],
            "owned": payload["owned"],
            "log": payload["log"],
        },
        "manifest": payload["manifest"],
        "model": summarize_annotation_state(state),
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
        )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Artifact workbench: {result['url']}")
        print(f"annotation_state={result['annotation_state_url']}")
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
        "surface": command_surface,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
