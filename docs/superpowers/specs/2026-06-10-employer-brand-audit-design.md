# Employer Brand Audit Tool — Design Spec

**Date:** 2026-06-10  
**Status:** Approved for implementation  
**Author:** Michael Blum / Symphony Talent  

---

## Overview

An AI-powered employer brand audit tool delivered as a Claude Cowork plugin. The system collects a company's public employer brand footprint, analyzes it against Symphony Talent's KILOS framework, and produces a structured audit report. The primary artifact is an L4 HTML report suitable for internal review and client delivery.

The tool is designed for non-technical Symphony Talent staff operating within Claude Cowork on macOS (and eventually Windows). No developer setup is required beyond plugin installation.

---

## Architecture

Three components, each with a single clear responsibility:

| Component | Role |
|---|---|
| **Cowork Skill** | Conversational orchestrator. Intake wizard, workflow routing, layer handoffs, report delivery. |
| **Claude in Chrome** | Browser layer. URL discovery, text extraction, full-page screenshots, all in the user's real Chrome with real sessions/cookies. |
| **Python MCP Server** | Heavy lifting. Image stitching/cropping, KILOS analysis, manifest management, Google Drive sync, L4 report generation. |

**Why Claude in Chrome over Playwright/headless:** The target sites (Indeed, Glassdoor, LinkedIn, Kununu) actively detect headless automation. Claude in Chrome uses the user's real Chrome browser with their existing fingerprint and session cookies — indistinguishable from a legitimate user visit. No distribution problem (the extension is already installed). No captcha risk. See [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md) and [Issue #1](https://github.com/michaelblum/employer-brand-audits/issues/1) (Playwright headless fallback, deferred to V1.1).

**Why Python over Node:** Python ships with macOS. No binary compilation issues, no Node.js install requirement for non-developer users. Pillow handles image stitching natively.

---

## Workflow Configuration

**Option B (selected):** Power users can clone and tweak templates.

A standard template library is maintained by Symphony Talent admins. End users pick a template, answer the intake wizard, and run. Power users (defined by role) can clone a template, adjust sources, toggle KILOS pillars, and save a named variant for reuse.

V1 ships with two templates:

| Template | Sources | Talent scope |
|---|---|---|
| `standard-audit` | Careers page + LinkedIn + Indeed + Glassdoor | All talent |
| `tech-talent-audit` | Careers page + careers/tech subpage + LinkedIn + Indeed | Technology & Product |

---

## Layer Model (L0–L5)

The pipeline is organized into layers. Each layer produces artifacts consumed by the next. All artifacts are tracked in the audit manifest with full provenance.

### L0 — URL Discovery

**Input:** Company name, domain (or guessed from company name), workflow template.  
**Process:** Claude in Chrome navigates the company's careers site and known platforms (LinkedIn, Indeed, Glassdoor) to discover and enumerate target URLs.  
**Output:** Ranked URL list with source type tags (`careers-main`, `careers-subpage`, `linkedin-jobs`, `indeed-company`, `glassdoor-company`, etc.)  
**Artifacts:** `l0-urls.json`

### L1 — Text and Screenshot Capture

**Input:** L0 URL list.  
**Process:** For each URL, Claude in Chrome runs two capture passes:

1. **Text pass:** `get_page_text` + DRAW `extractSimpleText` injected via `javascript_tool`. Output: clean markdown.
2. **Screenshot pass:** DRAW `scroll_active_element` + `_waitForAnimations` + `_hideObscuringElements` injected via `javascript_tool`, triggering the scroll-and-stitch pipeline (Pillow port of `clipUtils.stitchImagesWithOverlap`). Output: full-page PNG at ≤2000px height.

**Capture recipes** are defined per source type in the workflow template. Each recipe captures intent, not implementation (e.g., "full-page scan of careers landing page, hiding chat widgets and cookie banners"). The agent can re-derive the approach from the intent description if the DOM changes (intent-addressable automation, per [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md)).

Additional recipe types:
- `review_clip` — screenshot of a specific element (e.g., a Glassdoor rating widget), with crop coordinates
- `animated_widget` — screenshot taken at the settled frame of an animation (uses `_waitForAnimations`)

**Output:** Per-URL `{url_id}-text.md` and `{url_id}-screenshot.png`, stored in the audit directory.  
**Artifacts:** `l1-{url_id}-text`, `l1-{url_id}-screenshot`

### L2 — KILOS Analysis and Image Crops

**Input:** L1 text + screenshot artifacts for a given URL.  
**Process:** The Python MCP `run_kilos_analysis` tool calls Claude (claude-opus-4-8 or claude-sonnet-4-6) with the page text, page screenshot, and KILOS reference schema. The prompt asks the model to assess each of the 29 KILOS factors across 5 pillars (K1–K5, I1–I6, L1–L7, O1–O6, S1–S5).

Per-factor output:
- `status`: `present` | `absent`
- `evidence`: 1–2 quotes from page text, or image descriptions where text is absent
- `source_url`: canonical URL
- `snapshot_date`: ISO date

Per-page output (in addition to factors):
- `tone`: `human` | `formal`
- `layout`: `modern` | `dated`
- `content_type`: `dynamic` | `static`
- `talent_segment_specific`: `true` | `false` + supporting quote

Image crops: where evidence points to a specific visual element (e.g., a hero image, a benefits section), the Python MCP `crop_image` tool extracts that region from the full-page screenshot.

**Output:** `l2-{url_id}-kilos.json`, `l2-{url_id}-crop-{n}.png`

### L3 — Synthesis JSON with Provenance

**Input:** All L2 KILOS analysis files for the company.  
**Process:** Python MCP `synthesise_l3` aggregates across all sources:

- **Factor strength** promoted from binary to `strong` | `present` | `absent` based on recurrence and prominence across sources
- **Brand positioning statement** — one-sentence distillation of how the company presents itself as an employer
- **Tone/layout/content** — modal values across all sources
- **Strengths** (2–3) — factors where the company performs distinctively well, labeled `strength` or `differentiator`
- **Gaps** (2–3) — absent or underweight factors that represent an opportunity, labeled `opportunity` with a `gap_description`
- **Talent segment coverage** — whether target talent segments are explicitly addressed

Every field in the L3 JSON carries `source_artifact_ids[]` and `source_url` for provenance. Citations in the L4 report link directly to the source URL with a snapshot date disclaimer.

**Output:** `l3-synthesis.json`  
**Synced to:** Google Drive (audit folder)

### L4 — HTML SPA Report

**Input:** `l3-synthesis.json`, L2 crop images (Drive IDs), L1 screenshots (Drive IDs).  
**Process:** Python MCP `generate_report` renders a Jinja2 template into a self-contained HTML file.

Report sections:
1. **Cover** — company name, audit date, talent segment scope
2. **Brand positioning** — one-sentence statement with supporting quote
3. **Creative execution** — tone / layout / content-type assessment with screenshot evidence
4. **KILOS heat map** — 29-factor grid showing `strong` / `present` / `absent` per source (columns = sources, rows = factors, grouped by pillar)
5. **Strengths and differentiators** — 2–3 labeled narrative blocks
6. **Gaps and opportunities** — 2–3 labeled narrative blocks with specific evidence
7. **Source evidence** — per-source section with embedded screenshot (via `lh3.googleusercontent.com/d/{fileId}`) and key factor presence

Images are embedded using the `lh3.googleusercontent.com/d/{fileId}` pattern (Drive-hosted, no base64 bloat). Citations include source URL as a clickable link with snapshot date.

Report visual design is V1 functional/minimal. See [Issue #3](https://github.com/michaelblum/employer-brand-audits/issues/3) for V1.1 visual polish using the Symphony Talent publications kit.

**Output:** `l4-report-{company_slug}.html`  
**Synced to:** Google Drive (audit folder)  
**Delivered:** Opened in Claude Code preview panel at end of run.

### L5 — Comparative Meta-Analysis (future)

Not in V1. After three or more L3 audits exist in the same sector, an L5 run aggregates them into a comparative KILOS heat map (companies × factors), brand positioning map, and market trend assessment — equivalent to the full ADT Comp Audit format. Deferred until at least one L3 audit exists as a POC.

---

## KILOS Analytical Procedure

KILOS reference data is stored in [`data/kilos-framework.json`](../../../data/kilos-framework.json).

**29 factors across 5 pillars:**

| Pillar | Factors |
|---|---|
| **K — Kinship** | K1 Diverse & Inclusive, K2 Wellbeing, K3 Safe to Voice Opinions, K4 Fairness & Respect, K5 Sense of Belonging |
| **I — Impact** | I1 Meaningful Work for People, I2 Meaningful Work for Planet, I3 Empowerment/Autonomy, I4 Influence Strategy, I5 Impact on Big Scale, I6 Innovation & Invention |
| **L — Lifestyle** | L1 Good Benefits, L2 Work Environment, L3 Policies, L4 Flexibility (Hours), L5 Flexibility (Location), L6 Balance, L7 Stability |
| **O — Opportunity** | O1 Skills Attainment, O2 Professional Expertise, O3 Challenge & Stretch, O4 Career Mobility, O5 Task Variety, O6 Career Progression |
| **S — Status** | S1 Brand Name Recognition, S2 Industry Reputation, S3 Tools & Technologies, S4 Market Position, S5 Professional Reputation |

**L2 prompt contract:** The model receives: page markdown text + page screenshot + the full `kilos-framework.json` (factors with descriptions and survey labels). It is asked to assess each factor as `present` or `absent`, provide 1–2 evidence items per present factor, and assess tone/layout/content-type. Output is validated against a JSON schema before being written to disk. Default model: `claude-sonnet-4-6`.

**L3 strength promotion logic:**
- `strong` — factor is `present` in 3+ sources, OR present in 1–2 sources with prominent evidence (headline-level copy, hero image)
- `present` — factor is `present` in 1–2 sources with body-level evidence
- `absent` — factor appears in no source

---

## Python MCP Tool Surface

All tools are exposed via stdio MCP. The server lives at `mcp-server/server.py` inside the plugin.

| Tool | Inputs | Outputs | Notes |
|---|---|---|---|
| `create_audit` | company_name, domain, template_id, talent_segment? | audit_id, manifest path | Creates audit directory + manifest |
| `get_audit_status` | audit_id | step statuses, artifact counts | Read-only manifest query |
| `save_artifact` | audit_id, layer, type, file_path, parent_ids[], params{} | artifact_id | Writes artifact record to manifest |
| `stitch_images` | image_base64_list[], client_height, device_pixel_ratio | full_page_base64 | Pillow port of clipUtils.stitchImagesWithOverlap |
| `crop_image` | full_page_base64, rect{x,y,w,h}, device_pixel_ratio | crop_base64 | Pillow port of clipUtils.cropToElement |
| `upload_to_drive` | file_path, parent_folder_id, mime_type? | drive_file_id, view_url | Drive API via service account |
| `run_kilos_analysis` | audit_id, url_id, text_path, screenshot_path | l2_artifact_id | Calls Claude API, writes l2-{url_id}-kilos.json |
| `synthesise_l3` | audit_id | l3_artifact_id | Aggregates all L2 JSONs, writes l3-synthesis.json |
| `generate_report` | audit_id | l4_artifact_id, report_path | Renders Jinja2 template, writes HTML |
| `set_step_status` | audit_id, step_id, status, error? | — | Manifest step status update for live ops rendering |

---

## Audit Manifest

The manifest is the single source of truth for pipeline state and all UI rendering. See [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md) for the principle. ADR-002 (forthcoming) will specify the full schema; key fields:

```json
{
  "audit_id": "acme-corp-2026-06-10",
  "company": "Acme Corp",
  "template_id": "standard-audit",
  "created_at": "2026-06-10T14:00:00Z",
  "steps": [
    {
      "id": "l0-url-discovery",
      "name": "URL Discovery",
      "description": "Find all careers and employer brand URLs for Acme Corp across careers site, LinkedIn, Indeed, and Glassdoor",
      "status": "pending | running | complete | failed | blocked",
      "started_at": null,
      "completed_at": null,
      "required_inputs": [
        { "id": "company_domain", "label": "Company domain", "status": "pending", "value": null }
      ],
      "artifact_ids": [],
      "parent_step_ids": []
    }
  ],
  "artifacts": [
    {
      "id": "l1-careers-main-text",
      "layer": 1,
      "type": "text",
      "status": "complete",
      "created_at": "2026-06-10T14:05:00Z",
      "parent_ids": ["l0-url-discovery"],
      "params": { "url": "https://careers.acme.com" },
      "file_path": "artifacts/l1-careers-main-text.md"
    }
  ]
}
```

---

## Cowork Plugin Structure

```
employer-brand-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── brand-audit/
│       ├── SKILL.md
│       └── references/
│           ├── kilos-framework.json
│           ├── layer-model.md
│           └── workflow-templates.json
├── mcp-server/
│   ├── server.py
│   └── requirements.txt
├── .mcp.json
└── README.md
```

**plugin.json:**
```json
{
  "name": "employer-brand-audit",
  "version": "0.1.0",
  "description": "AI-powered employer brand audit using the Symphony Talent KILOS framework",
  "author": { "name": "Symphony Talent" }
}
```

**SKILL.md trigger phrases:** "run a brand audit", "audit [company]'s employer brand", "analyze employer brand for [company]", "start an employer brand audit"

**SKILL.md behavior:** Runs the intake wizard (company name, target talent segment, workflow template), then orchestrates L0→L1→L2→L3→L4, updating the manifest at each step, and delivers the L4 report in the preview panel.

**.mcp.json:**
```json
{
  "mcpServers": {
    "employer-brand-audit": {
      "command": "python3",
      "args": ["<plugin_dir>/mcp-server/server.py"]
    }
  }
}
```
Note: exact plugin-dir path variable syntax is implementation-dependent; resolve during plugin build.

**First-run setup:** On first skill invocation, the skill checks for Python 3 and runs `pip install -r requirements.txt` (Pillow, jinja2, markdown) if not already installed. No Node.js required. No user-facing install steps beyond plugin installation.

---

## Google Drive Integration

All audits sync to a shared Google Drive folder structure:

```
Symphony Talent Audits/
└── {company_slug}-{date}/
    ├── artifacts/
    │   ├── l1-*.md
    │   ├── l1-*.png
    │   ├── l2-*-kilos.json
    │   ├── l2-*-crop-*.png
    │   └── l3-synthesis.json
    └── l4-report-{company_slug}.html
```

Images are uploaded to Drive and referenced in the L4 report via `lh3.googleusercontent.com/d/{fileId}` — no base64 embedding, no external CDN, reports work for anyone with Drive access.

---

## Deferred Items

| Item | Issue | Target |
|---|---|---|
| Playwright MCP headless fallback | [#1](https://github.com/michaelblum/employer-brand-audits/issues/1) | V1.1 |
| Browser as collaborative surface (overlays, guided tours) | [#2](https://github.com/michaelblum/employer-brand-audits/issues/2) | V2 |
| L4 report visual design (publications kit) | [#3](https://github.com/michaelblum/employer-brand-audits/issues/3) | V1.1 |
| L5 comparative meta-analysis | — | After V1 POC |
| ADR-002: Full audit manifest schema | — | Early implementation |
| Visual workflow diagram-with-blanks renderer | ADR-001 | V1.1 |
