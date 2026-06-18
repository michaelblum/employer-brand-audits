# Publication Pipeline Family Roadmap

## Goal

Create reusable, intake-driven pipelines for every reference publication family.
Each pipeline should accept an intake artifact, use repo-native capture and
projection tools, codify the analysis process into structured records, and
render the resulting artifacts in the ADR-002 workbench.

## Shared Intake Contract

Every pipeline starts with a `pipeline_intake` artifact. The intake is the
operator-facing control surface for the workflow, not a final report. It should
be viewable in the workbench and should drive downstream capture and analysis.

Required fields:

- `pipeline_id`: stable pipeline family id.
- `client`: name, sector, geography, domain, and audience.
- `objective`: the publication or decision the pipeline supports.
- `reference_artifacts`: local reference files used to model structure.
- `source_seeds`: URLs, uploaded docs, spreadsheets, decks, notes, or staged
  URL manifests.
- `competitors`: named organizations plus optional source URLs.
- `target_talent_segments`: roles, functions, geographies, or cohorts.
- `ontology`: KILOS framework id and any pipeline-specific extensions.
- `desired_outputs`: report, deck, workbook, L4 view, or campaign plan.
- `review_requirements`: evidence depth, source count, screenshot needs, and
  manual review gates.

Common pipeline stages:

1. `intake`: normalize the request into a bounded artifact.
2. `source_roster`: resolve client, competitor, partner, benchmark, and source
   organizations.
3. `capture_pack`: use `./eba dev stage-url`, file readers, and source notes to
   stage screenshots, visible text, document text, workbook rows, and slide text.
4. `evidence_matrix`: normalize evidence into long-form KILOS-tagged records.
5. `analysis_pack`: derive positioning, trends, strengths, gaps,
   opportunities, risks, recommendations, and campaign lessons.
6. `publication_views`: render report, deck, workbook, and L4 HTML views through
   the existing workbench manifest path.

Installed/readers now available in the local environment:

- `python-docx` for DOCX report structure and text extraction.
- `python-pptx` for PPTX slide structure and text extraction.
- `openpyxl` for XLSX workbook ingestion.
- Existing repo URL capture through `./eba dev stage-url`.

## Pipeline Order

### 0. Base EVP Client Immersion And Competitor Messaging Audit

Reference:

- `reference_publications/Reference/Northside EVP 2025 Client Data Immersion and Comp Audit.docx`

Status:

- First implementation exists and is being corrected to the generic
  `publication-pipeline.evp-client-immersion-competitor-audit` template.
- Northside is a tracked reference profile under
  `data/publication-pipeline-profiles/`, not the pipeline shape.
- The shared `p0-pipeline-intake` artifact now starts the ADR-002 manifest and
  records the operator-facing client, source seed, competitor, ontology,
  desired-output, and review-requirement contract.

Why first:

- It is the smallest complete report family.
- It proves the common source-roster, capture-pack, evidence-matrix,
  analysis-pack, report/deck/workbook/L4 spine.

Next implementation needs:

- Keep the default reference profile fixture.
- Ensure arbitrary-profile output has no reference-profile labels.
- Keep workbench demo and projection tests around the full record chain.

### 1. Segment-Specific Talent Value Proposition Audit

References:

- `reference_publications/Reference/ADT Tech Product TVP 2025 Client Data Immersion and Comp Audit.docx`
- `reference_publications/Reference/ADT Comp Audit for Tech.pptx`

Why second:

- It is the closest sibling to the base audit.
- It adds a reusable `target_talent_segment` dimension without changing the
  core KILOS evidence model.
- The paired DOCX and PPTX let one pipeline prove report-plus-deck rendering.

Generalized pipeline id:

- `publication-pipeline.segment-tvp-audit`

Status:

- Implemented as `./eba dev demo --fixture segment-tvp-audit` with a tracked
  ADT reference profile, segment source roster, segment capture pack, KILOS
  segment evidence matrix, TVP analysis pack, report/deck/social/workbook/L4
  views, and arbitrary-profile leakage tests.

Additional intake fields:

- `target_talent_segments`: for example Technology, Product, Engineering,
  Nursing, Sales, Early Careers.
- `role_evidence_sources`: job postings, role-family careers pages, recruiter
  notes, segment-specific proofpoints.
- `segment_competitors`: competitors chosen for the same talent market, not just
  the same industry.
- `social_sources`: LinkedIn or platform examples when the social audit view is
  requested.

Data model additions:

- `talent_segment`
- `job_posting_artifact`
- `segment_proofpoint`
- `segment_positioning_finding`
- `social_content_observation`

Workbench outputs:

- Intake artifact.
- Segment source roster.
- Job-post/source capture pack.
- KILOS evidence matrix with segment column.
- TVP analysis pack.
- Report view.
- Research summary and brand strategy deck view.

### 2. Evidence Workbook And DEI Competitor Audit

References:

- `reference_publications/Reference/HarbourVest Partners - Competitor messaging samples.xlsx`
- `reference_publications/Reference/HarbourVest Partners - Competitor Audit_.pptx`

Why third:

- The workbook already exposes the raw matrix shape needed by many reports.
- The deck adds a clear DEI competitor-audit structure after the matrix ingester
  exists.
- This is the first pipeline that needs partner organizations, activations, and
  inclusion-philosophy classification.

Generalized pipeline ids:

- `publication-pipeline.competitor-messaging-workbook`
- `publication-pipeline.dei-competitor-audit`

Status:

- `publication-pipeline.competitor-messaging-workbook` is implemented as
  `./eba dev demo --fixture competitor-messaging-workbook` with a tracked
  HarbourVest workbook reference profile, workbook extraction metadata,
  long-form evidence cells, partner organization and activation records,
  analysis pack, workbook view, L4 readout, and arbitrary-profile leakage tests.
- `publication-pipeline.dei-competitor-audit` is implemented as
  `./eba dev demo --fixture dei-competitor-audit` with the HarbourVest reference
  profile, DEI deck extraction metadata, activation, inclusion philosophy,
  partner, benchmark, coverage-gap, deck, L4, and arbitrary-profile leakage
  tests.

Additional intake fields:

- `matrix_workbook`: workbook path or uploaded workbook artifact.
- `dei_dimensions`: gender, ethnicity, LGBTQ+, disability, age, socioeconomic,
  caregivers, veterans, and locally relevant dimensions.
- `partner_org_sources`: memberships, external networks, awards, benchmarks,
  and industry groups.
- `withdrawal_watch`: optional DEI withdrawal or risk sources.

Data model additions:

- `wide_matrix_cell`
- `partner_org`
- `dei_activation`
- `inclusion_philosophy`
- `benchmark_employer`
- `coverage_gap`

Workbench outputs:

- Intake artifact.
- Workbook ingestion preview.
- Long-form evidence matrix.
- DEI activation matrix.
- Partner organization landscape.
- Inclusion philosophy map.
- Competitor audit deck view.
- L4 recommendation/readout view.

### 3. DEI Campaign Desk Research And Competitor Audit

Reference:

- `reference_publications/Reference/Scottish Power DEI Campaign - Desk Research Report & Comp Audit.pptx`

Why fourth:

- It is structurally different from employer-brand audits.
- It requires external research, campaign case studies, source credibility, and
  channel/tactic recommendations.
- It benefits from the matrix, deck, and DEI activations already built in the
  previous pipelines.

Generalized pipeline id:

- `publication-pipeline.campaign-desk-research-comp-audit`

Status:

- Implemented as
  `./eba dev demo --fixture campaign-desk-research-comp-audit` with a tracked
  Scottish Power reference profile, research source roster, desk-research
  evidence pack, campaign case matrix, channel tactic opportunity map,
  campaign recommendation readout, L4 view, and arbitrary-profile leakage tests.

Additional intake fields:

- `campaign_goal`: representation, applications, perception, retention, or
  hiring funnel change.
- `target_population`: for example women in engineering, returners, early
  careers, underrepresented technologists.
- `labor_market_sources`: government, industry, academic, and sector reports.
- `campaign_case_sources`: competitor campaigns and comparator campaigns.
- `channel_scope`: careers site, paid social, organic social, events,
  partnerships, job adverts, or recruiter enablement.
- `geography_scope`: country or region for statistics and policy context.

Data model additions:

- `desk_research_source`
- `labor_market_stat`
- `policy_or_context_signal`
- `campaign_case_study`
- `channel_tactic`
- `campaign_recommendation`

Workbench outputs:

- Intake artifact.
- Research source roster.
- Desk research evidence pack.
- Competitor/campaign case matrix.
- Campaign lessons analysis pack.
- Channels, media, tactics, and strategy view.
- Campaign deck view.
- L4 campaign recommendation view.

### 4. KILOS Ontology And Methodology Publication

References:

- `reference_publications/Ontologies/KILOS/KILOS Introduction.pptx`
- `reference_publications/Ontologies/KILOS/KILOS tables.pptx`
- `reference_publications/Ontologies/KILOS/ST_ KILOS Methodology.pptx`
- `reference_publications/Ontologies/KILOS/KILOS mapping.xlsx`
- `reference_publications/kilos-framework.json`

Why supporting track:

- KILOS is the ontology all audit pipelines use.
- The current runtime already uses `data/kilos-framework.json`; this pipeline
  should turn the ontology itself into an inspectable workbench artifact family.
- It should be built when the audit pipelines need methodology pages, scoring
  explanations, or mapping governance beyond the existing JSON.

Generalized pipeline id:

- `publication-pipeline.kilos-methodology`

Status:

- Implemented as `./eba dev demo --fixture kilos-methodology` with tracked
  KILOS framework data, ontology source roster, KILOS browser, mapping workbook,
  methodology deck metadata, scorecard table metadata, report snippets, L4
  view, and reference-reader tests for local-only KILOS materials when present.

Additional intake fields:

- `ontology_sources`: JSON, PPTX, and XLSX source paths.
- `mapping_sources`: survey labels, workbook mappings, and factor aliases.
- `methodology_outputs`: intro deck, scoring tables, report explainer section,
  or workbench ontology browser.

Data model additions:

- `ontology_pillar`
- `ontology_factor`
- `survey_mapping`
- `methodology_slide`
- `scorecard_table`

Workbench outputs:

- Intake artifact.
- Ontology source roster.
- KILOS browser view.
- Mapping workbook view.
- Methodology deck view.
- Reusable report-section snippets for other pipelines.

## Implementation Sequence

1. Finish the generic base pipeline correction.
2. Add the shared `pipeline_intake` artifact and workbench view.
3. Build `segment-tvp-audit` from the ADT DOCX/PPTX pair.
4. Build `competitor-messaging-workbook` from the HarbourVest workbook.
5. Extend that into `dei-competitor-audit` from the HarbourVest deck.
6. Build `campaign-desk-research-comp-audit` from the Scottish Power deck.
7. Codify `kilos-methodology` as a reusable supporting pipeline.

## Verification Pattern

Each pipeline needs focused tests before workbench demo:

- fixture/profile test: arbitrary intake produces no reference-client leakage;
- reader test: DOCX/PPTX/XLSX extraction captures expected headings, slides, or
  sheets;
- lineage test: every analysis finding cites evidence ids;
- manifest test: workbench projection exposes intake, capture, evidence,
  analysis, and publication views;
- demo smoke: `./eba dev demo --fixture <pipeline>` or manifest-targeted demo
  serves the generated workbench bundle.
