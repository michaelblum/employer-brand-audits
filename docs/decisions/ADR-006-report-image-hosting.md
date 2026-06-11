# ADR-006: Report Image Hosting and Analysis Renditions

**Date:** 2026-06-10  
**Status:** Accepted  

---

## Context

The L4 report embeds screenshot evidence. Two separate questions had to be answered: **where do the report's images live so they render in an `<img>`,** and **how big should the images sent to the model for visual analysis be.** Both are shaped by hard constraints established earlier this session.

**Constraint A — bytes must not route through the model.** Per the token-accounting finding ([ADR-005](ADR-005-screenshot-capture-strategy.md) context + Issue #4), tool-call *arguments* are model **output** tokens, and a multi-MB base64 image as an argument exceeds the output-token ceiling and simply fails. So the connected Drive MCP's `create_file(base64Content=…)` cannot be used by the agent to upload real screenshots.

**Constraint B — `<img src>` is an unauthenticated, cross-origin GET.** The browser sends no OAuth token — only a cookie for the image's host. So a non-public image can only be authorized by the viewer's own session cookie, and Google removed that path (third-party cookies for Drive downloads) on **2 Jan 2024**. Research verified that `lh3.googleusercontent.com/d/{id}` and `drive.google.com/uc?export=view` now require public link-sharing and/or the dead cookie, return 403s, and are throttled and undocumented. **Drive hotlinks are not a reliable embed mechanism**, independent of confidentiality.

**Confidentiality scoping (Michael, V1).** The image **clips** are screenshots of *public-facing* websites (careers pages, job ads) — non-sensitive, freely available online. The **analysis and composed report** are the sensitive layer. Public hosting of the clips is therefore acceptable for V1; this may change as the tool expands and is explicitly out of scope now.

## Decision

### 1. Public clips on GitHub; private report in Drive

- **Image clips → a dedicated public GitHub assets repo** (e.g. `eba-audit-assets`, separate from the code repo). The Python MCP server `git push`es each clip (bytes go local-disk → GitHub via git, reusing the user's existing GitHub auth — no new credentials, nothing through the model). The report embeds `https://raw.githubusercontent.com/<org>/<assets-repo>/<branch>/<audit>/<file>.png`.
- **The report file stays access-controlled** in the Drive shared folder. It references public image URLs but is itself private — the sensitive layer (analysis, narrative) is never public. A dedicated public repo also guarantees raw URLs work regardless of the code repo's visibility and keeps binary churn out of the code history.
- **`raw.githubusercontent.com`** is the V1 embed URL (immediate, free, adequate for low-traffic reports). **jsDelivr** (CDN over the same repo, commit-pinned) is the drop-in upgrade if traffic/perf warrants — not needed for V1.

### 2. Sensitive-image fallback: base64 inline

Any image flagged sensitive is **not** pushed to GitHub; it is base64-`data:`-URI inlined into the (private) report by the Python server. This inherits the report file's own permissions, has no expiry, and needs no host. It is the documented escape hatch for the future non-public-imagery case.

### 3. Two image renditions (analysis vs archival)

The Python server produces two renditions per capture; **the model only ever ingests the analysis rendition.**

| Rendition | Purpose | Settings |
|---|---|---|
| **Archival** | Report image (GitHub-hosted, human-viewed, zoomable) | JPEG q≈80, ≤~1600–2000px long edge |
| **Analysis** | Sent to the model for the L2 visual pass | downscaled to a **tunable** ~768–1024px long edge, q≈70 |

**Why this works:** vision token cost is a function of **pixel dimensions**, not file bytes — ≈ `(w×h)/750`, capped (~1,590 tokens) for any image above ~1.15MP. JPEG quality cuts storage/transfer but **not** model cost; downscaling cuts model cost. And because L1 already captured the page **text** separately (the `get_page_text` markdown), the screenshot's only L2 job is **visual language** (tone, layout, color, imagery, modern-vs-dated) — gestalt, not legibility. So the analysis rendition can be small, and the L2 prompt explicitly instructs: *judge visual language only; text is provided separately; do not read text from the image.* This cuts vision tokens ~2–3× per image **and** improves accuracy (no straining to OCR a blurry capture).

A per-recipe fidelity override exists for the rare case of text baked *into* an image that isn't in the DOM (opt into high fidelity for that one recipe).

## Consequences

- The image-hosting and infeasible-upload problems both disappear: bytes flow local→GitHub (git) and local→Drive (file sync), never through the model.
- **Report & artifact delivery to Drive** is affected by Constraint A too: the Python server writes artifacts (manifest, JSON, the lean HTML report) to the **local** audit folder; Drive sync is achieved by that folder living under a **Google Drive for Desktop** synced path (a user-facing dependency, standard in Workspace orgs), falling back to local-only + manual share if absent. The connected Drive MCP reverts to **read-only** (fetching the KILOS source docs); it is no longer the artifact write path. *(Confirmed: Drive for Desktop is mandated on the org's managed machines.)*
- New mechanical Python responsibilities: produce the two renditions (downscale), and `publish_image` (git add/commit/push to the assets repo → return raw URL).
- **V1.1 enhancement (noted, not built):** much "visual language" is extractable cheaply from the DOM/CSS already injected (computed fonts, brand color palette, video/carousel/animation presence, image count, density). Feeding that as structured text augments — and could partly replace — pixel inference.

## Out of scope (V1)

- Sensitive/non-public imagery (→ base64 inline, or GCS V4 signed URLs which are confidential + embeddable but cap at a 7-day expiry and need GCP setup).
- jsDelivr CDN, `@googleworkspace/cli` (real and Google-published, uploads to Drive, but only yields the dead Drive hotlinks for embedding and is pre-1.0).

## Related

- [ADR-005: Screenshot Capture Strategy](ADR-005-screenshot-capture-strategy.md)
- [Issue #4: Capture primitive implementation spikes](https://github.com/michaelblum/employer-brand-audits/issues/4)
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
