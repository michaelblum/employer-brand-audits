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
| **Cowork Skill** | Conversational orchestrator **and analyst**. Intake wizard, workflow routing, layer handoffs, KILOS assessment (L2) and synthesis (L3) performed inline in the agent loop, report delivery. |
| **Claude in Chrome** | Browser layer. URL discovery, text extraction, full-page screenshots, all in the user's real Chrome with real sessions/cookies. |
| **Python MCP Server** | Mechanical utilities only. Image stitching/cropping/**rendition** (Pillow), manifest read/write, schema validation, L4 report templating (Jinja2), and writing all artifacts to the local audit folder + `git push` of public image clips. No model calls, no network credentials beyond the user's existing git auth. |
| **Connected Google Drive MCP** | **Read-only** — fetches the KILOS source docs. No longer the artifact write path (see [ADR-006](../../decisions/ADR-006-report-image-hosting.md)). |
| **GitHub assets repo (public)** | Hosts non-sensitive public-web image clips for `<img>` embedding in the report. Written by the Python server via `git push`; see [ADR-006](../../decisions/ADR-006-report-image-hosting.md). |

**Why Claude in Chrome over Playwright/headless:** The target sites (Indeed, Glassdoor, LinkedIn, Kununu) actively detect headless automation. Claude in Chrome uses the user's real Chrome browser with their existing fingerprint and session cookies — indistinguishable from a legitimate user visit. No distribution problem (the extension is already installed). No captcha risk. See [ADR-003](../../decisions/ADR-003-browser-layer.md) and [Issue #1](https://github.com/michaelblum/employer-brand-audits/issues/1) (Playwright headless fallback, deferred to V1.1).

**Why Python over Node:** Python ships with macOS. No binary compilation issues, no Node.js install requirement for non-developer users. Pillow handles image stitching natively.

### Credentials and external access (zero-config premise)

The architecture was chosen specifically to require **no API keys, no service accounts, and no per-user configuration**. This premise constrains where each responsibility lives:

| Capability | Where it runs | Why not the Python MCP server |
|---|---|---|
| Browser automation | Claude in Chrome (host extension) | The server has no browser and no session cookies. |
| KILOS analysis & synthesis (L2/L3) | The orchestrating skill, inline in the agent loop | A bundled MCP server is a separate process with **no inherited model access** — calling Claude would require its own API key and billing. MCP *sampling* (server-requests-host-completion) is host-dependent and historically unsupported in Cowork, and even where available it is pure indirection: the skill already holds the page text and screenshots in context. The analysis stays in the agent loop. |
| Read KILOS source docs | Connected Drive MCP (read-only) | A service account would be a second, conflicting credential mechanism; the session already has an authenticated Drive MCP. |
| Artifact + report delivery to Drive | Python writes to the local audit folder → **Google Drive for Desktop** syncs it | The connected Drive MCP's `create_file` can't carry real files: a multi-MB base64 argument is model **output** tokens and exceeds the output ceiling (it fails, not just costs). So bytes must not route through the model. Drive for Desktop is mandated on the org's managed machines, so it's a safe dependency. |
| Public image-clip hosting | Python `git push` to a public GitHub assets repo | Reuses the user's existing git auth (no new credential); bytes go local→GitHub, never through the model. Clips are non-sensitive public-web imagery (see ADR-006). |
| Image processing, manifest, templating | Python MCP server | These are local, deterministic, credential-free — exactly what the server is for. |

The Python MCP server is therefore a pure mechanical utility, plus the one sanctioned external action of `git push`ing public clips with the user's existing git credentials. If a future need requires it to call Claude or reach the network beyond that, that is a deliberate departure from this premise and warrants its own ADR. Detail in [ADR-006](../../decisions/ADR-006-report-image-hosting.md).

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
2. **Screenshot pass:** DRAW `_waitForAnimations`, `_hideObscuringElements`, and `_suppressScrollbarsAndRounding` injected via `javascript_tool` to settle the page and remove overlays/seam artifacts, then capture. Two capture modes (full strategy in [ADR-005](../../decisions/ADR-005-screenshot-capture-strategy.md), validated by an empirical spike):
   - **Element crop (fits in viewport)** → scroll into view, then Claude in Chrome `zoom` to the element's `getBoundingClientRect`. The `zoom` region is CSS-px and viewport-relative, returns an element-exact crop at ~2× resolution. No stitching, no Pillow.
   - **Full-page scan / element taller than viewport / inner-scroll container** → the agent scroll-tiles via `computer` screenshot and the Python MCP `stitch_images` tool stitches with overlap correction (Pillow port of `clipUtils.stitchImagesWithOverlap`). DRAW's three scroll-stitch paths apply (page scroll, element-window intersection crop, internal `scrollBy`).

**Scale is measured, not assumed — "page as ruler."** `computer` screenshot is a *display-region* capture, so its pixel scale depends on which monitor the window is on (verified: ~0.982× CSS px on a scaled retina display; a lower-DPI external monitor differs; assuming `× devicePixelRatio` would be 2× wrong). The pipeline measures `S = capture_pixel_width / window.innerWidth` per sequence and validates it against the height ratio (mismatch ⇒ window straddles two displays ⇒ abort). The capture is page-only with origin at viewport (0,0), so once `S` is known, any CSS rect maps to image pixels. Never detect the display or query DPI.

**Image handoff.** Single `zoom` element crops return inline to the agent (one image — fine). The many-tile full-page stitch prefers tiles on disk so N images don't cross the agent's context; whether `save_to_disk` exposes a server-readable path (or needs a fallback) is the one open build-time spike — [Issue #4](https://github.com/michaelblum/employer-brand-audits/issues/4).

**Two renditions per capture (cost control).** The Python server writes each captured/stitched image in two renditions: an **archival** rendition for the report (JPEG q≈80, ≤~1600–2000px long edge — what humans see and what gets hosted) and a smaller **analysis** rendition (downscaled to a *tunable* ~768–1024px long edge) that is the **only** image sent to the model for the L2 visual pass. Vision token cost scales with pixel *area* (≈ `w×h/750`, capped for large images), so **downscaling — not JPEG quality — is the lever** (quality only affects bytes/hosting); the analysis rendition saves ~2–3× per image. Non-sensitive clips are published to the public GitHub assets repo by the server (`publish_image`); the report references their raw URLs. Full rationale in [ADR-006](../../decisions/ADR-006-report-image-hosting.md).

**Capture recipes** are defined per source type in the workflow template. Each recipe captures intent, not implementation (e.g., "full-page scan of careers landing page, hiding chat widgets and cookie banners"). The agent can re-derive the approach from the intent description if the DOM changes (intent-addressable automation, per [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md)).

Recipe types:
- `full_page` — scroll-tile-stitch of the whole page (optionally scaled to a max height, e.g. ≤2000px, per recipe)
- `element_clip` — crop to one element via `zoom` to its rect; supports optional `frame` and `trim` (below)
- `scroll_region` — full content of a nested `overflow:auto/scroll` element captured via internal `scrollBy` + stitch
- `animated_widget` — capture at the settled frame of an animation (uses `_waitForAnimations`)

**`frame` and `trim` are distinct operations** (see [ADR-005](../../decisions/ADR-005-screenshot-capture-strategy.md) §5):
- **`frame {top,right,bottom,left}`** — breathing room in the element's *own background* (e.g. text flush to the edge of a zero-padding element). Achieved by JIT-injecting CSS padding onto the element, re-measuring, capturing, then restoring (DRAW `apply_clip_padding`). Expanding the crop rect would instead capture adjacent page content — not a clean frame.
- **`trim {top,right,bottom,left}`** — shave px off the clip: shrink the `zoom` region inward, or crop inward in Pillow (top/bottom on a stitched image are a post-stitch crop).

**Output:** Per-URL `{url_id}-text.md` and `{url_id}-screenshot.png`, stored in the audit directory.  
**Artifacts:** `l1-{url_id}-text`, `l1-{url_id}-screenshot`

### L2 — KILOS Analysis and Image Crops

**Input:** L1 text + screenshot artifacts for a given URL.  
**Process:** The **orchestrating skill performs the assessment inline** — it holds the page **markdown** (full fidelity, for content) and the small **analysis rendition** of the screenshot (for visual language) from L1, plus the KILOS reference schema from its `references/` directory. Content factors (benefits, DEI, progression, etc.) are read from the markdown; visual-language factors (tone, layout, imagery, modernity) are judged from the image. The prompt instructs: *judge visual language only from the image; the page text is provided separately; do not read or transcribe text from the image* — which is exactly why the analysis rendition can be aggressively downscaled (see [ADR-006](../../decisions/ADR-006-report-image-hosting.md)). It assesses each of the 29 KILOS factors across 5 pillars (K1–K5, I1–I6, L1–L7, O1–O6, S1–S5), emits a structured JSON object, then calls Python MCP `save_artifact` with `validate_schema: "kilos-l2"` to validate and persist it. (No MCP tool calls Claude — see the credentials table above.)

**Eager pass = card + map** (see [ADR-007](../../decisions/ADR-007-eager-extraction-lazy-reinference.md)). The same per-source pass emits two *separate* outputs: a lens-**neutral** `card` and the lens-**specific** `kilos_map`. The card is kept KILOS-agnostic so the durable substrate survives the tool outgrowing KILOS; the map is the swappable V1 lens. Both are eager — the raw artifacts stay **re-inferable** for later confluence analysis (L3/L5) that the eager fields can't answer.

Per-factor output (in `kilos_map`):
- `status`: `present` | `absent`
- `salience`: `0–3` — 0 absent, 1 incidental/body, 2 prominent, 3 hero/headline. Feeds L3's weighted strength roll-up.
- `evidence`: 1–2 quotes from page text, or image descriptions where text is absent
- `source_url`: canonical URL
- `snapshot_date`: ISO date

Per-source output (in addition to factors):
- `tone`: `human` | `formal`
- `layout`: `modern` | `dated`
- `content_type`: `dynamic` | `static`
- `talent_segment_specific`: `true` | `false` + supporting quote

Per-artifact `card` (lens-neutral, every text/screenshot/crop artifact): `summary` (≤~250-word NL essence) + tags (`content_type`, `theme[]`, `imagery_kind`, `talent_segment_hint`, source title/SLD). Stored on the manifest artifact record, mirrored to the Drive file description, echoed in the filename. This is the routing/grouping/lookup index.

Image crops: where evidence points to a specific visual element (e.g., a hero image, a benefits section), the preferred path is a direct `zoom` element crop (the L1 `element_clip` recipe) — high-res, CSS coordinates, no post-processing. When the element exists only inside an already-captured stitched full-page image, the skill calls Python MCP `crop_image` with the stitched image, a CSS rect, and `window.innerWidth` so Pillow applies the measured scale `S`; Pillow writes the crop PNG to disk.

**Output:** `l2-{url_id}-kilos.json`, `l2-{url_id}-crop-{n}.png`

### L3 — Synthesis JSON with Provenance

**Input:** All L2 KILOS analysis files for the company.  
**Process:** The **skill synthesizes inline** — a *confluence re-inference* over the eager per-artifact fields (cards + `kilos_map`s + salience) read via the manifest, escalating to re-reading raw artifacts only when a comparison needs more than the fields hold (see [ADR-007](../../decisions/ADR-007-eager-extraction-lazy-reinference.md)). It produces:

- **Factor strength** — a weighted roll-up of per-source `salience` to `strong` | `present` | `absent` (rule below)
- **Brand positioning statement** — one-sentence distillation of how the company presents itself as an employer
- **Tone/layout/content** — modal values across all sources
- **Strengths** (2–3) — factors where the company performs distinctively well, labeled `strength` or `differentiator`
- **Gaps** (2–3) — absent or underweight factors that represent an opportunity, labeled `opportunity` with a `gap_description`
- **Talent segment coverage** — whether target talent segments are explicitly addressed

Strength promotion and modal tone/layout are mechanical and could be precomputed, but the strengths/gaps narratives require judgment — so the whole L3 object is produced by the skill in one pass, then persisted via `save_artifact` with `validate_schema: "l3-synthesis"`.

Every field in the L3 JSON carries `source_artifact_ids[]` and `source_url` for provenance. Citations in the L4 report link directly to the source URL with a snapshot date disclaimer.

**Output:** `l3-synthesis.json`  
**Synced to:** written to the local audit folder; reaches Drive via Drive-for-Desktop sync (see [ADR-006](../../decisions/ADR-006-report-image-hosting.md))

### L4 — HTML SPA Report

**Input:** `l3-synthesis.json`, L2 crop images and L1 archival screenshots (referenced by their public GitHub raw URLs, recorded in the manifest after the Python server pushes them — see [ADR-006](../../decisions/ADR-006-report-image-hosting.md)).  
**Process:** Python MCP `generate_report` renders a Jinja2 template into an HTML report whose images are `<img src>` to the public GitHub-hosted clips. The report file itself (the sensitive layer — analysis + composed narrative) is **not** public; it stays access-controlled in the Drive shared folder. Only the non-sensitive public-web clips are publicly hosted.

Report sections:
1. **Cover** — company name, audit date, talent segment scope
2. **Brand positioning** — one-sentence statement with supporting quote
3. **Creative execution** — tone / layout / content-type assessment with screenshot evidence
4. **KILOS heat map** — 29-factor grid showing `strong` / `present` / `absent` per source (columns = sources, rows = factors, grouped by pillar)
5. **Strengths and differentiators** — 2–3 labeled narrative blocks
6. **Gaps and opportunities** — 2–3 labeled narrative blocks with specific evidence
7. **Source evidence** — per-source section with embedded screenshot (public GitHub raw URL) and key factor presence

Images are embedded as `<img src="https://raw.githubusercontent.com/<org>/<assets-repo>/<branch>/<audit>/<img>.png">` — the clips are non-sensitive public-web imagery (see [ADR-006](../../decisions/ADR-006-report-image-hosting.md)). For any image flagged sensitive, the fallback is base64 `data:` URI inlined into the (private) report. Citations include source URL as a clickable link with snapshot date.

Report visual design is V1 functional/minimal. See [Issue #3](https://github.com/michaelblum/employer-brand-audits/issues/3) for V1.1 visual polish using the Symphony Talent publications kit.

**Output:** `l4-report-{company_slug}.html` (private — written to the local audit folder; reaches the Drive shared folder via Drive-for-Desktop sync)  
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

**L3 strength promotion logic (weighted roll-up of per-source `salience`):**
- `strong` — any source with `salience` ≥ 2 (prominent/hero), OR `present` (`salience` ≥ 1) in 3+ sources
- `present` — `salience` ≥ 1 in 1–2 sources, none ≥ 2
- `absent` — `salience` = 0 in every source

---

## Python MCP Tool Surface

All tools are exposed via stdio MCP. The server lives at `mcp-server/server.py` inside the plugin. **Every tool is mechanical** — local file/image/template operations with no model calls and no network credentials, except `publish_image`, which uses the user's existing git auth. Inputs and outputs that reference images are **disk paths**, never base64.

| Tool | Inputs | Outputs | Notes |
|---|---|---|---|
| `create_audit` | company_name, domain, template_id, talent_segment? | audit_id, manifest path | Creates audit directory + manifest |
| `get_audit_status` | audit_id | step statuses, artifact counts | Read-only manifest query |
| `save_artifact` | audit_id, layer, type, source_path, parent_ids[], params{}, validate_schema? | artifact_id | Records artifact in manifest; moves/copies the file into the audit dir. If `validate_schema` is given (e.g. `kilos-l2`, `l3-synthesis`), validates the file against that JSON schema first and fails on mismatch. This is the write path for **all** agent-produced artifacts (L0–L3). |
| `stitch_images` | audit_id, tiles[{path, scroll_top}], viewport{inner_width, inner_height, client_height} | output_path, measured_scale | Reads tile PNGs from disk; derives scale `S = tile_pixel_width / inner_width` (validates against height ratio); stitches with overlap correction (`overlap = (prevScrollTop + clientHeight) − curScrollTop`). Pillow port of clipUtils.stitchImagesWithOverlap. |
| `crop_image` | audit_id, source_path, css_rect{x,y,w,h}, inner_width, trim?, matte? | output_path | Reads source PNG; derives scale `S = source_pixel_width / inner_width`; crops `css_rect × S`, then optional `trim` (crop inward, CSS px) and/or `matte` (extend canvas with a solid color). Pillow port of clipUtils.cropToElement. Note: Pillow cannot produce an element's-*own-background* frame — that is the capture-time `frame` op (JIT padding); here only solid-color matte is possible. For in-viewport elements prefer a direct `zoom` crop. |
| `make_rendition` | audit_id, source_path, max_edge, quality? | output_path | Downscales an image to `max_edge` (long edge) as JPEG. Produces the small **analysis** rendition for the L2 visual pass (default ~768–1024px, tunable) and the **archival** rendition for the report (~1600–2000px). See [ADR-006](../../decisions/ADR-006-report-image-hosting.md). |
| `publish_image` | audit_id, source_path | public_url | `git add/commit/push`es the (archival) clip to the public GitHub assets repo using the user's existing git auth; returns the `raw.githubusercontent.com` URL. The only tool that touches the network. |
| `generate_report` | audit_id | report_path | Renders Jinja2 template from manifest + l3-synthesis.json into an HTML report; images are `<img src>` to public GitHub raw URLs (or base64-inlined for any image flagged sensitive). |
| `set_step_status` | audit_id, step_id, status, error? | — | Manifest step status update for live-ops rendering. |

**Deliberately not MCP tools:**
- **KILOS analysis (L2) and synthesis (L3)** — performed by the orchestrating skill inline; persisted via `save_artifact` + `validate_schema`. (See credentials table.)
- **Drive upload of artifacts/report** — not via the connected Drive MCP (`create_file` can't carry multi-MB files — the base64 argument exceeds the output-token ceiling). The Python server writes artifacts to the local audit folder; Drive-for-Desktop syncs them. See [ADR-006](../../decisions/ADR-006-report-image-hosting.md).

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

## Storage, Sync, and Hosting

The governing rule (from the token-accounting finding): **image/large-file bytes never route through the model.** The Python server writes everything locally; bytes reach their destinations via file sync (Drive) and git (GitHub). See [ADR-006](../../decisions/ADR-006-report-image-hosting.md).

**Private — the audit folder (analysis + report).** The Python server writes all artifacts to a local audit directory. That directory lives under a **Google Drive for Desktop** synced path, so Drive uploads it in the background — no `create_file`, no bytes through the model. The folder is shared at the folder level (the user sets this up once); the sensitive layer stays access-controlled.

```
<Drive-for-Desktop synced path>/Symphony Talent Audits/   ← private, shared within the org
└── {company_slug}-{date}/
    ├── manifest.json
    ├── artifacts/
    │   ├── l1-*.md
    │   ├── l1-*-archival.jpg      ← report rendition
    │   ├── l1-*-analysis.jpg      ← small rendition sent to the model
    │   ├── l2-*-kilos.json
    │   ├── l2-*-crop-*.jpg
    │   └── l3-synthesis.json
    └── l4-report-{company_slug}.html   ← references public clip URLs; itself private
```

Filenames follow a meaningful convention (ADR-007): `l{layer}_{slug}_{sld}_{ordinal}.{ext}`, e.g. `l1_acme-benefits_acme-com_03.jpg` — the slug comes from the artifact's lens-neutral `card`. Each artifact's `card` is also mirrored to its Drive file description for Drive-native search; the manifest stays the source of truth.

**Public — the image clips.** Non-sensitive public-web clips (archival renditions) are `git push`ed to a dedicated **public GitHub assets repo** by the Python server (`publish_image`), and the report embeds their `raw.githubusercontent.com` URLs. Clips are screenshots of public-facing pages; the *report* that interprets them is not public. Any image flagged sensitive skips GitHub and is base64-inlined into the private report instead.

> **Dependency (confirmed):** Drive for Desktop is mandated on the org's managed machines, so the private-folder sync is a safe assumption. The connected Drive MCP remains read-only (KILOS source docs); it is not the artifact write path.

---

## Deferred Items

| Item | Issue | Target |
|---|---|---|
| Playwright MCP headless fallback | [#1](https://github.com/michaelblum/employer-brand-audits/issues/1) | V1.1 |
| Browser as collaborative surface (overlays, guided tours) | [#2](https://github.com/michaelblum/employer-brand-audits/issues/2) | V2 |
| L4 report visual design (publications kit) | [#3](https://github.com/michaelblum/employer-brand-audits/issues/3) | V1.1 |
| L5 comparative meta-analysis | — | After V1 POC |
| Visual workflow diagram-with-blanks renderer | ADR-001 | V1.1 |
| DOM/CSS-derived visual metadata (cheaper visual-language signal) | ADR-006 | V1.1 |
| Sensitive-image hosting (base64 inline / GCS signed URLs) | ADR-006 | As scope expands |

**Architecture decisions of record:** [ADR-001](../../decisions/ADR-001-workflow-graph-as-ui.md) (workflow graph as UI), [ADR-002](../../decisions/ADR-002-audit-manifest-schema.md) (manifest schema), [ADR-003](../../decisions/ADR-003-browser-layer.md) (browser layer), [ADR-004](../../decisions/ADR-004-layered-artifact-dag.md) (layered artifact DAG), [ADR-005](../../decisions/ADR-005-screenshot-capture-strategy.md) (screenshot capture strategy), [ADR-006](../../decisions/ADR-006-report-image-hosting.md) (report image hosting & renditions), [ADR-007](../../decisions/ADR-007-eager-extraction-lazy-reinference.md) (eager extraction + lazy re-inference).
