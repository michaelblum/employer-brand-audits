# ADR-004: Layered Artifact DAG

**Date:** 2026-06-10  
**Status:** Accepted  

---

## Context

An audit is not a single transform from URL to report. It collects raw material, interprets it through a framework, synthesizes a judgment, and re-expresses that judgment as a report — and users will want to revise one of those stages without paying for all of them again. The question was whether to model the pipeline as a monolithic single-pass run or as a graph of reusable, layered artifacts.

## Decision

Model the pipeline as a **layered artifact DAG** — the design's L0–L5 layers, where each layer's outputs are immutable, addressable artifacts that downstream layers consume. (This was "approach C" in brainstorming.) The layers:

- **L0** URL discovery → **L1** text + screenshots → **L2** per-source KILOS analysis + crops → **L3** synthesized judgment with provenance → **L4** HTML report → **L5** (future) cross-company meta-analysis.

Artifacts and their dependency edges are recorded in the manifest ([ADR-002](ADR-002-audit-manifest-schema.md)).

## Why — the four properties that justified it

1. **Compute reuse.** Re-running L4 (report) or L3 (synthesis) does not re-scrape L1 or re-call the browser. Lower layers are cached as artifacts.
2. **Branching.** From one set of L1/L2 artifacts, multiple L3/L4 expressions can branch (e.g. an all-talent report and a tech-talent report from the same captures).
3. **Additivity.** New sources can be added to an existing audit — new L1/L2 artifacts attach to the graph without rebuilding what is already there.
4. **Novel synthesis and re-expression.** L2/L3 are where interpretation lives; L4 is a *re-expression* of L3, and L5 is a synthesis *across* many L3s. Separating "the judgment" (L3) from "the presentation" (L4) means the report can be redesigned, or a meta-analysis built, without touching the analysis.

## Alternative considered

**Monolithic single-pass pipeline** — collect, analyze, and render in one run with no persisted intermediate artifacts. Rejected: every revision re-collects and re-analyzes (slow, and re-hits the anti-bot sites unnecessarily), branching is impossible, sources can't be added incrementally, and a report redesign would require re-running analysis. The single-pass model is simpler to build but forecloses exactly the things this tool exists to do.

## Consequences

- **The manifest is load-bearing.** Reuse, branching, and selective re-runs all depend on artifacts being addressable with explicit provenance — hence ADR-002's schema and the rule that `save_artifact` is the universal write path.
- **Layers are a contract, not just a label.** Each layer consumes the layer below through artifact references, so a layer can be re-implemented as long as it honors the artifact `type` it produces.
- **Staleness is a real concern.** When an upstream artifact is regenerated, downstream artifacts derived from it (via `parent_ids`) are stale and must be flagged or rebuilt. The detection rule is implementation detail; the schema makes it expressible.
- **L5 is unlocked for free.** Because each company's judgment is a persisted L3 artifact, the future comparative meta-analysis is "synthesize across N L3s" rather than a separate data-collection effort.

## Related

- [ADR-002: Audit Manifest Schema](ADR-002-audit-manifest-schema.md) — the structure that makes reuse/branching expressible
- [ADR-001: The Workflow Graph Is The UI](ADR-001-workflow-graph-as-ui.md) — the same graph, rendered for users
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
