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
    * { box-sizing: border-box; }
    :root {
      color-scheme: dark;
      --ink: #f4f7fb;
      --muted: #aeb8c7;
      --panel: #111827;
      --panel-2: #172033;
      --line: #344154;
      --blue: #6ea8fe;
      --green: #62d394;
      --amber: #f3c969;
      --coral: #ff8f70;
      --violet: #b8a4ff;
      --paper: #eef2f7;
      --paper-ink: #17202a;
    }
    html { background: #0b0f16; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(110, 168, 254, 0.14), transparent 280px),
        #0b0f16;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 34px 28px 70px;
    }
    h1, h2, h3, p { margin-top: 0; }
    h1 {
      max-width: 820px;
      margin-bottom: 18px;
      font-size: 44px;
      line-height: 1.04;
      letter-spacing: 0;
    }
    h2 { margin-bottom: 16px; font-size: 24px; }
    h3 { margin-bottom: 8px; font-size: 16px; }
    p { color: var(--muted); }
    a { color: inherit; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
      gap: 24px;
      align-items: stretch;
      margin-bottom: 26px;
    }
    .hero-copy,
    .report-card,
    .proof-strip,
    .rewrite-plan,
    .ledger {
      border: 1px solid var(--line);
      background: rgba(17, 24, 39, 0.94);
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.26);
    }
    .hero-copy { padding: 30px; }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 18px;
      color: var(--green);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .eyebrow::before {
      content: "";
      width: 26px;
      height: 2px;
      background: var(--green);
    }
    .dek {
      max-width: 720px;
      margin-bottom: 0;
      color: #d8e0ea;
      font-size: 18px;
    }
    .signal-panel {
      display: grid;
      gap: 14px;
      padding: 22px;
      border: 1px solid #44536a;
      background: #0f1724;
    }
    .signal-meter {
      display: grid;
      gap: 8px;
    }
    .meter-track {
      height: 12px;
      border: 1px solid #506078;
      background: #151e2c;
    }
    .meter-fill {
      display: block;
      width: 61%;
      height: 100%;
      background: linear-gradient(90deg, var(--coral), var(--amber), var(--green));
    }
    .signal-number {
      display: flex;
      align-items: baseline;
      gap: 7px;
      color: var(--ink);
      font-weight: 800;
    }
    .signal-number strong { font-size: 38px; }
    .callout {
      padding: 16px;
      border-left: 4px solid var(--amber);
      background: #1b2434;
      color: #f3f7fb;
    }
    .kilos-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 26px;
    }
    .score-tile {
      min-height: 132px;
      padding: 14px;
      border: 1px solid var(--line);
      background: var(--panel);
    }
    .score-tile strong {
      display: block;
      margin-bottom: 10px;
      color: var(--ink);
      font-size: 13px;
      text-transform: uppercase;
    }
    .score {
      display: inline-grid;
      place-items: center;
      width: 52px;
      height: 52px;
      margin-bottom: 12px;
      border: 2px solid currentColor;
      font-size: 22px;
      font-weight: 800;
    }
    .score.good { color: var(--green); }
    .score.mid { color: var(--amber); }
    .score.low { color: var(--coral); }
    .report-grid {
      display: grid;
      grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
      gap: 18px;
      margin-bottom: 26px;
    }
    .report-card,
    .proof-strip,
    .rewrite-plan,
    .ledger {
      padding: 22px;
    }
    .map {
      display: grid;
      gap: 10px;
    }
    .map-row {
      display: grid;
      grid-template-columns: 104px minmax(0, 1fr);
      gap: 12px;
      align-items: start;
      padding: 12px;
      border: 1px solid #2f3a4c;
      background: #101826;
    }
    .map-row b { color: var(--blue); }
    .map-row:nth-child(2) b { color: var(--amber); }
    .map-row:nth-child(3) b { color: var(--violet); }
    .map-row:nth-child(4) b { color: var(--green); }
    .ledger {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      color: var(--ink);
      font-size: 14px;
    }
    th, td {
      padding: 12px;
      border-bottom: 1px solid #303b4d;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: #d8e0ea;
      background: #111b2a;
      font-size: 12px;
      text-transform: uppercase;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border: 1px solid #4a5870;
      color: #e8edf5;
      background: #182235;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .tag.fix { border-color: rgba(98, 211, 148, 0.65); color: #b9f4ce; }
    .tag.risk { border-color: rgba(255, 143, 112, 0.7); color: #ffd2c6; }
    .rewrite-plan ol {
      display: grid;
      gap: 12px;
      margin: 0;
      padding-left: 24px;
    }
    .rewrite-plan li {
      padding-left: 4px;
      color: #d8e0ea;
    }
    .proof-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 26px;
      background: #121a29;
    }
    .proof-strip article {
      padding: 16px;
      border: 1px solid #334052;
      background: #0f1724;
    }
    .proof-strip span {
      display: block;
      margin-bottom: 8px;
      color: var(--amber);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .footer-note {
      color: #8794a8;
      font-size: 13px;
    }
    @media (max-width: 860px) {
      main { padding: 20px 16px 52px; }
      h1 { font-size: 34px; }
      .hero,
      .report-grid,
      .proof-strip {
        grid-template-columns: 1fr;
      }
      .kilos-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 520px) {
      .kilos-grid { grid-template-columns: 1fr; }
      .map-row { grid-template-columns: 1fr; }
      th, td { padding: 10px; }
    }
  </style>
</head>
<body>
  <main data-report-surface="signal-brief">
    <section class="hero" id="executive-readout">
      <header class="hero-copy">
        <span class="eyebrow">Employer brand audit</span>
        <h1>Acme Robotics has a strong mission signal and a thin candidate proof layer.</h1>
        <p class="dek">The careers page sells dependable robotics work, but senior engineers still have to infer how the team operates, how interviews are judged, and what growth looks like after the first deployment cycle.</p>
      </header>
      <aside class="signal-panel" aria-label="KILOS signal">
        <div class="signal-meter">
          <span class="signal-number"><strong>61</strong><span>/100 KILOS signal</span></span>
          <span class="meter-track" aria-hidden="true"><span class="meter-fill"></span></span>
        </div>
        <div class="callout">
          <strong>Best next move:</strong> Add field-engineering proof near the top of the page, then link every technical role to an explicit interview-plan explainer.
        </div>
      </aside>
    </section>

    <section class="kilos-grid" aria-label="KILOS scorecard">
      <article class="score-tile" data-kilos-score="knowledge">
        <strong>Knowledge</strong>
        <span class="score mid">3</span>
        <p>Robotics category is clear; technical practice is implied.</p>
      </article>
      <article class="score-tile" data-kilos-score="identity">
        <strong>Identity</strong>
        <span class="score good">4</span>
        <p>Mission and product direction are easy to recognize.</p>
      </article>
      <article class="score-tile" data-kilos-score="logistics">
        <strong>Logistics</strong>
        <span class="score low">2</span>
        <p>Interview stages and decision criteria are under-explained.</p>
      </article>
      <article class="score-tile" data-kilos-score="opportunity">
        <strong>Opportunity</strong>
        <span class="score mid">3</span>
        <p>Growth promise exists but needs role-level examples.</p>
      </article>
      <article class="score-tile" data-kilos-score="social-proof">
        <strong>Social proof</strong>
        <span class="score low">2</span>
        <p>Employee-authored evidence is the biggest credibility gap.</p>
      </article>
    </section>

    <section class="report-grid">
      <article class="report-card">
        <h2>Candidate journey repair map</h2>
        <div class="map" aria-label="Candidate journey">
          <div class="map-row"><b>Arrives</b><span>Understands the mission quickly: robots working beside people in real customer environments.</span></div>
          <div class="map-row"><b>Evaluates</b><span>Wants to know the engineering loop: simulation, lab validation, field feedback, incident learning.</span></div>
          <div class="map-row"><b>Decides</b><span>Needs interview transparency and proof that senior engineers can do high-leverage systems work.</span></div>
          <div class="map-row"><b>Commits</b><span>Needs a crisp picture of autonomy ownership, field exposure, and promotion expectations.</span></div>
        </div>
      </article>
      <article class="rewrite-plan">
        <h2>Rewrite sprint</h2>
        <ol>
          <li>Add an engineering proof strip above the role list with one field failure review, one simulation artifact, and one deployment metric.</li>
          <li>Convert the interview plan into a stable page section and link it from every technical role.</li>
          <li>Replace generic benefits language with robotics-specific working rhythms: lab days, field rotations, reliability reviews, and deep-work blocks.</li>
          <li>Give senior candidates one named ownership promise: the systems loop they will own in their first 90 days.</li>
        </ol>
      </article>
    </section>

    <section class="ledger" id="candidate-signal-ledger">
      <h2>Signal ledger</h2>
      <table>
        <thead>
          <tr>
            <th>Signal</th>
            <th>Evidence</th>
            <th>Candidate read</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="tag fix">Mission</span></td>
            <td>Build robots that work beside people.</td>
            <td>Clear category and purpose.</td>
            <td>Keep the line; attach one concrete deployment story.</td>
          </tr>
          <tr>
            <td><span class="tag risk">Hiring</span></td>
            <td>Interview process appears only as broad copy.</td>
            <td>Unclear evaluation bar for senior systems engineers.</td>
            <td>Publish stages, artifacts reviewed, and decision criteria.</td>
          </tr>
          <tr>
            <td><span class="tag risk">Team proof</span></td>
            <td>Few employee-authored examples.</td>
            <td>Culture claims need operational receipts.</td>
            <td>Add field note excerpts and reliability-review examples.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="proof-strip" aria-label="Recommended proof blocks">
      <article>
        <span>Proof block 1</span>
        <h3>From simulation to site</h3>
        <p>Show how a planning bug moves from trace, to lab reproduction, to customer deployment fix.</p>
      </article>
      <article>
        <span>Proof block 2</span>
        <h3>Senior engineering bar</h3>
        <p>Name the systems judgment expected in the technical discussion and paid work sample.</p>
      </article>
      <article>
        <span>Proof block 3</span>
        <h3>Growth loop</h3>
        <p>Explain how engineers progress from owning subsystems to owning fleet reliability outcomes.</p>
      </article>
    </section>

    <p class="footer-note">Source lineage: L0 intake, L1 careers text and screenshot, L2 KILOS analysis, and L3 synthesis notes.</p>
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
        "workbench_context": {
            "artifact_control_policy": "read-only",
            "mermaid_source_visibility": "preview-hidden",
        },
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
                "artifact_ids": ["l4-final-report"],
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
                "file_path": "l4-final-report.html",
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
