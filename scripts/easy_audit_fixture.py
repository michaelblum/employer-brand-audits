#!/usr/bin/env python3
"""Generate a deterministic ADR-002 easy-audit demo fixture."""

from __future__ import annotations

import argparse
import base64
import json
import struct
import zlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "easy-audit" / "latest"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
MOCK_SITE_PAGES = [
    {"slug": "careers", "path": "site/index.html", "url_path": "/"},
    {"slug": "roles", "path": "site/roles.html", "url_path": "/roles.html"},
    {"slug": "culture", "path": "site/culture.html", "url_path": "/culture.html"},
]
CAPTURE_FEATURES = [
    "sticky_header",
    "fixed_overlay_hide_restore",
    "animation_settle",
    "shadow_dom",
    "internal_scroll",
    "tall_full_page",
]


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def mock_capture_png(width: int = 1000, height: int = 720) -> bytes:
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if y < 76:
                rgb = (18, 34, 56)
            elif 118 < y < 220 and 70 < x < width - 70:
                rgb = (223, 238, 255)
            elif 260 < y < 350 and 80 < x < 470:
                rgb = (255, 255, 255)
            elif 260 < y < 350 and 530 < x < 920:
                rgb = (245, 248, 252)
            elif 420 < y < 620 and 90 < x < 610:
                rgb = (247, 207, 87) if (y // 24) % 2 == 0 else (255, 255, 255)
            else:
                rgb = (238, 242, 246)
            row.extend(rgb)
        rows.append(b"\x00" + bytes(row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(b"".join(rows), level=9))
        + png_chunk(b"IEND", b"")
    )


def shared_site_css() -> str:
    return """
    * { box-sizing: border-box; }
    html { background: #eef2f6; scroll-behavior: smooth; }
    body { margin: 0; color: #17202a; font-family: Arial, Helvetica, sans-serif; line-height: 1.45; }
    a { color: inherit; }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 36px;
      color: #fff;
      background: rgba(18, 34, 56, 0.94);
      box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18);
    }
    .topbar nav { display: flex; gap: 18px; font-size: 14px; }
    .fixed-overlay {
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 30;
      max-width: 280px;
      padding: 16px;
      color: #122238;
      background: #fff;
      border: 1px solid #c7d0da;
      box-shadow: 0 12px 34px rgba(0, 0, 0, 0.22);
    }
    main { max-width: 1040px; margin: 0 auto; padding: 44px 28px 120px; }
    .hero { min-height: 420px; display: grid; align-items: center; }
    .hero-card {
      max-width: 720px;
      padding: 36px;
      background: #dfeeff;
      border: 1px solid #a8c5e5;
      animation: settle-nudge 220ms ease-out 1;
    }
    @keyframes settle-nudge {
      from { transform: translateY(20px); opacity: 0.35; }
      to { transform: translateY(0); opacity: 1; }
    }
    section { margin: 0 0 44px; padding: 24px; background: #fff; border: 1px solid #c7d0da; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .card { padding: 20px; background: #f7fafc; border: 1px solid #d8e1ea; }
    .sticky-apply { position: sticky; top: 92px; background: #f7cf57; border-color: #c79a18; }
    .internal-scroll { height: 220px; overflow: auto; border: 3px solid #435269; background: #f9fafb; }
    .internal-scroll-content {
      min-height: 780px;
      padding: 20px;
      background: repeating-linear-gradient(180deg, #fff 0 54px, #e8eef5 54px 108px);
    }
    .shadow-host-shell { padding: 16px; border: 1px dashed #8294a6; background: #f3f7fb; }
    .spacer { min-height: 760px; padding: 32px; background: linear-gradient(180deg, #eef2f6, #dce6f1); }
    """


def site_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{title}</title>
  <style>{shared_site_css()}</style>
</head>
<body>
  <header class="topbar" data-capture-sticky>
    <strong>Acme Robotics Careers</strong>
    <nav>
      <a href="index.html">Careers</a>
      <a href="roles.html">Roles</a>
      <a href="culture.html">Culture</a>
    </nav>
  </header>
  <aside class="fixed-overlay" data-capture-overlay>
    Chat with recruiting. This overlay should be hidden and restored by capture scripts.
  </aside>
  {body}
</body>
</html>
"""


def write_mock_site(output_dir: Path) -> None:
    site_dir = output_dir / "site"
    write_text(
        site_dir / "index.html",
        site_page(
            "Acme Robotics Careers",
            """<main>
  <section class="hero">
    <div class="hero-card" id="animated-card">
      <h1>Build robots that work beside people.</h1>
      <p>Acme Robotics hires engineers, designers, and operators for field-tested autonomy.</p>
    </div>
  </section>
  <section class="grid">
    <div class="card"><h2>Mission</h2><p>Turn complex robotics into dependable worksite systems.</p></div>
    <div class="card"><h2>Benefits</h2><p>Deep work blocks, lab access, field stipends, and transparent leveling.</p></div>
  </section>
  <div class="spacer">Tall careers page content for full-page capture.</div>
</main>""",
        ),
    )
    write_text(
        site_dir / "roles.html",
        site_page(
            "Acme Robotics Roles",
            """<main>
  <section class="grid">
    <div>
      <h1>Open roles</h1>
      <div class="card">Senior Robotics Engineer</div>
      <div class="card">Perception Systems Lead</div>
      <div class="card">Field Reliability Engineer</div>
    </div>
    <aside class="card sticky-apply" id="context-target">
      <h2>Apply with context</h2>
      <p>Our process includes a portfolio screen, technical work sample, and onsite systems review.</p>
    </aside>
  </section>
  <section>
    <h2>Role detail scroller</h2>
    <div class="internal-scroll" id="internal-scroll">
      <div class="internal-scroll-content">
        <h3>Senior Robotics Engineer</h3>
        <p>Top: own planning, controls, and simulation loops.</p>
        <p style="margin-top: 260px;">Middle: collaborate with field operators and product engineering.</p>
        <p style="margin-top: 260px;">Bottom: publish reliability notes and mentor systems engineers.</p>
      </div>
    </div>
  </section>
</main>""",
        ),
    )
    write_text(
        site_dir / "culture.html",
        site_page(
            "Acme Robotics Culture",
            """<main>
  <section>
    <h1>Engineering culture</h1>
    <p>Teams write field notes, share failure reviews, and rotate through customer deployments.</p>
    <div class="shadow-host-shell">
      <employee-proof id="employee-proof"></employee-proof>
    </div>
  </section>
  <section id="trim-target">
    <h2>Operating principles</h2>
    <p>Prototype in simulation, validate in the lab, and learn in the field.</p>
  </section>
  <script>
    customElements.define('employee-proof', class extends HTMLElement {
      connectedCallback() {
        const root = this.attachShadow({ mode: 'open' });
        root.innerHTML = `
          <style>
            blockquote { margin: 0; padding: 18px; background: #153c2f; color: white; }
            cite { display: block; margin-top: 8px; color: #b9ead8; }
          </style>
          <blockquote>
            "The best part is watching a field bug become next week's reliability win."
            <cite>Principal autonomy engineer</cite>
          </blockquote>`;
      }
    });
  </script>
</main>""",
        ),
    )


def report_markdown() -> str:
    return """# Acme Robotics Employer Brand Audit

## Executive Readout

Acme Robotics presents a credible engineering story, but the careers page asks
candidates to infer too much about team practices, hiring criteria, and growth.
The strongest next move is to connect technical ambition to concrete employee
proof.

```mermaid
flowchart TD
  intake[Intake inputs] --> urls[L0 URL discovery]
  urls --> capture[L1 text and screenshot capture]
  capture --> kilos[L2 KILOS analysis]
  kilos --> synth[L3 synthesis]
  synth --> report[L4 report]
```

## Findings

- The mission is clear, but candidate outcomes are vague.
- The page has visual proof, yet few proof points from employees.
- Engineering role copy should expose interview stages and decision criteria.

## Recommended Edits

1. Add one engineering-team proof block near the top of the careers page.
2. Publish a short interview-process explainer linked from every technical role.
3. Tie benefits language to robotics-specific working rhythms and learning loops.
"""


def analysis_markdown() -> str:
    return """# KILOS Analysis

| Dimension | Signal | Evidence |
| --- | --- | --- |
| Knowledge | Medium | Robotics mission is explicit, technical practices are thin. |
| Identity | Strong | Product category and company voice are easy to understand. |
| Logistics | Weak | Interview stages and location expectations are not surfaced. |
| Opportunity | Medium | Growth story exists but lacks role-level examples. |
| Social Proof | Weak | Few employee-authored or team-authored proof points. |
"""


def build_manifest(output_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": "adr-002.audit-manifest.v1",
        "audit_id": "easy-audit-acme-robotics",
        "company": "Acme Robotics",
        "domain": "acme.example",
        "template_id": "employer-brand-audit.easy",
        "talent_segment": "Senior robotics engineers",
        "status": "complete",
        "created_at": "2026-06-13T01:00:00Z",
        "required_inputs": [
            {"id": "company", "label": "Company", "value": "Acme Robotics"},
            {"id": "domain", "label": "Domain", "value": "acme.example"},
            {
                "id": "talent_segment",
                "label": "Talent segment",
                "value": "Senior robotics engineers",
            },
        ],
        "mock_site": {
            "pages": MOCK_SITE_PAGES,
            "capture_features": CAPTURE_FEATURES,
            "purpose": "deterministic local careers site for Playwright capture pipeline coverage",
        },
        "steps": [
            {
                "id": "l0-url-discovery",
                "layer": 0,
                "name": "L0 URL discovery",
                "description": "Collect public source URLs for the audit.",
                "status": "complete",
                "started_at": "2026-06-13T01:00:00Z",
                "completed_at": "2026-06-13T01:01:00Z",
                "required_inputs": ["company", "domain"],
                "artifact_ids": ["l0-source-urls"],
                "parent_step_ids": [],
            },
            {
                "id": "l1-source-capture",
                "layer": 1,
                "name": "L1 source capture",
                "description": "Capture text and screenshot evidence from source URLs.",
                "status": "complete",
                "started_at": "2026-06-13T01:01:00Z",
                "completed_at": "2026-06-13T01:03:00Z",
                "required_inputs": [],
                "artifact_ids": ["l1-careers-text", "l1-careers-screenshot"],
                "parent_step_ids": ["l0-url-discovery"],
            },
            {
                "id": "l2-kilos-analysis",
                "layer": 2,
                "name": "L2 KILOS analysis",
                "description": "Score candidate-facing evidence against the KILOS rubric.",
                "status": "complete",
                "started_at": "2026-06-13T01:03:00Z",
                "completed_at": "2026-06-13T01:05:00Z",
                "required_inputs": ["talent_segment"],
                "artifact_ids": ["l2-kilos-json", "l2-kilos-analysis"],
                "parent_step_ids": ["l1-source-capture"],
            },
            {
                "id": "l3-synthesis",
                "layer": 3,
                "name": "L3 synthesis",
                "description": "Summarize strengths, gaps, and recommended message moves.",
                "status": "complete",
                "started_at": "2026-06-13T01:05:00Z",
                "completed_at": "2026-06-13T01:07:00Z",
                "required_inputs": [],
                "artifact_ids": ["l3-synthesis-notes"],
                "parent_step_ids": ["l2-kilos-analysis"],
            },
            {
                "id": "l4-report",
                "layer": 4,
                "name": "L4 report",
                "description": "Render the reviewable audit report with provenance map.",
                "status": "complete",
                "started_at": "2026-06-13T01:07:00Z",
                "completed_at": "2026-06-13T01:09:00Z",
                "required_inputs": [],
                "artifact_ids": ["l4-final-report"],
                "parent_step_ids": ["l3-synthesis"],
            },
        ],
        "artifacts": [
            {
                "id": "l0-source-urls",
                "layer": 0,
                "type": "url_list",
                "status": "complete",
                "created_at": "2026-06-13T01:01:00Z",
                "produced_by_step_id": "l0-url-discovery",
                "parent_ids": [],
                "file_path": "l0-source-urls.json",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Seed source URLs", "tags": {"layer": "L0"}},
            },
            {
                "id": "l1-careers-text",
                "layer": 1,
                "type": "text_capture",
                "status": "complete",
                "created_at": "2026-06-13T01:02:00Z",
                "produced_by_step_id": "l1-source-capture",
                "parent_ids": ["l0-source-urls"],
                "file_path": "l1-careers-text.txt",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Careers page text", "tags": {"layer": "L1"}},
            },
            {
                "id": "l1-careers-screenshot",
                "layer": 1,
                "type": "screenshot",
                "status": "complete",
                "created_at": "2026-06-13T01:03:00Z",
                "produced_by_step_id": "l1-source-capture",
                "parent_ids": ["l0-source-urls"],
                "file_path": "l1-careers-screenshot.png",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Careers page screenshot", "tags": {"layer": "L1"}},
            },
            {
                "id": "l2-kilos-json",
                "layer": 2,
                "type": "kilos_scores",
                "status": "complete",
                "created_at": "2026-06-13T01:04:00Z",
                "produced_by_step_id": "l2-kilos-analysis",
                "parent_ids": ["l1-careers-text", "l1-careers-screenshot"],
                "file_path": "l2-kilos-scores.json",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Structured KILOS scores", "tags": {"layer": "L2"}},
            },
            {
                "id": "l2-kilos-analysis",
                "layer": 2,
                "type": "kilos_analysis",
                "status": "complete",
                "created_at": "2026-06-13T01:05:00Z",
                "produced_by_step_id": "l2-kilos-analysis",
                "parent_ids": ["l2-kilos-json"],
                "file_path": "l2-kilos-analysis.md",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Readable KILOS analysis", "tags": {"layer": "L2"}},
            },
            {
                "id": "l3-synthesis-notes",
                "layer": 3,
                "type": "synthesis_notes",
                "status": "complete",
                "created_at": "2026-06-13T01:07:00Z",
                "produced_by_step_id": "l3-synthesis",
                "parent_ids": ["l2-kilos-analysis"],
                "file_path": "l3-synthesis-notes.txt",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Synthesis notes", "tags": {"layer": "L3"}},
            },
            {
                "id": "l4-final-report",
                "layer": 4,
                "type": "report",
                "status": "complete",
                "created_at": "2026-06-13T01:09:00Z",
                "produced_by_step_id": "l4-report",
                "parent_ids": ["l3-synthesis-notes", "l1-careers-screenshot"],
                "file_path": "l4-final-report.md",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Final employer brand audit", "tags": {"layer": "L4"}},
            },
        ],
    }


def generate_easy_audit_fixture(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "l0-source-urls.json",
        [
            {"url": "https://acme.example/careers", "role": "careers_home"},
            {"url": "https://acme.example/jobs/robotics-engineer", "role": "job_posting"},
        ],
    )
    write_text(
        output_dir / "l1-careers-text.txt",
        "Build autonomous systems with Acme Robotics. Benefits, mission, and roles are visible; interview process proof is missing.\n",
    )
    write_mock_site(output_dir)
    (output_dir / "l1-careers-screenshot.png").write_bytes(mock_capture_png())
    write_json(
        output_dir / "l2-kilos-scores.json",
        {
            "knowledge": 3,
            "identity": 4,
            "logistics": 2,
            "opportunity": 3,
            "social_proof": 2,
        },
    )
    write_text(output_dir / "l2-kilos-analysis.md", analysis_markdown())
    write_text(
        output_dir / "l3-synthesis-notes.txt",
        "Strong mission and category clarity. Main gap: candidates need concrete proof of hiring process, team practices, and growth paths.\n",
    )
    write_text(output_dir / "l4-final-report.md", report_markdown())
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, build_manifest(output_dir))
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will receive manifest.json and mock artifacts.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = generate_easy_audit_fixture(args.output_dir)
    payload = {
        "status": "generated",
        "fixture": "easy-audit",
        "manifest": repo_relative(manifest_path),
        "artifact_root": repo_relative(manifest_path.parent),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Generated easy-audit fixture: {payload['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
