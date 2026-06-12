#!/usr/bin/env python3
"""Exercise advanced Playwright CLI capture modes against a local fixture."""

import argparse
import json
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from image_normalization_bridge import normalize_image_artifact


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "playwright-cli-capture-modes" / "latest"
DEFAULT_SESSION = "eba-capture-modes"
FIXTURE = REPO_ROOT / "scripts" / "playwright-fixtures" / "capture-modes.html"
WRAPPER = REPO_ROOT / "scripts" / "playwright_cli_browser.py"
SETTLE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "settle-page.js"
HIDE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "hide-obscuring-elements.js"
RESTORE_SNIPPET = REPO_ROOT / "scripts" / "playwright-snippets" / "restore-page.js"
FIXTURE_DIR = FIXTURE.parent


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test advanced Playwright CLI capture modes using a deterministic local fixture."
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
    parser.add_argument(
        "--normalization-policy",
        type=Path,
        help="Optional JSON policy for composition-time image normalization",
    )
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
    print(f"[capture-smoke] {label}")
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


def normalize_outputs(paths: dict[str, Path], policy_path: Path | None) -> dict[str, dict]:
    normalized = {}
    for subtype, path in paths.items():
        normalized[subtype] = normalize_image_artifact(path, subtype, policy_path)
    return normalized


def start_fixture_server() -> tuple[ThreadingHTTPServer, str]:
    handler = partial(QuietHTTPRequestHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/{FIXTURE.name}"


def write_mode_snippet(
    path: Path,
    *,
    frame_path: Path,
    trim_path: Path,
    context_path: Path,
    internal_scroll_path: Path,
) -> None:
    path.write_text(
        f"""async (page) => {{
  const outputs = {{
    frame: {str(frame_path.relative_to(REPO_ROOT)).__repr__()},
    trim: {str(trim_path.relative_to(REPO_ROOT)).__repr__()},
    context: {str(context_path.relative_to(REPO_ROOT)).__repr__()},
    internalScroll: {str(internal_scroll_path.relative_to(REPO_ROOT)).__repr__()},
  }};

  const frameTarget = page.locator("#frame-target");
  await frameTarget.scrollIntoViewIfNeeded();
  await frameTarget.evaluate((el) => {{
    el.dataset.previousPadding = el.style.padding || "";
    el.style.padding = "22px 28px";
  }});
  await frameTarget.screenshot({{ path: outputs.frame }});
  await frameTarget.evaluate((el) => {{
    el.style.padding = el.dataset.previousPadding || "";
    delete el.dataset.previousPadding;
  }});

  const trimTarget = page.locator("#trim-target");
  await trimTarget.scrollIntoViewIfNeeded();
  const trimBox = await trimTarget.boundingBox();
  if (!trimBox) {{
    throw new Error("Missing #trim-target bounding box");
  }}
  await page.screenshot({{
    path: outputs.trim,
    clip: {{
      x: trimBox.x + 18,
      y: trimBox.y + 18,
      width: trimBox.width - 36,
      height: trimBox.height - 36,
    }},
  }});

  const contextTarget = page.locator("#context-target");
  await contextTarget.scrollIntoViewIfNeeded();
  const contextBox = await contextTarget.boundingBox();
  if (!contextBox) {{
    throw new Error("Missing #context-target bounding box");
  }}
  const margin = 42;
  await page.screenshot({{
    path: outputs.context,
    clip: {{
      x: Math.max(0, contextBox.x - margin),
      y: Math.max(0, contextBox.y - margin),
      width: contextBox.width + margin * 2,
      height: contextBox.height + margin * 2,
    }},
  }});

  const scroller = page.locator("#internal-scroll");
  await scroller.scrollIntoViewIfNeeded();
  const previousStyle = await scroller.evaluate((el) => {{
    const previous = {{
      height: el.style.height || "",
      overflow: el.style.overflow || "",
    }};
    el.style.height = `${{el.scrollHeight}}px`;
    el.style.overflow = "visible";
    return previous;
  }});
  await scroller.screenshot({{ path: outputs.internalScroll }});
  await scroller.evaluate((el, previous) => {{
    el.style.height = previous.height;
    el.style.overflow = previous.overflow;
  }}, previousStyle);

  return outputs;
}}
""",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    if output_dir == REPO_ROOT or REPO_ROOT not in output_dir.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {output_dir}")

    if shutil.which("playwright-cli") is None:
        raise SystemExit("playwright-cli not found on PATH")

    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    fixture_server, fixture_url = start_fixture_server()
    log_path = output_dir / "playwright-cli-capture-modes-smoke.log"
    snapshot_path = output_dir / "fixture.snapshot.txt"
    settled_viewport_path = output_dir / "fixture.settled-viewport.png"
    hide_viewport_path = output_dir / "fixture.overlay-hidden-viewport.png"
    full_page_path = output_dir / "fixture.full-page.png"
    frame_path = output_dir / "fixture.own-background-frame.png"
    trim_path = output_dir / "fixture.trim.png"
    context_path = output_dir / "fixture.context-margin.png"
    internal_scroll_path = output_dir / "fixture.internal-scroll-expanded.png"
    settle_stdout_path = output_dir / "fixture.settle.stdout.txt"
    hide_stdout_path = output_dir / "fixture.hide-obscuring.stdout.txt"
    restore_stdout_path = output_dir / "fixture.restore-page.stdout.txt"
    capture_modes_stdout_path = output_dir / "fixture.capture-modes.stdout.txt"
    capture_modes_snippet = output_dir / "capture-modes.generated.js"
    normalization_path = output_dir / "fixture.image-normalization.json"

    write_mode_snippet(
        capture_modes_snippet,
        frame_path=frame_path,
        trim_path=trim_path,
        context_path=context_path,
        internal_scroll_path=internal_scroll_path,
    )

    failed = False
    opened = False
    closed = False
    try:
        run_step(
            "open local capture fixture",
            command_for(args.session, "open", fixture_url, "--no-persistent"),
            log_path,
        )
        opened = True
        run_step(
            "resize browser",
            command_for(args.session, "resize", args.width, args.height),
            log_path,
        )
        run_step(
            "settle fixture",
            command_for(args.session, "run-code", SETTLE_SNIPPET),
            log_path,
            stdout_path=settle_stdout_path,
        )
        run_step(
            "write settled viewport screenshot",
            command_for(args.session, "screenshot", settled_viewport_path),
            log_path,
        )
        run_step(
            "hide fixture overlays",
            command_for(args.session, "run-code", HIDE_SNIPPET),
            log_path,
            stdout_path=hide_stdout_path,
        )
        run_step(
            "write overlay-hidden viewport screenshot",
            command_for(args.session, "screenshot", hide_viewport_path),
            log_path,
        )
        run_step(
            "write snapshot with boxes",
            command_for(args.session, "snapshot", snapshot_path),
            log_path,
        )
        run_step(
            "write full-page screenshot",
            command_for(args.session, "screenshot", full_page_path, "--full-page"),
            log_path,
        )
        run_step(
            "write custom capture mode screenshots",
            command_for(args.session, "run-code", capture_modes_snippet),
            log_path,
            stdout_path=capture_modes_stdout_path,
        )
        normalization = normalize_outputs(
            {
                "viewport": settled_viewport_path,
                "viewport_overlay_hidden": hide_viewport_path,
                "full_page": full_page_path,
                "frame": frame_path,
                "trim": trim_path,
                "context": context_path,
                "internal_scroll": internal_scroll_path,
            },
            args.normalization_policy,
        )
        normalization_path.write_text(
            json.dumps(normalization, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        run_step(
            "restore fixture overlays",
            command_for(args.session, "run-code", RESTORE_SNIPPET),
            log_path,
            stdout_path=restore_stdout_path,
        )
    except RuntimeError as exc:
        failed = True
        print(f"[capture-smoke] {exc}", file=sys.stderr)
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
        fixture_server.shutdown()
        fixture_server.server_close()

    print("\n[capture-smoke] artifact paths")
    for path in [
        snapshot_path,
        settled_viewport_path,
        hide_viewport_path,
        full_page_path,
        frame_path,
        trim_path,
        context_path,
        internal_scroll_path,
        settle_stdout_path,
        hide_stdout_path,
        restore_stdout_path,
        capture_modes_stdout_path,
        capture_modes_snippet,
        normalization_path,
        log_path,
    ]:
        status = "exists" if path.exists() else "missing"
        print(f"- {path} ({status})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
