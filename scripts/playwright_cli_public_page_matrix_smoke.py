#!/usr/bin/env python3
"""Exercise Playwright CLI capture across a small real public-page matrix."""

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

from image_normalization_bridge import normalize_image_artifact


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest"
DEFAULT_SESSION_PREFIX = "eba-public-matrix"
DEFAULT_TARGET = "main"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
TEXT_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "extract-visible-text.js"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"

DEFAULT_PAGES = [
    {
        "slug": "mozilla-careers",
        "url": "https://www.mozilla.org/en-US/careers/",
        "target": "main",
    },
    {
        "slug": "automattic-work-with-us",
        "url": "https://automattic.com/work-with-us/",
        "target": "main",
    },
    {
        "slug": "wikimedia-jobs",
        "url": "https://wikimediafoundation.org/about/jobs/",
        "target": "main",
    },
    {
        "slug": "thirty-seven-signals-jobs",
        "url": "https://37signals.com/jobs/",
        "target": "main",
    },
]


def parse_page(value: str) -> dict[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected --page slug=url")
    slug, url = value.split("=", 1)
    if not slug or not url:
        raise argparse.ArgumentTypeError("Expected --page slug=url")
    return {"slug": slug, "url": url}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test Playwright CLI browser artifacts across a small public-page matrix."
    )
    parser.add_argument(
        "--page",
        action="append",
        type=parse_page,
        help=(
            "Page entry as slug=url. "
            "Repeat to replace the built-in low-risk public-page matrix."
        ),
    )
    parser.add_argument(
        "--session-prefix",
        default=DEFAULT_SESSION_PREFIX,
        help="Prefix for named Playwright CLI sessions",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help="Global fallback selector before main/h1/body when a page entry has no target",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Deterministic artifact directory to replace on each run",
    )
    parser.add_argument("--width", type=int, default=1365, help="Browser width")
    parser.add_argument("--height", type=int, default=900, help="Browser height")
    parser.add_argument(
        "--normalization-policy",
        type=Path,
        help="Optional JSON policy for composition-time image normalization",
    )
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
    print(f"[public-page-matrix] {label}")
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

    if check and command_failed(completed):
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")

    return completed


def safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT not in resolved.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {resolved}")
    return resolved


def result_json(stdout: str) -> Any:
    marker = "### Result"
    if marker not in stdout:
        return None
    after_marker = stdout.split(marker, 1)[1]
    before_code = after_marker.split("### Ran Playwright code", 1)[0].strip()
    if not before_code:
        return None
    try:
        return json.loads(before_code)
    except json.JSONDecodeError:
        return None


def png_dimensions(path: Path) -> dict[str, int] | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return {"width": width, "height": height}


def unique_targets(*targets: str) -> list[str]:
    seen = set()
    result = []
    for target in targets:
        if not target or target in seen:
            continue
        seen.add(target)
        result.append(target)
    return result


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative_result_path(path_value: str) -> str:
    path = Path(path_value).resolve()
    if REPO_ROOT in path.parents:
        return str(path.relative_to(REPO_ROOT))
    return str(path)


def normalize_capture_artifact(
    manifest: dict[str, Any],
    key: str,
    path: Path,
    policy_path: Path | None,
) -> None:
    result = normalize_image_artifact(path, key, policy_path)
    output_path = relative_result_path(result["output_path"])
    manifest["artifacts"][key] = output_path
    normalized = {
        **result,
        "source_path": relative_result_path(result["source_path"]),
        "output_path": output_path,
    }
    manifest.setdefault("image_normalization", {})[key] = normalized


def run_page(
    *,
    page: dict[str, str],
    page_index: int,
    args: argparse.Namespace,
    output_dir: Path,
) -> dict[str, Any]:
    slug = page["slug"]
    page_dir = output_dir / slug
    page_dir.mkdir(parents=True, exist_ok=True)
    session = f"{args.session_prefix}-{page_index + 1}"
    log_path = page_dir / "playwright-cli-public-page-matrix.log"
    url_path = page_dir / "url.txt"
    manifest_path = page_dir / "manifest.json"
    snapshot_path = page_dir / "snapshot.txt"
    viewport_path = page_dir / "viewport.png"
    full_page_path = page_dir / "full-page.png"
    element_path = page_dir / "element.png"
    visible_text_path = page_dir / "visible-text.stdout.txt"
    settle_path = page_dir / "settle.stdout.txt"
    hide_path = page_dir / "hide-obscuring.stdout.txt"
    restore_path = page_dir / "restore-page.stdout.txt"
    page_target = page.get("target", args.target)
    target_candidates = unique_targets(page_target, args.target, "main", "h1", "body")

    manifest: dict[str, Any] = {
        "slug": slug,
        "url": page["url"],
        "session": session,
        "status": "failed",
        "width": args.width,
        "height": args.height,
        "target_candidates": target_candidates,
        "target_used": None,
        "hidden_count": None,
        "restored_count": None,
        "screenshot_dimensions": {},
        "artifacts": {
            "url": str(url_path.relative_to(REPO_ROOT)),
            "snapshot": str(snapshot_path.relative_to(REPO_ROOT)),
            "visible_text_stdout": str(visible_text_path.relative_to(REPO_ROOT)),
            "viewport": str(viewport_path.relative_to(REPO_ROOT)),
            "full_page": str(full_page_path.relative_to(REPO_ROOT)),
            "element": str(element_path.relative_to(REPO_ROOT)),
            "settle_stdout": str(settle_path.relative_to(REPO_ROOT)),
            "hide_stdout": str(hide_path.relative_to(REPO_ROOT)),
            "restore_stdout": str(restore_path.relative_to(REPO_ROOT)),
            "log": str(log_path.relative_to(REPO_ROOT)),
            "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        },
    }
    url_path.write_text(f"{page['url']}\n", encoding="utf-8")

    opened = False
    closed = False
    try:
        run_step(
            f"{slug}: open public page",
            command_for(session, "open", page["url"], "--no-persistent"),
            log_path,
        )
        opened = True
        run_step(
            f"{slug}: resize desktop viewport",
            command_for(session, "resize", args.width, args.height),
            log_path,
        )
        settle_result = run_step(
            f"{slug}: settle public page",
            command_for(session, "run-code", SETTLE_SNIPPET),
            log_path,
            stdout_path=settle_path,
        )
        manifest["settle_result"] = result_json(settle_result.stdout)
        hide_result = run_step(
            f"{slug}: hide obscuring elements",
            command_for(session, "run-code", HIDE_SNIPPET),
            log_path,
            stdout_path=hide_path,
        )
        hide_json = result_json(hide_result.stdout)
        if isinstance(hide_json, dict):
            manifest["hidden_count"] = hide_json.get("hidden")
        run_step(
            f"{slug}: write snapshot with boxes",
            command_for(session, "snapshot", snapshot_path),
            log_path,
        )
        run_step(
            f"{slug}: extract visible text",
            command_for(session, "run-code", TEXT_SNIPPET),
            log_path,
            stdout_path=visible_text_path,
        )
        run_step(
            f"{slug}: write viewport screenshot",
            command_for(session, "screenshot", viewport_path),
            log_path,
        )
        normalize_capture_artifact(manifest, "viewport", viewport_path, args.normalization_policy)
        run_step(
            f"{slug}: write full-page screenshot",
            command_for(session, "screenshot", full_page_path, "--full-page"),
            log_path,
        )
        normalize_capture_artifact(manifest, "full_page", full_page_path, args.normalization_policy)
        for target in target_candidates:
            candidate_result = run_step(
                f"{slug}: write element screenshot for {target}",
                command_for(session, "screenshot", element_path, "--target", target),
                log_path,
                check=False,
            )
            if not command_failed(candidate_result):
                manifest["target_used"] = target
                break
        if manifest["target_used"] is None:
            raise RuntimeError(f"{slug}: no element screenshot target worked")
        normalize_capture_artifact(manifest, "element", element_path, args.normalization_policy)
        restore_result = run_step(
            f"{slug}: restore page",
            command_for(session, "run-code", RESTORE_SNIPPET),
            log_path,
            stdout_path=restore_path,
        )
        restore_json = result_json(restore_result.stdout)
        if isinstance(restore_json, dict):
            manifest["restored_count"] = restore_json.get("restored")
        manifest["status"] = "passed"
    except RuntimeError as exc:
        manifest["error"] = str(exc)
        print(f"[public-page-matrix] {exc}", file=sys.stderr)
    finally:
        if opened and not closed:
            close_result = run_step(
                f"{slug}: close session",
                command_for(session, "close"),
                log_path,
                check=False,
            )
            if command_failed(close_result):
                manifest["close_error"] = f"close failed with exit code {close_result.returncode}"
            else:
                closed = True
        manifest["closed"] = closed
        normalized = manifest.get("image_normalization", {})
        manifest["screenshot_dimensions"] = {
            "viewport": normalized.get("viewport", {}).get("output_dimensions") or png_dimensions(viewport_path),
            "full_page": normalized.get("full_page", {}).get("output_dimensions") or png_dimensions(full_page_path),
            "element": normalized.get("element", {}).get("output_dimensions") or png_dimensions(element_path),
        }
        write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    args = parse_args()
    output_dir = safe_output_dir(args.output_dir)
    pages = args.page or DEFAULT_PAGES

    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not found on PATH")

    slug_pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    for page in pages:
        if not slug_pattern.match(page["slug"]):
            raise SystemExit(f"Invalid page slug: {page['slug']}")

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_manifests = [
        run_page(page=page, page_index=index, args=args, output_dir=output_dir)
        for index, page in enumerate(pages)
    ]
    aggregate_manifest = {
        "status": "passed" if all(page["status"] == "passed" for page in page_manifests) else "failed",
        "page_count": len(page_manifests),
        "passed_count": sum(1 for page in page_manifests if page["status"] == "passed"),
        "pages": page_manifests,
    }
    write_json(output_dir / "manifest.json", aggregate_manifest)

    print("\n[public-page-matrix] artifact paths")
    print(f"- {output_dir / 'manifest.json'} (exists)")
    for page in page_manifests:
        page_dir = output_dir / page["slug"]
        print(f"- {page_dir} ({page['status']})")

    return 0 if aggregate_manifest["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
