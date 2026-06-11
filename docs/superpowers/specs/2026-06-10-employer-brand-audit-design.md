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
| **Cowork Skill** | Conversational orchestrator **and analyst**. Intake wizard, workflow routing, layer handoffs, KILOS assessment (L2) and synthesis (L3) performed inline in the agent loop, Drive sync via the connected Drive MCP, report delivery. |
| **Claude in Chrome** | Browser layer. URL discovery, text extraction, full-page screenshots, all in the user's real Chrome with real sessions/cookies. |
| **Python MCP Server** | Mechanical utilities only. Image stitching/cropping (Pillow), manifest read/write, schema validation, L4 report templating (Jinja2). No model calls, no network credentials. |
| **Connected Google Drive MCP** | Drive file operations (create/copy/read). Already authenticated in the Cowork session — reused, not re-provisioned. |

**Why Claude in Chrome over Playwright/headless:** The target sites (Indeed, Glassdoor, LinkedIn, Kununu) actively detect headless automation. Claude in Chrome uses the user's real Chrome browser with their existing fingerprint and session cookies — indistinguishable from a legitimate user visit. No distribution problem (the extension is already installed). No captcha risk. See [ADR-003](../../decisions/ADR-003-browser-layer.md) and [Issue #1](https://github.com/michaelblum/employer-brand-audits/issues/1) (Playwright headless fallback, deferred to V1.1).

**Why Python over Node:** Python ships with macOS. No binary compilation issues, no Node.js install requirement for non-developer users. Pillow handles image stitching natively.

### Credentials and external access (zero-config premise)

The architecture was chosen specifically to require **no API keys, no service accounts, and no per-user configuration**. This premise constrains where each responsibility lives:

| Capability | Where it runs | Why not the Python MCP server |
|---|---|---|
| Browser automation | Claude in Chrome (host extension) | The server has no browser and no session cookies. |
| KILOS analysis & synthesis (L2/L3) | The orchestrating skill, inline in the agent loop | A bundled MCP server is a separate process with **no inherited model access** — calling Claude would require its own API key and billing. MCP *sampling* (server-requests-host-completion) is host-dependent and historically unsupported in Cowork, and even where available it is pure indirection: the skill already holds the page text and screenshots in context. The analysis stays in the agent loop. |
| Google Drive read/write | Connected Drive MCP | A service account would be a second, conflicting credential mechanism. The session already has an authenticated Drive MCP. |
| Image processing, manifest, templating | Python MCP server | These are local, deterministic, credential-free — exactly what the server is for. |

The Python MCP server is therefore a pure mechanical utility. If a future need requires it to call Claude or reach the network independently, that is a deliberate departure from this premise and warrants its own ADR.

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
2. **Screenshot pass:** DRAW `_waitForAnimations` + `_hideObscuringElements` injected via `javascript_tool` to settle the page, then the agent scrolls and captures viewport tiles using Claude in Chrome's `computer` screenshot with `save_to_disk` (each tile returns a local file path). The Python MCP `stitch_images` tool reads those tile paths from disk and writes a stitched full-page PNG (≤2000px height) — the Pillow port of `clipUtils.stitchImagesWithOverlap` with overlap correction.

**Image handoff is disk-based, by design.** Tiles and stitched output move between Claude in Chrome and the Python server as **file paths on the local disk**, never as multi-MB base64 strings through the agent's tool channel. The agent passes path lists, not pixels. This is the single most important constraint on the L1→L2 image seam.

**Capture recipes** are defined per source type in the workflow template. Each recipe captures intent, not implementation (e.g., "full-page scan of careers landing page, hiding chat widgets and cookie banners"). The agent can re-derive the approach from the intent description if the DOM changes (intent-addressable automation, per [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md)).

Additional recipe types:
- `review_clip` — screenshot of a specific element (e.g., a Glassdoor rating widget), with crop coordinates
- `animated_widget` — screenshot taken at the settled frame of an animation (uses `_waitForAnimations`)

**Output:** Per-URL `{url_id}-text.md` and `{url_id}-screenshot.png`, stored in the audit directory.  
**Artifacts:** `l1-{url_id}-text`, `l1-{url_id}-screenshot`

### L2 — KILOS Analysis and Image Crops

**Input:** L1 text + screenshot artifacts for a given URL.  
**Process:** The **orchestrating skill performs the assessment inline** — it already holds the page markdown and screenshot in context from L1, plus the KILOS reference schema from its `references/` directory. It assesses each of the 29 KILOS factors across 5 pillars (K1–K5, I1–I6, L1–L7, O1–O6, S1–S5) and emits a structured JSON object. It then calls Python MCP `save_artifact` with `validate_schema: "kilos-l2"`, which validates the object against the L2 schema and persists it. (No MCP tool calls Claude — see the credentials table above.)

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

Image crops: where evidence points to a specific visual element (e.g., a hero image, a benefits section), the skill calls Python MCP `crop_image` with the screenshot path and a pixel rect; Pillow extracts the region and writes a crop PNG to disk.

**Output:** `l2-{url_id}-kilos.json`, `l2-{url_id}-crop-{n}.png`

### L3 — Synthesis JSON with Provenance

**Input:** All L2 KILOS analysis files for the company.  
**Process:** The **skill synthesizes inline** — it reads all L2 JSONs (via the manifest) and reasons across them to produce:

- **Factor strength** promoted from binary to `strong` | `present` | `absent` (recurrence + prominence rule below)
- **Brand positioning statement** — one-sentence distillation of how the company presents itself as an employer
- **Tone/layout/content** — modal values across all sources
- **Strengths** (2–3) — factors where the company performs distinctively well, labeled `strength` or `differentiator`
- **Gaps** (2–3) — absent or underweight factors that represent an opportunity, labeled `opportunity` with a `gap_description`
- **Talent segment coverage** — whether target talent segments are explicitly addressed

Strength promotion and modal tone/layout are mechanical and could be precomputed, but the strengths/gaps narratives require judgment — so the whole L3 object is produced by the skill in one pass, then persisted via `save_artifact` with `validate_schema: "l3-synthesis"`.

Every field in the L3 JSON carries `source_artifact_ids[]` and `source_url` for provenance. Citations in the L4 report link directly to the source URL with a snapshot date disclaimer.

**Output:** `l3-synthesis.json`  
**Synced to:** Google Drive (audit folder) via the connected Drive MCP

### L4 — HTML SPA Report

**Input:** `l3-synthesis.json`, L2 crop images (Drive fileIds from the manifest), L1 screenshots (Drive fileIds from the manifest).  
**Process:** Python MCP `generate_report` renders a Jinja2 template into a single-file HTML report (images referenced as remote Drive URLs, so the file carries no local asset dependencies).

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
**Delivered:** Opened in the Cowork preview panel at end of run.

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

**L2 assessment contract:** The skill assesses against: page markdown text + page screenshot (both already in context from L1) + the full `kilos-framework.json` from its `references/` directory (factors with descriptions and survey labels). For each factor it emits `present`/`absent` with 1–2 evidence items per present factor, plus tone/layout/content-type. The emitted JSON is validated against the `kilos-l2` schema by `save_artifact` before it is persisted. The analyst is the running agent — whichever model the user has selected for the Cowork session — not a pinned API model.

**L3 strength promotion logic:**
- `strong` — factor is `present` in 3+ sources, OR present in 1–2 sources with prominent evidence (headline-level copy, hero image)
- `present` — factor is `present` in 1–2 sources with body-level evidence
- `absent` — factor appears in no source

---

## Python MCP Tool Surface

All tools are exposed via stdio MCP. The server lives at `mcp-server/server.py` inside the plugin. **Every tool is mechanical** — local file/image/template operations with no model calls and no network credentials. Inputs and outputs that reference images are **disk paths**, never base64.

| Tool | Inputs | Outputs | Notes |
|---|---|---|---|
| `create_audit` | company_name, domain, template_id, talent_segment? | audit_id, manifest path | Creates audit directory + manifest |
| `get_audit_status` | audit_id | step statuses, artifact counts | Read-only manifest query |
| `save_artifact` | audit_id, layer, type, source_path, parent_ids[], params{}, validate_schema? | artifact_id | Records artifact in manifest; moves/copies the file into the audit dir. If `validate_schema` is given (e.g. `kilos-l2`, `l3-synthesis`), validates the file against that JSON schema first and fails on mismatch. This is the write path for **all** agent-produced artifacts (L0–L3). |
| `stitch_images` | audit_id, tile_paths[], client_height, device_pixel_ratio | output_path | Reads tile PNGs from disk, writes stitched full-page PNG. Pillow port of clipUtils.stitchImagesWithOverlap. |
| `crop_image` | audit_id, source_path, rect{x,y,w,h}, device_pixel_ratio | output_path | Reads source PNG from disk, writes crop PNG. Pillow port of clipUtils.cropToElement. |
| `generate_report` | audit_id | report_path | Renders Jinja2 template from manifest + l3-synthesis.json into a single-file HTML report (Drive-hosted image URLs). |
| `set_step_status` | audit_id, step_id, status, error? | — | Manifest step status update for live-ops rendering. |

**Deliberately not MCP tools:**
- **KILOS analysis (L2) and synthesis (L3)** — performed by the orchestrating skill inline; persisted via `save_artifact` + `validate_schema`. (See credentials table.)
- **Drive upload** — the skill calls the connected Drive MCP (`create_file`); the returned `fileId` is recorded via `save_artifact` params.

---

## Audit Manifest

The manifest is the single source of truth for pipeline state and all UI rendering. See [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md) for the principle and [ADR-002](../../decisions/ADR-002-audit-manifest-schema.md) for the full schema of record (the snippet below is illustrative; ADR-002 is authoritative, including the `parent_step_ids` vs `parent_ids` distinction). Key fields:

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
      "produced_by_step_id": "l1-text-capture",
      "parent_ids": ["l0-urls"],
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

**First-run setup:** On first skill invocation, the skill checks for Python 3 and runs `pip install -r requirements.txt` (Pillow for images, jinja2 for templating, jsonschema for artifact validation) into a plugin-local venv if not already present. No Node.js required. No user-facing install steps beyond plugin installation.

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

Files are uploaded via the **connected Drive MCP** (`create_file` with `base64Content` + `contentMimeType` for binary PNGs), not a service account. The returned `fileId` is recorded in the manifest, and the L4 report references images via `lh3.googleusercontent.com/d/{fileId}` — no base64 in the report, no external CDN; reports work for anyone with Drive access.

**Known cost:** uploading a binary via the connected Drive MCP means the image's base64 passes through the agent's tool channel once, at upload time. For V1's modest image count (≈1–2 images per source, each scaled to ≤2000px) this is acceptable. If image volume grows, the alternative is to have the Python server write PNGs into a Drive-desktop-sync folder and resolve `fileId`s via Drive MCP `search_files` — avoiding base64 entirely, at the cost of assuming the user runs Drive desktop sync. Deferred until volume justifies it.

---

## Deferred Items

| Item | Issue | Target |
|---|---|---|
| Playwright MCP headless fallback | [#1](https://github.com/michaelblum/employer-brand-audits/issues/1) | V1.1 |
| Browser as collaborative surface (overlays, guided tours) | [#2](https://github.com/michaelblum/employer-brand-audits/issues/2) | V2 |
| L4 report visual design (publications kit) | [#3](https://github.com/michaelblum/employer-brand-audits/issues/3) | V1.1 |
| L5 comparative meta-analysis | — | After V1 POC |
| Visual workflow diagram-with-blanks renderer | ADR-001 | V1.1 |

**Architecture decisions of record:** [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md) (workflow graph as UI), [ADR-002](../../decisions/ADR-002-audit-manifest-schema.md) (manifest schema), [ADR-003](../../decisions/ADR-003-browser-layer.md) (browser layer), [ADR-004](../../decisions/ADR-004-layered-artifact-dag.md) (layered artifact DAG).
