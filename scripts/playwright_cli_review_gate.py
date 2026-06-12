#!/usr/bin/env python3
"""Manage the local Playwright CLI artifact viewer server."""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)
SERVER_SCRIPT = REPO_ROOT / "scripts" / "playwright_cli_review_server.py"
PID_NAME = "review-server.pid"
LOG_NAME = "review-server.log"
STATE_NAME = "review-server-state.json"
BROWSER_PID_NAME = "review-browser.pid"
BROWSER_LOG_NAME = "review-browser.log"


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
        if command == "surface":
            subparser.add_argument(
                "--channel",
                default="chrome",
                help="Chromium channel for Playwright CLI open, usually chrome",
            )
            subparser.add_argument(
                "--viewport-size",
                default="1440,1000",
                help="Browser viewport size passed to Playwright CLI open",
            )
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
        "browser_pid": artifact_root / BROWSER_PID_NAME,
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


def is_owned_review_server(pid: int, manifest_path: Path) -> bool:
    command = process_command(pid)
    return (
        str(SERVER_SCRIPT) in command
        and str(manifest_path) in command
        and "playwright_cli_review_server.py" in command
    )


def remove_stale_state(paths: dict[str, Path]) -> None:
    for key in ("pid", "state"):
        paths[key].unlink(missing_ok=True)


def health(url: str, timeout: float = 1.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500, str(response.status)
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 500, str(exc.code)
    except OSError as exc:
        return False, exc.__class__.__name__


def port_accepts_connection(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


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


def playwright_wrapper_path() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return codex_home / "skills" / "playwright" / "scripts" / "playwright_cli.sh"


def require_playwright_wrapper() -> Path:
    wrapper = playwright_wrapper_path()
    if not wrapper.exists():
        raise SystemExit(
            f"Playwright wrapper not found: {wrapper}. "
            "Install/enable the local Playwright skill or run surface --no-browser."
        )
    completed = subprocess.run(
        [str(wrapper), "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "Playwright wrapper failed health check. "
            f"command={wrapper} --help\n{completed.stderr or completed.stdout}"
        )
    return wrapper


def open_with_playwright(url: str, paths: dict[str, Path], channel: str, viewport_size: str) -> dict[str, Any]:
    wrapper = require_playwright_wrapper()
    paths["artifact_root"].mkdir(parents=True, exist_ok=True)
    log_handle = paths["browser_log"].open("a", encoding="utf-8")
    log_handle.write(f"\n## open {int(time.time())} {url}\n")
    log_handle.flush()
    process = subprocess.Popen(
        [
            str(wrapper),
            "open",
            "--channel",
            channel,
            "--viewport-size",
            viewport_size,
            url,
        ],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )
    log_handle.close()
    paths["browser_pid"].write_text(f"{process.pid}\n", encoding="utf-8")
    return {
        "opened": True,
        "method": "playwright-cli",
        "pid": process.pid,
        "log": str(paths["browser_log"].relative_to(REPO_ROOT)),
        "channel": channel,
        "viewport_size": viewport_size,
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
        if not is_owned_review_server(pid, manifest_path):
            raise SystemExit(f"Refusing to manage non-review-server PID {pid}")
        healthy, status = health(url)
        if not healthy:
            raise SystemExit(f"Recorded review server PID {pid} is alive but unhealthy: {status}")
        if args.open:
            webbrowser.open(url, new=2)
        if not command_quiet(args):
            print(f"Artifact viewer already running: {url}")
            print(f"pid={pid}")
            print(f"health={status}")
            print(f"annotation_state={url}api/annotation-state")
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
        webbrowser.open(url, new=2)
    if not command_quiet(args):
        print(f"Artifact viewer running: {url}")
        print(f"pid={process.pid}")
        print(f"health={status}")
        print(f"log={paths['log']}")
        print(f"annotation_state={url}api/annotation-state")
    return 0


def status_payload(args: argparse.Namespace, manifest_path: Path) -> dict[str, Any]:
    paths = paths_for(manifest_path)
    state = read_json(paths["state"], {}) or {}
    pid = read_pid(paths["pid"])
    host = state.get("host", getattr(args, "host", DEFAULT_HOST))
    port = int(state.get("port", getattr(args, "port", DEFAULT_PORT)))
    url = state.get("url", f"http://{host}:{port}/")
    alive = bool(pid is not None and pid_alive(pid))
    owned = bool(pid is not None and alive and is_owned_review_server(pid, manifest_path))
    healthy, health_status = health(url) if alive or port_accepts_connection(host, port) else (False, "not_listening")
    return {
        "url": url,
        "pid": pid,
        "alive": alive,
        "owned": owned,
        "health": health_status if healthy else f"unhealthy:{health_status}",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "log": str(paths["log"].relative_to(REPO_ROOT)),
        "annotation_state_url": f"{url.rstrip('/')}/api/annotation-state",
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
    if not is_owned_review_server(pid, manifest_path):
        raise SystemExit(f"Refusing to stop non-review-server PID {pid}")

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if not pid_alive(pid):
            remove_stale_state(paths)
            print(f"Stopped artifact viewer PID {pid}")
            return 0
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    remove_stale_state(paths)
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
    webbrowser.open(url, new=2)
    print(f"Opened {url}")
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
    if not payload["alive"] or not payload["owned"] or payload["health"] != "200":
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

    state = read_annotation_state(payload["annotation_state_url"])
    result: dict[str, Any] = {
        "url": payload["url"],
        "annotation_state_url": payload["annotation_state_url"],
        "server": {
            "pid": payload["pid"],
            "health": payload["health"],
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
        )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Artifact workbench: {result['url']}")
        print(f"annotation_state={result['annotation_state_url']}")
        print(f"server_pid={result['server']['pid']} health={result['server']['health']}")
        print(
            "model="
            + json.dumps(result["model"], sort_keys=True)
        )
        browser = result["browser"]
        if browser["opened"]:
            print(
                f"browser=playwright-cli pid={browser['pid']} "
                f"log={browser['log']} channel={browser['channel']}"
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
