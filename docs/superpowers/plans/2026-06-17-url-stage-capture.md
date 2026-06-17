# URL Stage Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `./eba dev stage-url <url>` path that turns any URL into a frozen, overlay-ready workbench artifact where the visual snapshot is durable and the natural-language intent spine is primary.

**Architecture:** Playwright CLI captures the live page and writes disk artifacts. A Python capture helper normalizes those artifacts into one URL stage manifest, one screenshot, one canonical `web-snapshot-data.json`, and synthetic `web-snapshot.html`. The workbench projects the staged page as `type: html` with `kind: web_snapshot` plus one supporting `kind: web_snapshot_data` artifact, so the app shell uses the existing same-origin HTML renderer and HTML element inspector without a new renderer or artifact component.

**Tech Stack:** Python command surface and manifest generation, checked-in Playwright CLI snippets, static browser primitives under `scripts/artifacts/`, existing artifact workbench server/projection, Node smoke checks, local HTML fixture for live validation.

---

## File Structure

- Create `scripts/url_stage_capture.py`: URL stage capture helper, manifest writer, canonical web-snapshot data builder, target-map projection, and synthetic HTML generation.
- Create `scripts/playwright-snippets/extract-web-blueprint.js`: checked-in Playwright CLI snippet that extracts viewport, document, and element evidence from the live page.
- Create `scripts/playwright-fixtures/url-stage-basic.html`: deterministic local page used by tests and live smoke.
- Create `scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js`: live workbench smoke for hover/click-ready web snapshot rendering.
- Modify `scripts/eba_cli.py`: add `stage-url`, include new Python/Node checks, and wire the fixture option used by the smoke.
- Modify `scripts/workbench_projection.py`: detect URL stage manifests and project an HTML-backed `web_snapshot` artifact plus one supporting `web_snapshot_data` artifact.
- Modify `scripts/workbench_projection_shape_check.py`: add shape assertions for a generated URL stage fixture manifest.
- Modify `tests/test_url_stage_capture.py`: focused Python tests for manifest shape, target-map projection, synthetic HTML, and safe output paths.
- Modify `tests/test_artifact_workbench_browser_control.py`: validation-surface assertions for the new snippets.
- Modify `scripts/AGENTS.md`: record the local contract for URL stage capture files. Update root `AGENTS.md` only if the command becomes a durable startup/demo recommendation.

## Out Of Scope

- Do not refactor the artifact component registry in this slice. The URL stage
  proof should keep the app shell ignorant by projecting the staged page as
  `type: html`, `kind: web_snapshot`.
- A self-registering artifact component registry is valuable follow-up work:
  artifact modules should eventually register themselves so new renderers,
  controls, readouts, and inspectors do not require app-shell changes.
  Track that separately in
  [issue #36](https://github.com/michaelblum/employer-brand-audits/issues/36).

## Accepted Follow-Up Amendment

After the first slice, the URL-stage artifact shape was tightened:

- Do not expose separate `target_map`, `web_blueprint`, `visible_text`,
  `page_snapshot`, or `page_screenshot` sidebar artifacts.
- Write `web-snapshot-data.json` as the canonical data package. It contains
  `visual`, `source_trees`, `projection_catalog`, `projections`, `ui_views`,
  replay policy, and site fingerprint hints.
- Treat UI toolbar modes as a curated subset of machine projections.
- Render `kind: web_snapshot` HTML as the root stage surface, not inside the
  generic HTML article/header wrapper.
- Make the managed workbench summon path self-heal stale Python server code by
  comparing server startup source fingerprints, not only dynamic asset hashes.

## Task 1: URL Stage Data Model

**Files:**
- Create: `scripts/url_stage_capture.py`
- Create: `tests/test_url_stage_capture.py`
- Test: `tests/test_url_stage_capture.py`

- [ ] **Step 1: Write the failing manifest and target-map tests**

Add this initial test file:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.url_stage_capture import (
    REPO_ROOT,
    build_target_map,
    build_web_snapshot_html,
    safe_stage_output_dir,
    slugify_stage_name,
    write_url_stage_manifest,
)


class UrlStageCaptureTests(unittest.TestCase):
    def test_slugify_stage_name_keeps_human_name_safe(self) -> None:
        self.assertEqual(slugify_stage_name("Acme Careers!"), "acme-careers")
        self.assertEqual(slugify_stage_name("https://example.com/jobs?q=robotics"), "example-com-jobs")

    def test_safe_stage_output_dir_refuses_repo_root(self) -> None:
        with self.assertRaises(SystemExit):
            safe_stage_output_dir(REPO_ROOT)

    def test_target_map_projects_blueprint_rects_to_screenshot_space(self) -> None:
        blueprint = {
            "url": "https://example.com/jobs",
            "viewport": {"width": 1000, "height": 800, "devicePixelRatio": 2},
            "document": {"width": 1000, "height": 1200},
            "elements": [
                {
                    "uid": "target-1",
                    "tag": "a",
                    "role": "link",
                    "accessible_name": "Apply now",
                    "text": "Apply now",
                    "selector_candidates": ["#apply", "a.cta"],
                    "document_rect": {"x": 100, "y": 200, "width": 150, "height": 40},
                    "target_kind": "link",
                    "confidence": 0.92,
                }
            ],
        }

        target_map = build_target_map(
            blueprint,
            screenshot_dimensions={"width": 2000, "height": 2400},
            screenshot_path="artifacts/url-stage/acme/latest/page.full-page.png",
        )

        self.assertEqual(target_map["schema_version"], "url_stage_target_map.v0")
        self.assertEqual(target_map["coordinate_space"], "screenshot")
        self.assertEqual(target_map["targets"][0]["rect"], {"x": 200, "y": 400, "width": 300, "height": 80})
        self.assertEqual(target_map["targets"][0]["selector_candidates"], ["#apply", "a.cta"])

    def test_web_snapshot_html_uses_image_background_and_proxy_targets(self) -> None:
        target_map = {
            "source_url": "https://example.com/jobs",
            "screenshot": {
                "path": "artifacts/url-stage/acme/latest/page.full-page.png",
                "dimensions": {"width": 1200, "height": 900},
            },
            "targets": [
                {
                    "id": "target-1",
                    "rect": {"x": 20, "y": 30, "width": 200, "height": 48},
                    "label": "Apply now",
                    "role": "link",
                    "target_kind": "link",
                    "selector_candidates": ["#apply"],
                }
            ],
        }

        html = build_web_snapshot_html(target_map)

        self.assertIn('data-web-snapshot-stage="true"', html)
        self.assertIn('src="/artifacts/url-stage/acme/latest/page.full-page.png"', html)
        self.assertIn('data-web-target-id="target-1"', html)
        self.assertIn("left:20px;top:30px;width:200px;height:48px", html)
        self.assertIn("Apply now", html)

    def test_write_url_stage_manifest_records_blueprint_and_derived_artifacts(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=".url-stage-test-", dir=REPO_ROOT / "artifacts"))
        try:
            manifest_path = write_url_stage_manifest(
                output_dir=root,
                slug="acme-careers",
                url="https://example.com/jobs",
                status="passed",
                viewport={"width": 1000, "height": 800, "devicePixelRatio": 1},
                paths={
                    "blueprint": root / "web-blueprint.json",
                    "target_map": root / "target-map.json",
                    "web_snapshot": root / "web-snapshot.html",
                    "page_screenshot": root / "page.full-page.png",
                    "visible_text": root / "visible-text.txt",
                    "page_snapshot": root / "page-snapshot.txt",
                    "capture_log": root / "capture.log",
                },
                screenshot_dimensions={"width": 1000, "height": 1200},
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            for child in sorted(root.glob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            root.rmdir()

        self.assertEqual(manifest["schema_version"], "url_stage_capture.v0")
        self.assertEqual(manifest["slug"], "acme-careers")
        self.assertEqual(manifest["artifacts"]["web_snapshot"], "artifacts/.url-stage-test-" + root.name.rsplit(".url-stage-test-", 1)[-1] + "/web-snapshot.html")
        self.assertEqual(manifest["screenshot"]["dimensions"], {"width": 1000, "height": 1200})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 tests/test_url_stage_capture.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.url_stage_capture'`.

- [ ] **Step 3: Implement the minimal data model helpers**

Create `scripts/url_stage_capture.py` with:

```python
#!/usr/bin/env python3
"""Capture a URL into a durable workbench web snapshot artifact."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "url-stage"


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        return str(resolved.relative_to(REPO_ROOT))
    return str(path)


def slugify_stage_name(value: str) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.netloc:
        raw = f"{parsed.netloc}{parsed.path}"
    raw = raw.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return slug[:80].strip("-") or "url-stage"


def safe_stage_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved == REPO_ROOT or REPO_ROOT not in resolved.parents:
        raise SystemExit(f"Refusing to replace unsafe output directory: {resolved}")
    return resolved


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def screenshot_rect(document_rect: dict[str, Any], *, scale_x: float, scale_y: float) -> dict[str, int]:
    return {
        "x": round(float(document_rect.get("x") or 0) * scale_x),
        "y": round(float(document_rect.get("y") or 0) * scale_y),
        "width": max(1, round(float(document_rect.get("width") or 0) * scale_x)),
        "height": max(1, round(float(document_rect.get("height") or 0) * scale_y)),
    }


def build_target_map(
    blueprint: dict[str, Any],
    *,
    screenshot_dimensions: dict[str, int],
    screenshot_path: str,
) -> dict[str, Any]:
    document = blueprint.get("document") if isinstance(blueprint.get("document"), dict) else {}
    document_width = max(1, float(document.get("width") or screenshot_dimensions["width"]))
    document_height = max(1, float(document.get("height") or screenshot_dimensions["height"]))
    scale_x = float(screenshot_dimensions["width"]) / document_width
    scale_y = float(screenshot_dimensions["height"]) / document_height
    targets = []
    for index, element in enumerate(blueprint.get("elements") or [], start=1):
        if not isinstance(element, dict) or not isinstance(element.get("document_rect"), dict):
            continue
        label = str(element.get("accessible_name") or element.get("text") or element.get("tag") or f"target {index}").strip()
        targets.append(
            {
                "id": str(element.get("uid") or f"target-{index}"),
                "label": label[:160],
                "role": str(element.get("role") or ""),
                "tag": str(element.get("tag") or ""),
                "text": str(element.get("text") or "")[:240],
                "target_kind": str(element.get("target_kind") or "element"),
                "rect": screenshot_rect(element["document_rect"], scale_x=scale_x, scale_y=scale_y),
                "selector_candidates": [str(item) for item in element.get("selector_candidates") or [] if str(item)],
                "confidence": float(element.get("confidence") or 0.5),
            }
        )
    return {
        "schema_version": "url_stage_target_map.v0",
        "coordinate_space": "screenshot",
        "source_url": str(blueprint.get("url") or ""),
        "viewport": blueprint.get("viewport") or {},
        "screenshot": {
            "path": screenshot_path,
            "dimensions": screenshot_dimensions,
        },
        "targets": targets,
    }


def build_web_snapshot_html(target_map: dict[str, Any]) -> str:
    screenshot = target_map.get("screenshot") if isinstance(target_map.get("screenshot"), dict) else {}
    dimensions = screenshot.get("dimensions") if isinstance(screenshot.get("dimensions"), dict) else {}
    image_path = "/" + str(screenshot.get("path") or "").lstrip("/")
    width = int(dimensions.get("width") or 1)
    height = int(dimensions.get("height") or 1)
    target_html = []
    for target in target_map.get("targets") or []:
        rect = target.get("rect") if isinstance(target.get("rect"), dict) else {}
        style = (
            f"left:{int(rect.get('x') or 0)}px;"
            f"top:{int(rect.get('y') or 0)}px;"
            f"width:{max(1, int(rect.get('width') or 1))}px;"
            f"height:{max(1, int(rect.get('height') or 1))}px"
        )
        metadata = html.escape(json.dumps(target, sort_keys=True))
        label = html.escape(str(target.get("label") or target.get("id") or "web target"))
        target_html.append(
            f'<button class="web-target" type="button" data-web-target-id="{html.escape(str(target.get("id") or ""))}" '
            f'data-web-target="{metadata}" style="{style}" aria-label="{label}" title="{label}"></button>'
        )
    return (
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8"><style>\n'
        "html,body{margin:0;background:#0f1115;}\n"
        ".web-snapshot-stage{position:relative;display:block;line-height:0;}\n"
        ".web-snapshot-stage img{display:block;width:100%;height:auto;}\n"
        ".web-target{position:absolute;border:0;background:rgba(70,132,255,0.01);padding:0;cursor:crosshair;}\n"
        ".web-target:hover,.web-target:focus{outline:2px solid #58a6ff;outline-offset:0;background:rgba(88,166,255,0.12);}\n"
        "</style></head><body>\n"
        f'<div class="web-snapshot-stage" data-web-snapshot-stage="true" style="width:{width}px;height:{height}px">\n'
        f'<img src="{html.escape(image_path)}" width="{width}" height="{height}" alt="Captured web page snapshot">\n'
        f"{''.join(target_html)}\n"
        "</div>\n"
        "</body></html>\n"
    )


def write_url_stage_manifest(
    *,
    output_dir: Path,
    slug: str,
    url: str,
    status: str,
    viewport: dict[str, Any],
    paths: dict[str, Path],
    screenshot_dimensions: dict[str, int],
) -> Path:
    manifest = {
        "schema_version": "url_stage_capture.v0",
        "slug": slug,
        "url": url,
        "status": status,
        "viewport": viewport,
        "screenshot": {
            "path": repo_relative(paths["page_screenshot"]),
            "dimensions": screenshot_dimensions,
        },
        "blueprint": {"path": repo_relative(paths["blueprint"])},
        "artifacts": {key: repo_relative(path) for key, path in sorted(paths.items())},
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python3 tests/test_url_stage_capture.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/url_stage_capture.py tests/test_url_stage_capture.py
git commit -m "Add URL stage capture data model"
```

## Task 2: Blueprint Extraction And Capture Command

**Files:**
- Create: `scripts/playwright-snippets/extract-web-blueprint.js`
- Create: `scripts/playwright-fixtures/url-stage-basic.html`
- Modify: `scripts/url_stage_capture.py`
- Modify: `scripts/eba_cli.py`
- Modify: `tests/test_url_stage_capture.py`
- Test: `tests/test_url_stage_capture.py`

- [ ] **Step 1: Add failing tests for command registration and fixture capture**

Append these tests to `UrlStageCaptureTests`:

```python
    def test_validation_includes_url_stage_capture_files(self) -> None:
        from scripts.eba_cli import validation_commands

        self.assertIn([sys.executable, "tests/test_url_stage_capture.py"], validation_commands())
        self.assertIn(["node", "--check", "scripts/playwright-snippets/extract-web-blueprint.js"], validation_commands())

    def test_stage_url_parser_is_registered(self) -> None:
        from scripts.eba_cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["dev", "stage-url", "https://example.com/jobs", "--name", "example-jobs", "--no-browser"])

        self.assertEqual(args.command, "stage-url")
        self.assertEqual(args.url, "https://example.com/jobs")
        self.assertEqual(args.name, "example-jobs")
        self.assertTrue(args.no_browser)
```

Add `import sys` to the imports in `tests/test_url_stage_capture.py`.

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 tests/test_url_stage_capture.py
```

Expected: failure showing `stage-url` is not a valid `./eba dev` subcommand and the snippet is not in validation.

- [ ] **Step 3: Create the deterministic fixture**

Create `scripts/playwright-fixtures/url-stage-basic.html`:

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>URL Stage Basic Fixture</title>
    <style>
      body { margin: 0; font-family: system-ui, sans-serif; color: #172033; background: #f6f7fb; }
      main { width: 960px; min-height: 1200px; margin: 0 auto; padding: 48px 32px; background: #fff; }
      h1 { margin: 0 0 24px; font-size: 44px; }
      .hero { border: 1px solid #d6dce8; padding: 32px; border-radius: 8px; }
      .actions { display: flex; gap: 16px; margin-top: 24px; }
      a, button { font: inherit; border-radius: 6px; padding: 12px 18px; }
      a { color: #fff; background: #215fd6; text-decoration: none; }
      button { border: 1px solid #8190aa; background: #fff; }
      form { margin-top: 420px; display: grid; gap: 12px; max-width: 420px; }
      label { display: grid; gap: 6px; font-weight: 700; }
      input { font: inherit; padding: 10px 12px; border: 1px solid #9aa8bd; border-radius: 4px; }
    </style>
  </head>
  <body>
    <main>
      <section class="hero" aria-label="Careers hero">
        <h1>Build robots that help people work safely</h1>
        <p>Acme Robotics is hiring field robotics engineers for autonomous inspection systems.</p>
        <div class="actions">
          <a id="apply" class="cta" href="/jobs/field-robotics-engineer">Apply now</a>
          <button id="talent-community" type="button">Join talent community</button>
        </div>
      </section>
      <form aria-label="Job alert form">
        <label>Email for job alerts <input id="email" type="email" placeholder="name@example.com"></label>
        <button id="subscribe" type="submit">Subscribe</button>
      </form>
    </main>
  </body>
</html>
```

- [ ] **Step 4: Create the blueprint extraction snippet**

Create `scripts/playwright-snippets/extract-web-blueprint.js`:

```js
async (page) => {
  return await page.evaluate(() => {
    const compact = (value, limit = 180) => String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
    const cssEscape = (value) => window.CSS?.escape ? window.CSS.escape(String(value)) : String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
    const roleFor = (el) => {
      const explicit = el.getAttribute("role");
      if (explicit) return explicit;
      const tag = el.tagName.toLowerCase();
      if (tag === "a" && el.getAttribute("href")) return "link";
      if (tag === "button") return "button";
      if (["input", "textarea", "select"].includes(tag)) return "textbox";
      if (/^h[1-6]$/.test(tag)) return "heading";
      if (tag === "img") return "image";
      if (["main", "section", "article", "nav", "header", "footer"].includes(tag)) return tag;
      return "";
    };
    const selectorCandidates = (el) => {
      const tag = el.tagName.toLowerCase();
      const candidates = [];
      if (el.id) candidates.push(`#${cssEscape(el.id)}`);
      const classes = [...el.classList].slice(0, 3).map((item) => `.${cssEscape(item)}`).join("");
      if (classes) candidates.push(`${tag}${classes}`);
      const aria = el.getAttribute("aria-label");
      if (aria) candidates.push(`${tag}[aria-label="${aria.replaceAll('"', '\\"')}"]`);
      candidates.push(tag);
      return [...new Set(candidates)];
    };
    const targetKind = (el, role) => {
      const tag = el.tagName.toLowerCase();
      if (role === "link" || tag === "a") return "link";
      if (role === "button" || tag === "button") return "button";
      if (["input", "textarea", "select"].includes(tag)) return "input";
      if (role === "heading" || /^h[1-6]$/.test(tag)) return "heading";
      if (tag === "img") return "image";
      if (["main", "section", "article", "nav"].includes(tag)) return "section";
      return "element";
    };
    const elements = [];
    const candidates = [...document.querySelectorAll("a[href],button,input,textarea,select,h1,h2,h3,main,section,article,img,[role],[aria-label]")];
    for (const [index, el] of candidates.entries()) {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      if (rect.width < 4 || rect.height < 4 || style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
        continue;
      }
      const role = roleFor(el);
      const text = compact(el.getAttribute("aria-label") || el.getAttribute("alt") || el.getAttribute("title") || el.textContent);
      elements.push({
        uid: `target-${index + 1}`,
        tag: el.tagName.toLowerCase(),
        role,
        target_kind: targetKind(el, role),
        accessible_name: text,
        text,
        selector_candidates: selectorCandidates(el),
        document_rect: {
          x: Math.round(rect.left + window.scrollX),
          y: Math.round(rect.top + window.scrollY),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        },
        confidence: role || text ? 0.85 : 0.55,
      });
    }
    return {
      schema_version: "url_stage_blueprint.v0",
      url: window.location.href,
      title: document.title,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio || 1,
      },
      document: {
        width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth || 0),
        height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0),
      },
      elements,
    };
  });
}
```

- [ ] **Step 5: Add capture orchestration to `url_stage_capture.py`**

Append functions `parse_playwright_cli_result`, `png_dimensions`, `command_for`, `run_step`, and `capture_url_stage`. Use the existing subprocess pattern from `scripts/playwright_cli_public_page_smoke.py`; keep the wrapper path as `scripts/playwright_cli_browser.py`; write these artifact filenames into `output_dir`:

```text
web-blueprint.json
target-map.json
web-snapshot.html
page.full-page.png
visible-text.txt
page-snapshot.txt
capture.log
settle.stdout.txt
hide-obscuring.stdout.txt
restore-page.stdout.txt
manifest.json
```

`capture_url_stage()` must:

1. safe-delete and recreate `output_dir`;
2. open the URL with `scripts/playwright_cli_browser.py open <url> --no-persistent --session <session>`;
3. resize to deterministic `width` and `height`;
4. run `settle-page.js` and `hide-obscuring-elements.js`;
5. run `extract-web-blueprint.js`, parse its `### Result` JSON, and write `web-blueprint.json`;
6. run `snapshot page-snapshot.txt`;
7. run `extract-visible-text.js`, parse its result as text when possible, and write `visible-text.txt`;
8. run `screenshot page.full-page.png --full-page`;
9. compute PNG dimensions, build `target-map.json`, generate `web-snapshot.html`, and write `manifest.json`;
10. run `restore-page.js` and close the session in `finally`.

- [ ] **Step 6: Wire `./eba dev stage-url`**

Modify `scripts/eba_cli.py`:

```python
from scripts.url_stage_capture import capture_url_stage, slugify_stage_name
```

Add `scripts/url_stage_capture.py` to `COMPILE_TARGETS`, add validation commands for `tests/test_url_stage_capture.py` and `node --check scripts/playwright-snippets/extract-web-blueprint.js`, then add:

```python
def command_stage_url(args: argparse.Namespace) -> int:
    slug = slugify_stage_name(args.name or args.url)
    manifest = capture_url_stage(
        url=args.url,
        slug=slug,
        output_dir=REPO_ROOT / "artifacts" / "url-stage" / slug / "latest",
        session=args.session,
        width=args.width,
        height=args.height,
    )
    if args.json:
        print_json({"status": "passed", "manifest": str(manifest.relative_to(REPO_ROOT))})
    else:
        print(f"manifest={manifest.relative_to(REPO_ROOT)}")
    if not args.no_browser:
        return command_demo(argparse.Namespace(manifest=manifest, fixture=None, no_browser=False, json=args.json))
    return 0
```

Register the parser:

```python
stage_url = dev_subparsers.add_parser("stage-url", help="Capture a URL as an overlay-ready workbench stage")
stage_url.add_argument("url")
stage_url.add_argument("--name")
stage_url.add_argument("--session", default="eba-url-stage")
stage_url.add_argument("--width", type=int, default=1365)
stage_url.add_argument("--height", type=int, default=900)
stage_url.add_argument("--no-browser", action="store_true")
stage_url.add_argument("--json", action="store_true")
stage_url.set_defaults(func=command_stage_url)
```

- [ ] **Step 7: Run focused checks**

Run:

```bash
python3 tests/test_url_stage_capture.py
node --check scripts/playwright-snippets/extract-web-blueprint.js
python3 -m py_compile scripts/url_stage_capture.py scripts/eba_cli.py
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/url_stage_capture.py scripts/playwright-snippets/extract-web-blueprint.js scripts/playwright-fixtures/url-stage-basic.html scripts/eba_cli.py tests/test_url_stage_capture.py
git commit -m "Add URL stage capture command"
```

## Task 3: URL Stage Projection

**Files:**
- Modify: `scripts/workbench_projection.py`
- Modify: `scripts/workbench_projection_shape_check.py`
- Modify: `tests/test_url_stage_capture.py`
- Test: `tests/test_url_stage_capture.py`, `scripts/workbench_projection_shape_check.py`

- [ ] **Step 1: Add failing projection test**

Append this test:

```python
    def test_url_stage_manifest_projects_web_snapshot_and_evidence_artifacts(self) -> None:
        from scripts.workbench_projection import project_workbench_manifest

        root = Path(tempfile.mkdtemp(prefix=".url-stage-projection-", dir=REPO_ROOT / "artifacts"))
        try:
            for name in [
                "web-blueprint.json",
                "target-map.json",
                "web-snapshot.html",
                "page.full-page.png",
                "visible-text.txt",
                "page-snapshot.txt",
                "capture.log",
            ]:
                (root / name).write_text("{}\n" if name.endswith(".json") else "fixture\n", encoding="utf-8")
            manifest_path = write_url_stage_manifest(
                output_dir=root,
                slug="acme-careers",
                url="https://example.com/jobs",
                status="passed",
                viewport={"width": 1000, "height": 800, "devicePixelRatio": 1},
                paths={
                    "blueprint": root / "web-blueprint.json",
                    "target_map": root / "target-map.json",
                    "web_snapshot": root / "web-snapshot.html",
                    "page_screenshot": root / "page.full-page.png",
                    "visible_text": root / "visible-text.txt",
                    "page_snapshot": root / "page-snapshot.txt",
                    "capture_log": root / "capture.log",
                },
                screenshot_dimensions={"width": 1000, "height": 1200},
            )
            projection = project_workbench_manifest(manifest_path)
        finally:
            for child in sorted(root.glob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            root.rmdir()

        artifact_by_id = {artifact["id"]: artifact for artifact in projection["artifacts"]}
        self.assertEqual(projection["source"]["format"], "url_stage_capture")
        self.assertEqual(artifact_by_id["acme-careers:web-snapshot"]["type"], "html")
        self.assertEqual(artifact_by_id["acme-careers:web-snapshot"]["kind"], "web_snapshot")
        self.assertEqual(artifact_by_id["acme-careers:web-snapshot"]["path"].endswith("web-snapshot.html"), True)
        self.assertEqual(artifact_by_id["acme-careers:target-map"]["type"], "json")
        self.assertIn("annotate", artifact_by_id["acme-careers:web-snapshot"]["capabilities"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 tests/test_url_stage_capture.py
```

Expected: `Unsupported workbench manifest shape`.

- [ ] **Step 3: Implement URL stage projection**

In `scripts/workbench_projection.py`, add:

```python
URL_STAGE_ARTIFACTS = {
    "web_snapshot": ("Web Snapshot", "web.stage", "html", "web_snapshot", 1),
    "page_screenshot": ("Page Screenshot", "web.screenshot", "image", "screenshot", 1),
    "target_map": ("Target Map", "web.target_map", "json", "target_map", 1),
    "visible_text": ("Visible Text", "web.visible_text", "text", "visible_text", 1),
    "page_snapshot": ("Page Snapshot", "web.page_snapshot", "text", "page_snapshot", 1),
    "capture_log": ("Capture Log", "debug.log", "log", "capture_log", 1),
}
```

Add `project_url_stage_manifest(path)` that reads `schema_version == "url_stage_capture.v0"`, creates one workflow step `step:url-stage:<slug>`, one URL resource, artifact IDs shaped as `<slug>:<kind-with-dashes>`, and a `source_page_bundle` group containing `web-snapshot`, `page-screenshot`, `target-map`, and `visible-text`.

Update `project_workbench_manifest()` before the ADR-002 branch:

```python
    if isinstance(manifest, dict) and manifest.get("schema_version") == "url_stage_capture.v0":
        return project_url_stage_manifest(path)
```

- [ ] **Step 4: Add projection shape check coverage**

In `scripts/workbench_projection_shape_check.py`, create a temp URL stage fixture using `write_url_stage_manifest()` and assert:

```python
require(payload["source"]["format"] == "url_stage_capture", "URL stage source format drifted")
web = next((artifact for artifact in payload["artifacts"] if artifact["id"].endswith(":web-snapshot")), None)
require(web and web["type"] == "html" and web["kind"] == "web_snapshot", "URL stage web snapshot artifact missing")
require("annotate" in web["capabilities"], "URL stage web snapshot must be annotatable")
```

- [ ] **Step 5: Run focused checks**

Run:

```bash
python3 tests/test_url_stage_capture.py
python3 scripts/workbench_projection_shape_check.py
python3 -m py_compile scripts/workbench_projection.py scripts/workbench_projection_shape_check.py
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/workbench_projection.py scripts/workbench_projection_shape_check.py tests/test_url_stage_capture.py
git commit -m "Project URL stage manifests into the workbench"
```

## Task 4: Live Workbench Smoke

**Files:**
- Create: `scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js`
- Modify: `scripts/eba_cli.py`
- Modify: `tests/test_artifact_workbench_browser_control.py`
- Test: local fixture smoke through `./eba dev stage-url`

- [ ] **Step 1: Add failing validation assertions**

In `tests/test_artifact_workbench_browser_control.py`, assert validation includes:

```python
self.assertIn(
    ["node", "--check", "scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js"],
    validation_commands(),
)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
python3 tests/test_artifact_workbench_browser_control.py -k validation_surface
```

Expected: missing validation command assertion.

- [ ] **Step 3: Create the web snapshot smoke snippet**

Create `scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js`:

```js
async (page) => {
  await page.reload();
  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
    const projection = await fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json());
    const artifact = (projection.artifacts || []).find((item) => item.type === "html" && item.kind === "web_snapshot");
    if (!artifact) throw new Error("Missing HTML-backed web_snapshot artifact");
    const index = (state.collection?.artifacts || []).findIndex((item) => item.id === artifact.id);
    if (index < 0) throw new Error("web_snapshot artifact is missing from collection");
    return { index, id: artifact.id };
  });
  await page.evaluate((index) => {
    document.querySelector(`.artifact-row[data-index="${index}"]`)?.click();
  }, model.index);
  await page.waitForFunction(() => {
    const frame = document.querySelector("[data-html-frame]");
    const doc = frame?.contentDocument;
    return doc?.querySelector("[data-web-snapshot-stage]") && doc.querySelector("[data-web-target-id]");
  }, null, { timeout: 5000 });
  return await page.evaluate(() => {
    const frame = document.querySelector("[data-html-frame]");
    const doc = frame?.contentDocument;
    const target = doc?.querySelector("[data-web-target-id]");
    return {
      rendererType: document.querySelector("[data-artifact-renderer]")?.getAttribute("data-artifact-renderer"),
      hasStage: Boolean(doc?.querySelector("[data-web-snapshot-stage]")),
      targetId: target?.getAttribute("data-web-target-id"),
      targetLabel: target?.getAttribute("aria-label"),
      readout: document.querySelector("#artifact-readout")?.textContent?.trim(),
      imageControlsMounted: Boolean(document.querySelector("#image-controls")),
      markdownControlsMounted: Boolean(document.querySelector("#markdown-controls")),
    };
  });
}
```

- [ ] **Step 4: Add validation command**

In `scripts/eba_cli.py`, add:

```python
["node", "--check", "scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js"],
```

- [ ] **Step 5: Run local fixture capture and live workbench smoke**

Run:

```bash
python3 -m http.server 8899 --directory scripts/playwright-fixtures
```

In a second terminal:

```bash
./eba dev stage-url http://127.0.0.1:8899/url-stage-basic.html --name url-stage-basic --json
./eba dev workbench reset artifacts/url-stage/url-stage-basic/latest/manifest.json --json
python3 scripts/playwright_cli_browser.py run-code scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js --session eba-workbench
```

Expected: smoke result reports `hasStage: true`, a non-empty `targetId`, and no image or markdown controls mounted.

- [ ] **Step 6: Stop the fixture server**

Press `Ctrl-C` in the terminal running `python3 -m http.server 8899 --directory scripts/playwright-fixtures`.

- [ ] **Step 7: Commit**

```bash
git add scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js scripts/eba_cli.py tests/test_artifact_workbench_browser_control.py
git commit -m "Smoke web snapshot workbench rendering"
```

## Task 5: Documentation And Full Validation

**Files:**
- Modify: `scripts/AGENTS.md`
- Optionally modify: `AGENTS.md`
- Test: `./eba dev validate`

- [ ] **Step 1: Update local DOX guidance**

In `scripts/AGENTS.md`, add a concise work-guidance bullet:

```markdown
- URL stage capture treats the screenshot plus blueprint-derived target map as
  the durable intent surface. Keep selector candidates advisory; do not make
  replay selectors the source of truth for interaction overlays.
```

Update root `AGENTS.md` only if the implementation makes `./eba dev stage-url`
a routine startup/demo command rather than a specialized capture command.

- [ ] **Step 2: Run full validation**

Run:

```bash
./eba dev validate
```

Expected: all Python, Node, projection, MCP, and `git diff --check` checks pass.

- [ ] **Step 3: Confirm repo state**

Run:

```bash
git status --short --branch
```

Expected: dirty files are only the URL stage implementation files intended for this plan.

- [ ] **Step 4: Commit**

```bash
git add scripts/AGENTS.md AGENTS.md
git commit -m "Document URL stage capture contracts"
```

If `AGENTS.md` is unchanged, run:

```bash
git add scripts/AGENTS.md
git commit -m "Document URL stage capture contracts"
```

- [ ] **Step 5: Prepare self-guided demo**

Run:

```bash
python3 -m http.server 8899 --directory scripts/playwright-fixtures
```

In a second terminal:

```bash
./eba dev stage-url http://127.0.0.1:8899/url-stage-basic.html --name url-stage-basic --json
./eba dev workbench reset artifacts/url-stage/url-stage-basic/latest/manifest.json --json
```

Expected: managed `eba-workbench` opens on the URL stage manifest with the HTML-backed `web_snapshot` artifact available for first-pass visual review.

Stop the fixture server with `Ctrl-C` after the demo surface is prepared.

## Self-Review Notes

- Spec coverage: Tasks 1-2 implement capture, blueprint, target-map, and synthetic HTML. Task 3 implements projection. Task 4 proves hover/click-ready rendering through the existing HTML inspector spine in the managed workbench. Task 5 covers DOX and validation.
- Placeholder scan: the plan contains no `TBD` or deferred implementation step in the first slice. Deferred replay remains outside this implementation plan by design.
- Type consistency: the render type is `html`; the semantic artifact kind is `web_snapshot`; the generated file is `web-snapshot.html`; projection artifact IDs use `web-snapshot`; target-map schema is `url_stage_target_map.v0`; blueprint schema is `url_stage_blueprint.v0`.
