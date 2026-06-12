#!/usr/bin/env python3
"""Serve a local human review carousel for Playwright CLI matrix artifacts."""

import argparse
import json
import mimetypes
import posixpath
import shutil
import sys
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MANIFEST = REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Playwright CLI Artifact Review</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #16181d;
      --muted: #5f6877;
      --line: #d9dee7;
      --accent: #2563eb;
      --accept: #15803d;
      --review: #b45309;
      --reject: #b91c1c;
      --shadow: 0 10px 28px rgba(31, 41, 55, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 5;
      background: rgba(246, 247, 249, 0.96);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(10px);
    }
    .topbar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: center;
      width: min(1440px, calc(100vw - 40px));
      margin: 0 auto;
      padding: 14px 0;
    }
    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .subtle { color: var(--muted); }
    .progress {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      align-items: center;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      background: var(--panel);
      color: var(--muted);
      white-space: nowrap;
    }
    main {
      width: min(1440px, calc(100vw - 40px));
      margin: 18px auto 36px;
    }
    .carousel {
      display: grid;
      grid-template-columns: 44px minmax(0, 1fr) 44px;
      gap: 12px;
      align-items: stretch;
    }
    .nav {
      align-self: center;
      width: 44px;
      height: 88px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--ink);
      font-size: 30px;
      cursor: pointer;
      box-shadow: var(--shadow);
    }
    .nav:hover { border-color: var(--accent); }
    .slide {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .slide-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      align-items: start;
    }
    h2 {
      margin: 0 0 6px;
      font-size: 24px;
      line-height: 1.18;
      letter-spacing: 0;
    }
    .url {
      margin: 0;
      overflow-wrap: anywhere;
      color: var(--muted);
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, auto);
      gap: 8px;
      align-items: center;
      justify-content: end;
      font-size: 13px;
    }
    .switch {
      display: grid;
      grid-template-columns: repeat(3, minmax(112px, 1fr));
      gap: 6px;
      padding: 12px 20px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }
    .switch label {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      font-weight: 700;
      cursor: pointer;
      user-select: none;
    }
    .switch input {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }
    .switch label:has(input:checked) {
      color: #fff;
      border-color: transparent;
    }
    .switch label.accept:has(input:checked) { background: var(--accept); }
    .switch label.review:has(input:checked) { background: var(--review); }
    .switch label.reject:has(input:checked) { background: var(--reject); }
    .comment {
      display: none;
      padding: 0 20px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }
    .comment.visible { display: block; }
    .comment textarea {
      width: 100%;
      min-height: 76px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
    }
    .body {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
      gap: 18px;
      padding: 18px 20px 20px;
    }
    .shots {
      display: grid;
      gap: 16px;
      min-width: 0;
    }
    .shot {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .shot h3, .side h3 {
      margin: 0;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
      letter-spacing: 0;
      background: #f9fafb;
    }
    .shot-frame {
      max-height: 620px;
      overflow: auto;
      background: #eef1f5;
    }
    .shot-frame.compact { max-height: 420px; }
    img {
      display: block;
      max-width: 100%;
      height: auto;
      background: #fff;
    }
    .side {
      display: grid;
      gap: 16px;
      align-content: start;
      min-width: 0;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .panel-body {
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .links {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    a {
      color: var(--accent);
      text-decoration: none;
      overflow-wrap: anywhere;
    }
    a:hover { text-decoration: underline; }
    .ready {
      margin-top: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 14px 16px;
      color: var(--muted);
    }
    .toast {
      position: fixed;
      right: 20px;
      bottom: 20px;
      max-width: 360px;
      padding: 12px 14px;
      border-radius: 8px;
      color: #fff;
      background: #111827;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 160ms ease, transform 160ms ease;
      pointer-events: none;
      z-index: 20;
    }
    .toast.visible {
      opacity: 1;
      transform: translateY(0);
    }
    @media (max-width: 960px) {
      .topbar, main { width: min(100vw - 24px, 1440px); }
      .carousel { grid-template-columns: 1fr; }
      .nav { width: 100%; height: 44px; }
      .slide-head, .body { grid-template-columns: 1fr; }
      .metrics { justify-content: start; grid-template-columns: repeat(2, auto); }
      .switch { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Playwright CLI Artifact Review</h1>
        <div class="subtle" id="gate-copy">Review draft saves locally. Return to the agent session and say "ready" to submit.</div>
      </div>
      <div class="progress" id="progress"></div>
    </div>
  </header>
  <main>
    <div class="carousel">
      <button class="nav" id="prev" type="button" aria-label="Previous slide">&lsaquo;</button>
      <section class="slide" id="slide"></section>
      <button class="nav" id="next" type="button" aria-label="Next slide">&rsaquo;</button>
    </div>
    <div class="ready">
      Final approval is intentionally not submitted from this browser page. When your review choices are set, return to the same agent session that started this process and say <strong>ready</strong>.
    </div>
  </main>
  <div class="toast" id="toast"></div>
  <script>
    const state = {
      manifest: null,
      draft: {},
      index: 0,
      saveTimer: null,
    };

    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));

    const rel = (path) => `/artifact/${String(path || "").split("/").map(encodeURIComponent).join("/")}`;
    const textLength = (page) => Number(page.visible_text_length || 0).toLocaleString();
    const dims = (dim) => dim ? `${dim.width}x${dim.height}` : "missing";

    function ensureDecision(slug) {
      if (!state.draft[slug]) {
        state.draft[slug] = { decision: "accept", comment: "" };
      }
      return state.draft[slug];
    }

    function showToast(message) {
      const toast = document.getElementById("toast");
      toast.textContent = message;
      toast.classList.add("visible");
      clearTimeout(showToast.timer);
      showToast.timer = setTimeout(() => toast.classList.remove("visible"), 1400);
    }

    async function saveDraftSoon() {
      clearTimeout(state.saveTimer);
      state.saveTimer = setTimeout(saveDraft, 180);
    }

    async function saveDraft() {
      const response = await fetch("/api/draft", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ decisions: state.draft }),
      });
      if (!response.ok) {
        showToast("Draft save failed");
        return;
      }
      showToast("Draft saved locally");
    }

    function updateProgress() {
      const pages = state.manifest.pages;
      const counts = pages.reduce((acc, page) => {
        const decision = ensureDecision(page.slug).decision;
        acc[decision] = (acc[decision] || 0) + 1;
        return acc;
      }, {});
      document.getElementById("progress").innerHTML = `
        <span class="pill">${state.index + 1} / ${pages.length}</span>
        <span class="pill">Accept ${counts.accept || 0}</span>
        <span class="pill">Needs review ${counts.needs_review || 0}</span>
        <span class="pill">Reject ${counts.reject || 0}</span>
      `;
    }

    function renderSlide() {
      const page = state.manifest.pages[state.index];
      const decision = ensureDecision(page.slug);
      const artifacts = page.artifacts || {};
      const shotDims = page.screenshot_dimensions || {};
      const commentVisible = decision.decision === "accept" ? "" : " visible";
      document.getElementById("slide").innerHTML = `
        <div class="slide-head">
          <div>
            <h2>${escapeHtml(page.slug)}</h2>
            <p class="url"><a href="${escapeHtml(page.url)}" target="_blank" rel="noreferrer">${escapeHtml(page.url)}</a></p>
          </div>
          <div class="metrics">
            <span class="pill">Target ${escapeHtml(page.target_used || "missing")}</span>
            <span class="pill">Hidden ${escapeHtml(page.hidden_count)}</span>
            <span class="pill">Restored ${escapeHtml(page.restored_count)}</span>
            <span class="pill">Text ${textLength(page)} chars</span>
          </div>
        </div>
        <div class="switch" role="radiogroup" aria-label="Review decision">
          <label class="accept"><input type="radio" name="decision" value="accept" ${decision.decision === "accept" ? "checked" : ""}>Accept</label>
          <label class="review"><input type="radio" name="decision" value="needs_review" ${decision.decision === "needs_review" ? "checked" : ""}>Needs review</label>
          <label class="reject"><input type="radio" name="decision" value="reject" ${decision.decision === "reject" ? "checked" : ""}>Reject</label>
        </div>
        <div class="comment${commentVisible}" id="comment-wrap">
          <textarea id="comment" placeholder="Optional comment for this decision">${escapeHtml(decision.comment || "")}</textarea>
        </div>
        <div class="body">
          <div class="shots">
            <div class="shot">
              <h3>Viewport Screenshot (${escapeHtml(dims(shotDims.viewport))})</h3>
              <div class="shot-frame compact"><img src="${rel(artifacts.viewport)}" alt="Viewport screenshot"></div>
            </div>
            <div class="shot">
              <h3>Full-Page Screenshot (${escapeHtml(dims(shotDims.full_page))})</h3>
              <div class="shot-frame"><img src="${rel(artifacts.full_page)}" alt="Full page screenshot"></div>
            </div>
          </div>
          <div class="side">
            <div class="shot">
              <h3>Element Screenshot (${escapeHtml(dims(shotDims.element))})</h3>
              <div class="shot-frame compact"><img src="${rel(artifacts.element)}" alt="Element screenshot"></div>
            </div>
            <div class="panel">
              <h3>Artifact Links</h3>
              <div class="panel-body links">
                <a href="${rel(artifacts.visible_text_stdout)}" target="_blank">Visible text</a>
                <a href="${rel(artifacts.snapshot)}" target="_blank">Snapshot</a>
                <a href="${rel(artifacts.manifest)}" target="_blank">Page manifest</a>
                <a href="${rel(artifacts.log)}" target="_blank">Log</a>
              </div>
            </div>
          </div>
        </div>
      `;
      document.querySelectorAll('input[name="decision"]').forEach((input) => {
        input.addEventListener("change", (event) => {
          decision.decision = event.target.value;
          const wrap = document.getElementById("comment-wrap");
          wrap.classList.toggle("visible", decision.decision !== "accept");
          updateProgress();
          saveDraftSoon();
        });
      });
      const comment = document.getElementById("comment");
      comment.addEventListener("input", (event) => {
        decision.comment = event.target.value;
        saveDraftSoon();
      });
      updateProgress();
    }

    function move(delta) {
      const count = state.manifest.pages.length;
      state.index = (state.index + delta + count) % count;
      renderSlide();
    }

    async function boot() {
      const manifestResponse = await fetch("/api/manifest");
      state.manifest = await manifestResponse.json();
      const draftResponse = await fetch("/api/draft");
      const draftPayload = await draftResponse.json();
      state.draft = draftPayload.decisions || {};
      for (const page of state.manifest.pages) {
        ensureDecision(page.slug);
      }
      document.getElementById("prev").addEventListener("click", () => move(-1));
      document.getElementById("next").addEventListener("click", () => move(1));
      document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") move(-1);
        if (event.key === "ArrowRight") move(1);
      });
      renderSlide();
      await saveDraft();
    }

    boot().catch((error) => {
      document.getElementById("slide").innerHTML = `<div class="panel-body">Failed to load review data: ${escapeHtml(error.message)}</div>`;
    });
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a local approval carousel for Playwright CLI public-page matrix artifacts."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Aggregate matrix manifest to review",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the local review URL in the system browser after the server starts",
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


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def visible_text_length(page: dict[str, Any]) -> int:
    path = page.get("artifacts", {}).get("visible_text_stdout")
    if not path:
        return 0
    artifact_path = (REPO_ROOT / path).resolve()
    if not artifact_path.exists() or REPO_ROOT not in artifact_path.parents:
        return 0
    return len(artifact_path.read_text(encoding="utf-8", errors="replace"))


def load_review_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        raise SystemExit(f"Invalid matrix manifest: {manifest_path}")
    enriched = json.loads(json.dumps(manifest))
    for page in enriched["pages"]:
        page["visible_text_length"] = visible_text_length(page)
    return enriched


class ReviewServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], manifest_path: Path):
        self.manifest_path = manifest_path
        self.artifact_root = manifest_path.parent
        self.draft_path = self.artifact_root / "review-draft.json"
        super().__init__(server_address, ReviewHandler)


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format: str, *args: object) -> None:
        print("[review-server] " + format % args, file=sys.stderr)

    def send_text(self, status: HTTPStatus, content: str, content_type: str = "text/plain") -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", f"{content_type}; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status: HTTPStatus, value: Any) -> None:
        data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.send_text(HTTPStatus.OK, HTML, "text/html")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path == "/api/manifest":
            self.send_json(HTTPStatus.OK, load_review_manifest(self.server.manifest_path))
            return
        if parsed.path == "/api/draft":
            draft = read_json(self.server.draft_path, {"decisions": {}})
            self.send_json(HTTPStatus.OK, draft)
            return
        if parsed.path.startswith("/artifact/"):
            self.serve_artifact(parsed.path.removeprefix("/artifact/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/draft":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        decisions = payload.get("decisions")
        if not isinstance(decisions, dict):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing decisions object"})
            return
        manifest = load_review_manifest(self.server.manifest_path)
        page_slugs = {page["slug"] for page in manifest["pages"]}
        clean: dict[str, dict[str, str]] = {}
        for slug, decision in decisions.items():
            if slug not in page_slugs or not isinstance(decision, dict):
                continue
            value = decision.get("decision", "accept")
            if value not in {"accept", "needs_review", "reject"}:
                value = "accept"
            clean[slug] = {
                "decision": value,
                "comment": str(decision.get("comment", "")),
            }
        for slug in page_slugs:
            clean.setdefault(slug, {"decision": "accept", "comment": ""})
        draft = {
            "status": "draft",
            "manifest": str(self.server.manifest_path.relative_to(REPO_ROOT)),
            "updated_at_epoch": int(time.time()),
            "decisions": clean,
        }
        write_json_atomic(self.server.draft_path, draft)
        self.send_json(HTTPStatus.OK, {"ok": True, "draft": str(self.server.draft_path)})

    def serve_artifact(self, encoded_path: str) -> None:
        relative = Path(posixpath.normpath(unquote(encoded_path)))
        if relative.is_absolute() or ".." in relative.parts:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        artifact_path = (REPO_ROOT / relative).resolve()
        if not artifact_path.exists() or REPO_ROOT not in artifact_path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        artifact_root = self.server.artifact_root.resolve()
        if artifact_path != artifact_root and artifact_root not in artifact_path.parents:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(artifact_path.stat().st_size))
        self.end_headers()
        with artifact_path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)


def main() -> int:
    args = parse_args()
    manifest_path = safe_manifest_path(args.manifest)
    server = ReviewServer((args.host, args.port), manifest_path)
    host, port = server.server_address
    print(f"[review-server] serving {manifest_path}")
    print(f"[review-server] open http://{host}:{port}/")
    print(f"[review-server] draft path: {server.draft_path}")
    if args.open:
        webbrowser.open(f"http://{host}:{port}/", new=2)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[review-server] stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
