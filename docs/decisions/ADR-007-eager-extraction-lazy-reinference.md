# ADR-007: Eager Per-Artifact Extraction + Lazy Confluence Re-Inference

**Date:** 2026-06-11  
**Status:** Accepted  
**Refines:** [ADR-004](ADR-004-layered-artifact-dag.md)

---

## Context

[ADR-004](ADR-004-layered-artifact-dag.md) established the layered artifact DAG (map per artifact, reduce across artifacts). This ADR pins down *how much inference happens when*, and what survives as durable, reusable signal — a high-leverage question once token economics matter.

Two anti-patterns to avoid:
- **One big pass over everything** — dump all sources into a single call. Dilutes attention ("lost in the middle"), re-pays to re-read every source for every comparison, and produces nothing reusable or incremental.
- **Over-eager lossy summarization** — compress each artifact to a coarse blob at creation and then *only ever* reason over the blobs. Connections that need detail the blob dropped are lost, and the lens is frozen at capture time.

## Decision

### Eager pass at artifact creation

When an artifact is created, run **one cheap inference pass** (on the markdown for text, the downscaled *analysis* rendition for images — see [ADR-006](ADR-006-report-image-hosting.md)) that produces two **separate** outputs:

1. **A lens-neutral `card`** — NL essence (≤~250 words) + lookup tags (`content_type`, theme tags, `imagery_kind`, `talent_segment_hint`, source title/SLD). KILOS-agnostic. Stored on the manifest artifact record, mirrored to the Drive file description, and echoed in the filename convention. This is the catalog/index layer: routing, grouping, dedup, lookup, provenance.
2. **A lens-specific `kilos_map`** — per applicable factor: `present` + **`salience` (0–3)** + evidence. Captured per source (the natural unit for the KILOS lens; a lone cropped image doesn't independently evidence "good benefits"). Cards are per *artifact* (finer); the KILOS map is per *source*.

### Lens-neutral / lens-specific split

The card and the map are kept **separate** deliberately. The card survives the tool outgrowing KILOS (a future non-KILOS analysis still gets a useful index from it); the map is the swappable V1 lens. Baking everything into KILOS terms would over-fit the durable substrate to one lens.

### Raw artifacts stay re-inferable ground truth

The eager outputs are an **index, not a replacement.** Raw artifacts remain addressable and are open to **additional inference later, in confluence with other artifacts** — including for questions not anticipated at creation. The eager pass captures the *anticipated* signal; raw re-inference handles the *unanticipated*.

### Lazy confluence re-inference with escalation tiering

Cross-artifact analysis (L3, L5, ad-hoc) reads the **eager fields first** (cards + maps + salience — cheap), and **escalates to re-inferring over the raw artifact only when the question isn't answerable from the fields.** This is what makes "leave it open for more inference" affordable: no pre-paying for every possible future analysis.

### Salience feeds weighted strength roll-up

Per-source `salience` (0 = absent, 1 = incidental/body, 2 = prominent, 3 = hero/headline) makes L3's `strong/present/absent` a **weighted roll-up** rather than a mention recount: `strong` if any source ≥2 (or `present` in 3+ sources); `present` if ≥1 in 1–2 sources; `absent` if 0 everywhere.

## Consequences

- The card + map are a **byproduct of the same per-source pass** — not a separate call. One eager pass per source yields both.
- New mandatory fields: `card` on the manifest artifact record ([ADR-002](ADR-002-audit-manifest-schema.md)); `salience` in the `kilos-l2` content schema.
- **V1 scope:** capture cards + maps + salience eagerly; L3 is a (simple) confluence re-inference over those fields, re-reading raw artifacts when a comparison needs more. The sophisticated card-driven routing (group like-with-like → scoped sub-synthesis → meta-assembly) rides on top at **L5 / large audits**, where N justifies it.
- **Filename convention** (cheap, durable, do from day 1): `l{layer}_{slug-from-card-or-title}_{sld}_{ordinal}.{ext}`, e.g. `l1_acme-benefits_acme-com_03.jpg`.
- Drive file metadata mirrors the card for Drive-native search; the **manifest remains the source of truth** (metadata is a mirror).

## Related

- [ADR-004: Layered Artifact DAG](ADR-004-layered-artifact-dag.md) — the structure this refines
- [ADR-002: Audit Manifest Schema](ADR-002-audit-manifest-schema.md) — gains the `card` field
- [ADR-006: Report Image Hosting & Renditions](ADR-006-report-image-hosting.md) — the analysis rendition the image pass runs on
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
