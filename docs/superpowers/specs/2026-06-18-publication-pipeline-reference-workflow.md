# Publication Pipeline Reference Workflow

## Purpose

Define the smallest useful reference path for producing the full publication
pipeline that leads to an L4 artifact: source capture, evidence matrix, KILOS
tagging, analysis records, workbook/report/deck views, and final publication
surface.

This spec separates the source-data artifact from the final publication
artifact:

- Smallest source-data artifact:
  `reference_publications/Reference/HarbourVest Partners - Competitor messaging samples.xlsx`
- Smallest full report milestone:
  `reference_publications/Reference/Northside EVP 2025 Client Data Immersion and Comp Audit.docx`
- Smallest audit deck milestone:
  `reference_publications/Reference/ADT Comp Audit for Tech.pptx`
- Smallest overall deck, but not a report:
  `reference_publications/Ontologies/KILOS/KILOS Introduction.pptx`

The practical reproduction target is the reusable EVP client immersion and
competitor messaging audit shape, backed by a KILOS-normalized evidence matrix
like the HarbourVest workbook.

The implementation path must be company-profile driven. Reference publications
provide structural shape only: section order, evidence density, slide or table
counts, and view types. Runnable demos must use fictional sample profiles from
`data/publication-pipeline-profiles/`. A profile for an arbitrary company must
be able to produce the same minimum data groups: client plus competitors,
source roster, capture pack, KILOS evidence, survey signals, review snapshots,
analysis findings, report outline, and report/deck/workbook/L4 views without
inheriting reference-source copy, competitors, IDs, or labels.

Hard rule: reference client names and their competitor/source labels must not
appear in generated default artifacts. They may appear only in docs identifying
the local reference source files and in reference-reader tests that assert
structural facts.

This is not an L4-only workflow. The L4 artifact is the last projection of the
same upstream records. The workflow must produce useful intermediate artifacts
on the way there, including source captures, normalized evidence, comparison
matrices, analysis findings, and report/deck drafts.

## Reference Selection

Use the Northside reference DOCX as the first structural source for the generic
EVP client immersion and competitor messaging audit archetype because it has the
lowest full-report complexity among the references inspected:

- one DOCX report rather than a large presentation;
- about 32 pages by embedded table of contents;
- 3 competitors plus the client;
- 8 tables and 10 media files;
- simple report sections: introduction, methodology, client immersion,
  competitor messaging audit, market trends, brand positioning, strengths,
  opportunities, and appendices.

Use the HarbourVest workbook as the first data artifact because its
`Messaging audit` sheet is already the underlying matrix that a report or deck
needs:

- columns are client and competitor entities;
- rows are ontology themes, prompts, source URLs, and evidence slots;
- cells are raw evidence or notes that can be normalized into long-form records.

## KILOS Role

KILOS is the organizing ontology for the first reproducible workflow. It is not
just presentation copy. The KILOS framework supplies the comparison vocabulary,
tagging rules, colors, and rollups that let the same source evidence render as
a workbook, report, deck, or L4 publication.

Required KILOS inputs:

- `reference_publications/kilos-framework.json` as the canonical ontology.
- Five pillars: Kinship, Impact, Lifestyle, Opportunity, and Status.
- Factor definitions and survey aliases for evidence tagging.
- Pillar colors and labels for tables, charts, scorecards, and callouts.
- Optional survey mapping from
  `reference_publications/Ontologies/KILOS/KILOS mapping.xlsx`.

Every captured evidence item should either map to a KILOS pillar/factor or be
explicitly marked as non-KILOS contextual evidence. Every generated trend,
strength, gap, and opportunity should preserve its supporting KILOS tags so the
artifact can switch between narrative sections and matrix views.

## Minimum Workflow

1. Select the pipeline target and current milestone.
   - `capture_pack`: source URL captures, screenshots, visible text, snapshots.
   - `evidence_matrix`: normalized evidence and workbook-ready matrix.
   - `analysis_pack`: KILOS rollups, trends, strengths, gaps, opportunities.
   - `report_docx`: client immersion and competitor messaging audit.
   - `audit_deck`: companion summary deck.
   - `data_workbook`: KILOS evidence matrix workbook.
   - `ontology_intro`: KILOS explanation deck.
   - `l4_publication`: final publication/report surface.

2. Create the project frame.
   - Client name, sector, geography, audience, report title, date, project goal.
   - Current milestone, downstream artifact target, expected sections, expected
     competitors, and KILOS version.

3. Build the source roster.
   - Client careers pages, DEI/culture pages, annual or strategy documents.
   - Competitor careers pages and relevant talent-audience pages.
   - Review sources such as Glassdoor or Indeed when used by the report.
   - Internal client data such as values, benefits, awards, survey results, and
     qualitative themes.

4. Capture and stage evidence.
   - Store source URL, capture artifact path, visible text, screenshot path, and
     capture timestamp.
   - Preserve quoted evidence snippets with enough context to cite them.
   - Attach source artifacts to stable entity and section ids.

5. Normalize into a long-form evidence model.
   - Convert wide spreadsheets into records keyed by project, entity, source,
     section, KILOS pillar/factor, and evidence text.
   - Keep raw excerpts separate from analyst summaries.
   - Treat KILOS JSON as the ontology source of truth.
   - Mark non-KILOS evidence separately instead of forcing weak matches.

6. Derive analysis records.
   - Employer positioning summary per entity.
   - KILOS theme coverage per entity.
   - Market trend observations across entities.
   - Client strengths, gaps, and opportunities.
   - Proof points and appendix samples.

7. Render milestone views.
   - Capture pack view: source inventory, screenshots, visible text, and capture
     status.
   - Data workbook view: evidence matrix and source tabs.
   - Analysis pack view: KILOS rollups, theme coverage, trend findings, and
     recommendation inputs.
   - DOCX report view: client immersion and competitor messaging sections and
     appendices.
   - PPTX deck view: executive summary and comparison tables.
   - L4 view: publication-ready report surface generated from the same records.

8. Verify closeness.
   - Match expected section order and artifact density before polishing.
   - Compare page or slide count, table count, media count, and appendix depth.
   - Render the output and inspect first-pass layout manually.
   - Confirm every analytical claim has at least one source-backed evidence item.
   - Confirm every KILOS-coded claim has a pillar/factor and supporting excerpt.

## Canonical Data Contract

Use a long-form schema as the canonical layer. Wide workbooks, DOCX sections,
slide tables, and L4 publication pages are views over these records.

```yaml
publication_project:
  project_id: string
  client_name: string
  industry: string
  geography: string
  audience: string
  current_milestone: capture_pack | evidence_matrix | analysis_pack | report_docx | audit_deck | data_workbook | ontology_intro | l4_publication
  final_artifact_target: report_docx | audit_deck | l4_publication
  framework_id: string
  framework_version: string
  report_title: string
  report_date: string

entity:
  entity_id: string
  project_id: string
  name: string
  role: client | competitor | partner_org | source_org
  source_urls:
    careers_url: string
    culture_url: string
    dei_url: string
    review_urls: [string]
    other_urls: [string]

source_artifact:
  artifact_id: string
  project_id: string
  entity_id: string
  source_url: string
  source_type: careers_page | culture_page | dei_page | report | review_site | social | note
  captured_at: string
  text_path: string
  screenshot_path: string
  snapshot_path: string
  citation_label: string

ontology_term:
  framework_id: string
  pillar_id: string
  pillar_name: string
  pillar_color: string
  factor_id: string
  factor_name: string
  theme_label: string
  aliases: [string]
  description: string

evidence_item:
  evidence_id: string
  project_id: string
  entity_id: string
  artifact_id: string
  section: client_immersion | careers_messaging | dei_messaging | creative |
    internal_activations | external_activations | partnerships | reviews |
    benefits | awards | notes
  pillar_id: string
  factor_id: string
  theme_label: string
  evidence_type: quote | paraphrase | url | metric | yes_no | note
  evidence_text: string
  source_url: string
  confidence: high | medium | low
  reviewer_notes: string

survey_signal:
  signal_id: string
  project_id: string
  survey_question: string
  response_choice: string
  percentage: number
  count: number
  pillar_id: string
  factor_id: string

review_snapshot:
  snapshot_id: string
  project_id: string
  entity_id: string
  source_name: string
  rating: number
  review_count: number
  recommend_percent: number
  positive_themes: [string]
  negative_themes: [string]
  captured_at: string

analysis_finding:
  finding_id: string
  project_id: string
  entity_id: string
  finding_type: positioning | market_trend | strength | gap | opportunity |
    proof_point | recommendation
  headline: string
  summary: string
  supporting_evidence_ids: [string]
  confidence: high | medium | low

artifact_plan:
  artifact_id: string
  project_id: string
  target: capture_pack | evidence_matrix | analysis_pack | report_docx |
    audit_deck | data_workbook | l4_publication
  reference_path: string
  sections:
    - section_id: string
      title: string
      source_record_types: [string]
      expected_layout: prose | table | matrix | scorecard | appendix | hero
```

## Base Audit Report Data Needs

A reusable EVP client immersion and competitor messaging audit needs these
populated record groups:

- `publication_project`: client, audience, project goal, date, and report title.
- `entity`: client plus 3-5 competitors.
- `source_artifact`: capture records for every cited client and competitor
  source.
- `ontology_term`: KILOS pillars, factors, aliases, colors, and descriptions.
- `evidence_item`: raw messaging and proof points mapped to entities and KILOS.
- `survey_signal`: client survey or internal data where available.
- `review_snapshot`: external review metrics if the report includes reputation
  comparison.
- `analysis_finding`: positioning, market trends, strengths, gaps, and
  opportunities.
- `artifact_plan`: section sequence matching the target report.

Minimum viable data volume:

- 1 client profile;
- 3 competitor profiles;
- 5 KILOS pillar definitions;
- at least 10 raw evidence items per entity;
- survey signals for the client immersion section;
- review snapshots for Glassdoor/Indeed-style reputation comparison;
- 1 positioning summary per entity;
- 4-8 cross-market trend findings;
- 3-5 client strengths;
- 3-5 client opportunities;
- 3 or more risks/gaps;
- appendix rows that preserve the raw messaging samples.

## Rendering Rules

Keep the generation boundary explicit:

- Evidence extraction produces records, not prose.
- Analysis turns evidence records into findings.
- Rendering turns findings into DOCX, PPTX, workbook, or L4 views.
- Visual polish is a separate pass after structure and source coverage are
  proven.

For close-enough reproduction, optimize first for:

1. section order;
2. comparison table shapes;
3. citation/source completeness;
4. density of evidence per entity;
5. enough screenshots or images to support visual-identity discussion.

Do not start by copying visual decoration from the reference. Start by proving
that the same data can drive the same sections.
