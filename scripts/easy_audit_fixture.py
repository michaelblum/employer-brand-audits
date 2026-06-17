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
INTAKE_FLOW_STEP_SELECTOR_CANDIDATES = [
    '[data-workflow-step-id="l0-seed-intake"]',
    'g.node[data-node="true"][data-id="intake"]',
]


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def intake_flow_input_anchor() -> dict[str, Any]:
    return {
        "artifact_id": "l0-intake-flow",
        "selector_candidates": INTAKE_FLOW_STEP_SELECTOR_CANDIDATES,
    }


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
    .brand-mark { display: inline-flex; align-items: center; gap: 10px; }
    .brand-icon {
      width: 30px;
      height: 30px;
      display: inline-grid;
      place-items: center;
      border-radius: 8px;
      color: #122238;
      background: #f7cf57;
      font-weight: 800;
    }
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
    .cta-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
    .cta-row a {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border: 1px solid #8294a6;
      background: #fff;
      text-decoration: none;
      font-weight: 700;
    }
    .progress-card { margin-top: 24px; padding: 18px; background: #fff; border: 1px solid #a8c5e5; }
    .progress-shell { height: 22px; overflow: hidden; border: 1px solid #26364a; background: #dbe4ee; }
    .progress-fill {
      width: 0%;
      height: 100%;
      background: linear-gradient(90deg, #1d7a52, #55c88a);
      animation: progress-fill 3s linear forwards;
    }
    @keyframes settle-nudge {
      from { transform: translateY(20px); opacity: 0.35; }
      to { transform: translateY(0); opacity: 1; }
    }
    @keyframes progress-fill {
      from { width: 0%; }
      to { width: 100%; }
    }
    section { margin: 0 0 44px; padding: 24px; background: #fff; border: 1px solid #c7d0da; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .card { padding: 20px; background: #f7fafc; border: 1px solid #d8e1ea; }
    .jobs-modal {
      margin: 0 0 44px;
      border: 1px solid #435269;
      background: #fff;
      box-shadow: 0 16px 34px rgba(18, 34, 56, 0.18);
    }
    .jobs-modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 22px;
      color: #fff;
      background: #26364a;
    }
    .jobs-modal-scroll {
      max-height: 340px;
      overflow: auto;
      padding: 22px;
    }
    .role-list { display: grid; gap: 16px; }
    .role-card {
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr);
      gap: 14px;
      padding: 16px;
      border: 1px solid #d8e1ea;
      background: #f7fafc;
    }
    .role-icon {
      width: 42px;
      height: 42px;
      display: inline-grid;
      place-items: center;
      border-radius: 999px;
      color: #fff;
      background: #1d4d7a;
      font-size: 12px;
      font-weight: 800;
    }
    .role-card h3 { margin: 0 0 6px; }
    .role-card p { margin: 0 0 8px; }
    .role-card a { color: #164f8f; font-weight: 700; }
    .sticky-apply { position: sticky; top: 92px; background: #f7cf57; border-color: #c79a18; }
    .sticky-obscured-target {
      scroll-margin-top: 0;
      margin-top: 720px;
      border: 4px solid #d14b35;
      background: #fff1ee;
    }
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
    <strong class="brand-mark"><span class="brand-icon">AR</span><span>Acme Robotics Careers</span></strong>
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
      <p>Acme Robotics hires engineers, designers, and field operators to build dependable autonomy for worksites, warehouses, and remote inspection teams.</p>
      <div class="cta-row">
        <a href="roles.html#principal-robotics-engineer"><span aria-hidden="true">ER</span><span>Principal Robotics Engineer</span></a>
        <a href="culture.html#employee-proof"><span aria-hidden="true">EP</span><span>Employee proof</span></a>
        <a href="roles.html#interview-plan"><span aria-hidden="true">IP</span><span>Interview plan</span></a>
      </div>
      <div class="progress-card" id="animation-progress">
        <h2>Capture animation diagnostic</h2>
        <p>The fill below animates from left to right over three seconds. A settled capture should show the bar filled.</p>
        <div class="progress-shell" aria-label="Three second progress bar">
          <div class="progress-fill"></div>
        </div>
      </div>
    </div>
  </section>
  <div class="jobs-modal" role="dialog" aria-label="Featured engineering roles">
    <div class="jobs-modal-header">
      <strong>Featured roles</strong>
      <span>Scrollable modal content</span>
    </div>
    <div class="jobs-modal-scroll" id="jobs-modal-scroll">
      <div class="role-list">
        <article class="role-card" id="principal-robotics-engineer">
          <span class="role-icon" aria-hidden="true">PR</span>
          <div>
            <h3>Principal Robotics Engineer</h3>
            <p>Own motion planning and reliability loops for robot fleets deployed in active customer sites.</p>
            <a href="roles.html#principal-robotics-engineer">Read the role profile</a>
          </div>
        </article>
        <article class="role-card">
          <span class="role-icon" aria-hidden="true">PX</span>
          <div>
            <h3>Perception Systems Lead</h3>
            <p>Lead sensor fusion, dataset review, and field-debugging tools for mixed indoor and outdoor environments.</p>
            <a href="roles.html#interview-plan">See interview plan</a>
          </div>
        </article>
        <article class="role-card">
          <span class="role-icon" aria-hidden="true">FR</span>
          <div>
            <h3>Field Reliability Engineer</h3>
            <p>Turn deployment incidents into repeatable tests, service guidance, and product-quality improvements.</p>
            <a href="culture.html">Explore team culture</a>
          </div>
        </article>
        <article class="role-card">
          <span class="role-icon" aria-hidden="true">DS</span>
          <div>
            <h3>Developer Systems Engineer</h3>
            <p>Build simulation workflows, trace viewers, and release diagnostics that shorten robot-debug cycles.</p>
            <a href="roles.html">View all open roles</a>
          </div>
        </article>
      </div>
    </div>
  </div>
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
      <div class="card" id="principal-robotics-engineer"><h2>Principal Robotics Engineer</h2><p>Lead planning, controls, and simulation contracts for production robot fleets.</p><a href="index.html#jobs-modal-scroll">Compare role highlights</a></div>
      <div class="card"><h2>Perception Systems Lead</h2><p>Design sensor review loops and model-quality gates with the autonomy platform team.</p></div>
      <div class="card"><h2>Field Reliability Engineer</h2><p>Own deployment feedback, field triage, and reliability playbooks.</p></div>
    </div>
    <aside class="card sticky-apply" id="context-target">
      <h2>Apply with context</h2>
      <p>Our process includes a portfolio screen, technical work sample, and onsite systems review.</p>
    </aside>
  </section>
  <section class="card" id="interview-plan">
    <h2>Interview plan</h2>
    <p>Step 1: recruiter context call. Step 2: technical systems discussion. Step 3: paid work sample. Step 4: onsite field-readiness review.</p>
  </section>
  <section class="sticky-obscured-target" id="sticky-obscured-target">
    <h2>Sticky header overlap diagnostic</h2>
    <p>This target intentionally has no scroll margin. When capture scrolls directly to it, the sticky header should partially cover the top edge unless the capture script compensates.</p>
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


def intake_flow_markdown() -> str:
    return """# Employer Brand Audit Intake

```mermaid
flowchart TD
  intake[Seed intake<br/>company · domain hint · template · talent segment]
  seeds[L0 seed entry points<br/>domain and platform roots]
  targets[Navigated capture targets<br/>pages and sections found by Playwright traversal]
  evidence[L1 captured evidence<br/>text · screenshots · clips]
  kilos[L2 KILOS analysis]
  synth[L3 synthesis]
  report[L4 report]

  intake --> seeds
  seeds --> targets
  targets --> evidence
  evidence --> kilos
  kilos --> synth
  synth --> report
```

## Intake Inputs

- Company
- Domain or inferred-domain hint
- Workflow template
- Talent segment or scope
"""


def report_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acme Robotics Employer Brand Audit</title>
  <style>
    body { margin: 0; color: #17202a; background: #f8fafc; font-family: Arial, Helvetica, sans-serif; line-height: 1.5; }
    main { max-width: 880px; margin: 0 auto; padding: 44px 28px 80px; }
    header, section { margin-bottom: 24px; padding: 24px; border: 1px solid #cbd5e1; background: #fff; }
    h1, h2 { margin-top: 0; }
    .finding-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .finding-card { padding: 14px; border: 1px solid #d8e1ea; background: #f1f5f9; }
    .cta { display: inline-flex; margin-top: 10px; padding: 10px 14px; background: #164f8f; color: #fff; text-decoration: none; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <header id="executive-readout">
      <p>Employer Brand Audit</p>
      <h1>Acme Robotics</h1>
      <p>Acme Robotics presents a credible engineering story, but the careers page asks candidates to infer too much about team practices, hiring criteria, and growth.</p>
      <a id="apply-context" class="cta primary" role="button" href="https://acme.example/careers">Review careers page CTA</a>
    </header>
    <section id="findings">
      <h2>Findings</h2>
      <div class="finding-grid">
        <article class="finding-card" id="mission-signal"><h3>Mission</h3><p>Clear robotics mission and category fit.</p></article>
        <article class="finding-card" id="process-gap"><h3>Process</h3><p>Interview stages and decision criteria need proof.</p></article>
        <article class="finding-card" id="employee-proof"><h3>Proof</h3><p>Employee-authored examples would make the story concrete.</p></article>
      </div>
    </section>
    <section id="recommended-edits">
      <h2>Recommended edits</h2>
      <ol>
        <li>Add one engineering-team proof block near the top of the careers page.</li>
        <li>Publish a short interview-process explainer linked from every technical role.</li>
        <li>Tie benefits language to robotics-specific working rhythms and learning loops.</li>
      </ol>
    </section>
  </main>
</body>
</html>
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
            {"id": "domain_hint", "label": "Domain or inferred-domain hint", "value": "acme.example"},
            {"id": "workflow_template", "label": "Workflow template", "value": "standard-audit"},
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
                "id": "l0-seed-intake",
                "layer": 0,
                "name": "L0 seed intake",
                "description": (
                    "Collect seed-level audit inputs. The agent uses these inputs to browse "
                    "entry points and discover concrete capture targets."
                ),
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "required_inputs": [
                    {
                        "id": "company",
                        "label": "Company",
                        "status": "pending",
                        "value": None,
                        "input_type": "text",
                        "placeholder": "Acme Robotics",
                        "anchor": intake_flow_input_anchor(),
                    },
                    {
                        "id": "domain_hint",
                        "label": "Domain or inferred-domain hint",
                        "status": "pending",
                        "value": None,
                        "input_type": "text",
                        "placeholder": "acme.example",
                        "anchor": intake_flow_input_anchor(),
                    },
                    {
                        "id": "workflow_template",
                        "label": "Workflow template",
                        "status": "pending",
                        "value": "standard-audit",
                        "input_type": "select",
                        "options": [
                            {"value": "standard-audit", "label": "Standard audit"},
                            {"value": "tech-talent-audit", "label": "Tech talent audit"},
                        ],
                        "anchor": intake_flow_input_anchor(),
                    },
                    {
                        "id": "talent_segment",
                        "label": "Talent segment or scope",
                        "status": "pending",
                        "value": None,
                        "input_type": "text",
                        "placeholder": "Senior robotics engineers",
                        "anchor": intake_flow_input_anchor(),
                    },
                ],
                "artifact_ids": ["l0-intake-flow"],
                "parent_step_ids": [],
            },
            {
                "id": "l0-url-discovery",
                "layer": 0,
                "name": "L0 URL discovery",
                "description": (
                    "Browse seed entry points to discover concrete pages and sections for capture."
                ),
                "status": "complete",
                "started_at": "2026-06-13T01:00:00Z",
                "completed_at": "2026-06-13T01:01:00Z",
                "required_inputs": ["company", "domain"],
                "artifact_ids": ["l0-source-urls"],
                "parent_step_ids": ["l0-seed-intake"],
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
                "description": "Render the workbench-visible audit report with provenance map.",
                "status": "complete",
                "started_at": "2026-06-13T01:07:00Z",
                "completed_at": "2026-06-13T01:09:00Z",
                "required_inputs": [],
                "artifact_ids": ["l4-final-report", "l4-final-report-html"],
                "parent_step_ids": ["l3-synthesis"],
            },
        ],
        "artifacts": [
            {
                "id": "l0-intake-flow",
                "layer": 0,
                "type": "intake_flow",
                "status": "pending",
                "created_at": "2026-06-13T00:59:00Z",
                "produced_by_step_id": "l0-seed-intake",
                "parent_ids": [],
                "file_path": "l0-intake-flow.md",
                "params": {"slot": "intake.flow"},
                "card": {
                    "summary": "Fixture-backed intake flow with bounded seed input overlays",
                    "tags": {"layer": "L0", "slot": "intake.flow"},
                },
            },
            {
                "id": "l0-source-urls",
                "layer": 0,
                "type": "url_list",
                "status": "complete",
                "created_at": "2026-06-13T01:01:00Z",
                "produced_by_step_id": "l0-url-discovery",
                "parent_ids": ["l0-intake-flow"],
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
            {
                "id": "l4-final-report-html",
                "layer": 4,
                "type": "html",
                "status": "complete",
                "created_at": "2026-06-13T01:09:30Z",
                "produced_by_step_id": "l4-report",
                "parent_ids": ["l4-final-report", "l3-synthesis-notes"],
                "file_path": "l4-final-report.html",
                "params": {"url": "https://acme.example/careers"},
                "card": {"summary": "Final employer brand audit HTML", "tags": {"layer": "L4"}},
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
    write_text(output_dir / "l0-intake-flow.md", intake_flow_markdown())
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
    write_text(output_dir / "l4-final-report.html", report_html())
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
