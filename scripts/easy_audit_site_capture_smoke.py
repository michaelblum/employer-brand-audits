#!/usr/bin/env python3
"""Capture the deterministic easy-audit careers site through Playwright CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from easy_audit_fixture import DEFAULT_OUTPUT_DIR, generate_easy_audit_fixture


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION = "eba-easy-audit-site"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"
LIVE_CAPTURE_REVIEW_ARTIFACTS = {
    "roles_internal_scroll": {
        "id": "l1-roles-internal-scroll",
        "summary": "Roles modal internal scroll capture",
        "url": "https://acme.example/roles",
    },
    "culture_shadow_proof": {
        "id": "l1-culture-shadow-proof",
        "summary": "Culture shadow DOM proof capture",
        "url": "https://acme.example/culture",
    },
    "animation_progress": {
        "id": "l1-animation-progress",
        "summary": "Animation settle progress capture",
        "url": "https://acme.example/careers",
    },
    "sticky_obscured_target": {
        "id": "l1-sticky-obscured-target",
        "summary": "Sticky header overlap diagnostic capture",
        "url": "https://acme.example/roles",
    },
}


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default=DEFAULT_SESSION, help="Named Playwright CLI session")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Easy-audit artifact directory to replace and then capture into.",
    )
    parser.add_argument("--width", type=int, default=1365, help="Browser width")
    parser.add_argument("--height", type=int, default=900, help="Browser height")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    return parser.parse_args()


def command_for(session: str, *args: str | int | Path) -> list[str]:
    return [sys.executable, str(WRAPPER), *[str(arg) for arg in args], "--session", session]


def command_failed(completed: subprocess.CompletedProcess[str]) -> bool:
    return (
        completed.returncode != 0
        or "### Error" in completed.stdout
        or "### Error" in completed.stderr
    )


def run_step(
    label: str,
    cmd: list[str],
    log_path: Path,
    stdout_path: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
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
    if stdout_path:
        stdout_path.write_text(completed.stdout, encoding="utf-8")
    if check and command_failed(completed):
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    return completed


def result_after_marker(stdout: str) -> str | None:
    marker = "### Result"
    if marker not in stdout:
        return None
    after_marker = stdout.split(marker, 1)[1]
    return after_marker.split("### Ran Playwright code", 1)[0].strip() or None


def start_site_server(site_dir: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(QuietHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/"


def write_extra_capture_snippet(
    path: Path,
    *,
    roles_path: Path,
    culture_path: Path,
    progress_path: Path,
    sticky_path: Path,
) -> None:
    path.write_text(
        f"""async (page) => {{
  const outputs = {{
    rolesInternalScroll: {str(roles_path.relative_to(REPO_ROOT)).__repr__()},
    cultureShadowProof: {str(culture_path.relative_to(REPO_ROOT)).__repr__()},
    progressTarget: {str(progress_path.relative_to(REPO_ROOT)).__repr__()},
    stickyObscuredTarget: {str(sticky_path.relative_to(REPO_ROOT)).__repr__()},
  }};

  const baseUrl = page.url().replace(/\\/[^/]*$/, '/');
  await page.locator('#animation-progress').scrollIntoViewIfNeeded();
  await page.locator('#animation-progress').screenshot({{ path: outputs.progressTarget }});

  await page.goto(baseUrl + 'roles.html');
  await page.locator('#internal-scroll').scrollIntoViewIfNeeded();
  const scroller = page.locator('#internal-scroll');
  const previousStyle = await scroller.evaluate((el) => {{
    const previous = {{ height: el.style.height || '', overflow: el.style.overflow || '' }};
    el.style.height = `${{el.scrollHeight}}px`;
    el.style.overflow = 'visible';
    return previous;
  }});
  await scroller.screenshot({{ path: outputs.rolesInternalScroll }});
  await scroller.evaluate((el, previous) => {{
    el.style.height = previous.height;
    el.style.overflow = previous.overflow;
  }}, previousStyle);
  await page.evaluate(() => {{
    document.querySelector('#sticky-obscured-target')?.scrollIntoView({{ block: 'start', inline: 'nearest' }});
  }});
  await page.locator('#sticky-obscured-target').screenshot({{ path: outputs.stickyObscuredTarget }});

  await page.goto(baseUrl + 'culture.html');
  await page.locator('employee-proof').scrollIntoViewIfNeeded();
  await page.locator('employee-proof').screenshot({{ path: outputs.cultureShadowProof }});
  return outputs;
}}
""",
        encoding="utf-8",
    )


def read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected manifest object: {path}")
    return payload


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def attach_live_capture_artifacts(manifest: dict[str, Any], artifacts: dict[str, str]) -> None:
    artifact_list = manifest.setdefault("artifacts", [])
    if not isinstance(artifact_list, list):
        return
    existing_ids = {
        str(artifact.get("id"))
        for artifact in artifact_list
        if isinstance(artifact, dict) and artifact.get("id")
    }
    l1_step = next(
        (
            step
            for step in manifest.get("steps", [])
            if isinstance(step, dict) and step.get("id") == "l1-source-capture"
        ),
        None,
    )
    if l1_step is not None:
        l1_step.setdefault("artifact_ids", [])

    for key, meta in LIVE_CAPTURE_REVIEW_ARTIFACTS.items():
        path_value = artifacts.get(key)
        artifact_id = meta["id"]
        if not path_value or artifact_id in existing_ids:
            continue
        artifact_path = Path(path_value)
        if not artifact_path.is_absolute():
            artifact_path = REPO_ROOT / artifact_path
        if not artifact_path.exists():
            continue
        artifact_list.append(
            {
                "id": artifact_id,
                "layer": 1,
                "type": "screenshot",
                "status": "complete",
                "created_at": "2026-06-13T01:03:30Z",
                "produced_by_step_id": "l1-source-capture",
                "parent_ids": ["l1-careers-screenshot"],
                "file_path": path_value,
                "params": {"url": meta["url"]},
                "card": {"summary": meta["summary"], "tags": {"layer": "L1", "capture": key}},
            }
        )
        existing_ids.add(artifact_id)
        if l1_step is not None and isinstance(l1_step.get("artifact_ids"), list):
            l1_step["artifact_ids"].append(artifact_id)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir == REPO_ROOT or REPO_ROOT not in output_dir.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {output_dir}")
    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not found on PATH")

    manifest_path = generate_easy_audit_fixture(output_dir)
    site_dir = manifest_path.parent / "site"
    server, base_url = start_site_server(site_dir)
    log_path = output_dir / "easy-audit-site-capture.log"
    snapshot_path = output_dir / "l1-careers-snapshot.txt"
    text_stdout_path = output_dir / "l1-careers-text.stdout.txt"
    screenshot_path = output_dir / "l1-careers-screenshot.png"
    roles_internal_scroll_path = output_dir / "l1-roles-internal-scroll.png"
    culture_shadow_path = output_dir / "l1-culture-shadow-proof.png"
    progress_path = output_dir / "l1-animation-progress.png"
    sticky_path = output_dir / "l1-sticky-obscured-target.png"
    settle_stdout_path = output_dir / "l1-settle.stdout.txt"
    hide_stdout_path = output_dir / "l1-hide-obscuring.stdout.txt"
    restore_stdout_path = output_dir / "l1-restore-page.stdout.txt"
    extra_capture_stdout_path = output_dir / "l1-extra-capture.stdout.txt"
    extra_capture_snippet = output_dir / "easy-audit-extra-capture.generated.js"
    write_extra_capture_snippet(
        extra_capture_snippet,
        roles_path=roles_internal_scroll_path,
        culture_path=culture_shadow_path,
        progress_path=progress_path,
        sticky_path=sticky_path,
    )

    opened = False
    failed = False
    try:
        run_step("open mock careers site", command_for(args.session, "open", base_url, "--no-persistent"), log_path)
        opened = True
        run_step("resize browser", command_for(args.session, "resize", args.width, args.height), log_path)
        run_step("settle careers page", command_for(args.session, "run-code", SETTLE_SNIPPET), log_path, settle_stdout_path)
        run_step("hide overlays", command_for(args.session, "run-code", HIDE_SNIPPET), log_path, hide_stdout_path)
        text_result = run_step(
            "extract visible text",
            command_for(args.session, "run-code", TEXT_SNIPPET),
            log_path,
            text_stdout_path,
        )
        visible_text = result_after_marker(text_result.stdout)
        if visible_text:
            (output_dir / "l1-careers-text.txt").write_text(visible_text + "\n", encoding="utf-8")
        run_step("write snapshot", command_for(args.session, "snapshot", snapshot_path), log_path)
        run_step("write full-page careers screenshot", command_for(args.session, "screenshot", screenshot_path, "--full-page"), log_path)
        run_step(
            "capture internal-scroll and shadow-dom artifacts",
            command_for(args.session, "run-code", extra_capture_snippet),
            log_path,
            extra_capture_stdout_path,
        )
        run_step("restore overlays", command_for(args.session, "run-code", RESTORE_SNIPPET), log_path, restore_stdout_path)
    except RuntimeError as exc:
        failed = True
        print(f"[easy-audit-site-capture] {exc}", file=sys.stderr)
    finally:
        if opened:
            close_result = run_step("close session", command_for(args.session, "close"), log_path, check=False)
            failed = failed or command_failed(close_result)
        server.shutdown()
        server.server_close()

    manifest = read_manifest(manifest_path)
    manifest["mock_site"]["base_url"] = base_url
    manifest["live_capture"] = {
        "status": "failed" if failed else "passed",
        "log": str(log_path.relative_to(REPO_ROOT)),
        "snapshot": str(snapshot_path.relative_to(REPO_ROOT)),
        "visible_text_stdout": str(text_stdout_path.relative_to(REPO_ROOT)),
        "settle_stdout": str(settle_stdout_path.relative_to(REPO_ROOT)),
        "hide_stdout": str(hide_stdout_path.relative_to(REPO_ROOT)),
        "restore_stdout": str(restore_stdout_path.relative_to(REPO_ROOT)),
        "extra_capture_stdout": str(extra_capture_stdout_path.relative_to(REPO_ROOT)),
        "extra_capture_snippet": str(extra_capture_snippet.relative_to(REPO_ROOT)),
        "artifacts": {
            "careers_full_page": str(screenshot_path.relative_to(REPO_ROOT)),
            "roles_internal_scroll": str(roles_internal_scroll_path.relative_to(REPO_ROOT)),
            "culture_shadow_proof": str(culture_shadow_path.relative_to(REPO_ROOT)),
            "animation_progress": str(progress_path.relative_to(REPO_ROOT)),
            "sticky_obscured_target": str(sticky_path.relative_to(REPO_ROOT)),
        },
    }
    attach_live_capture_artifacts(manifest, manifest["live_capture"]["artifacts"])
    write_manifest(manifest_path, manifest)

    payload = {
        "status": "failed" if failed else "passed",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "base_url": base_url,
        "artifacts": manifest["live_capture"]["artifacts"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
