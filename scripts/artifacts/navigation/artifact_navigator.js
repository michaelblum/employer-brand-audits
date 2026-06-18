(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  const PRIMITIVES = window.ArtifactPrimitives = window.ArtifactPrimitives || {};
  const common = ROOT.common;

  const ARTIFACT_TYPE_META = {
    image: { icon: "image", className: "image" },
    markdown: { icon: "markdown", className: "markdown" },
    html: { icon: "html", className: "html" },
    json: { icon: "text", className: "text" },
    text: { icon: "text", className: "text" },
    log: { icon: "log", className: "log" },
    file: { icon: "unknown", className: "unknown" },
  };

  function escapeHtml(value) {
    return common.escapeHtml(value);
  }

  function formatSlot(value) {
    return String(value || "").replace(/[._-]/g, " ");
  }

  function normalizedText(value) {
    return formatSlot(value)
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function uniqueValues(values = []) {
    const seen = new Set();
    const result = [];
    for (const value of values) {
      const text = String(value ?? "").replace(/\s+/g, " ").trim();
      const key = normalizedText(text);
      if (!text || seen.has(key)) continue;
      seen.add(key);
      result.push(text);
    }
    return result;
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function flexibleWhitespacePattern(value) {
    return escapeRegExp(value).replace(/\\ /g, "\\s+");
  }

  function projectionMetaValues(values = []) {
    return values
      .map((value) => String(value ?? "").trim())
      .filter(Boolean);
  }

  function projectedArtifact(context, item) {
    return context.projectedArtifactsById?.[item?.id] || null;
  }

  function projectedStep(context, item) {
    const projected = projectedArtifact(context, item);
    return projected ? context.projectedStepsById?.[projected.produced_by_step_id] || null : null;
  }

  function projectedSlot(context, item) {
    const projected = projectedArtifact(context, item);
    return projected ? context.projectedSlotsByValue?.[projected.slot] || null : null;
  }

  function activeComposite(context = {}) {
    return context.filters?.compositeId ? context.projectedGroupsById?.[context.filters.compositeId] || null : null;
  }

  function artifactProjectionModel(payload = null) {
    const workbenchProjection = payload && typeof payload === "object" ? payload : null;
    const model = {
      workbenchProjection,
      projectedArtifactsById: {},
      projectedStepsById: {},
      projectedSlotsByValue: {},
      projectedGroupsById: {},
    };
    for (const item of workbenchProjection?.artifacts || []) {
      if (item?.id) model.projectedArtifactsById[item.id] = item;
    }
    for (const step of workbenchProjection?.workflow?.steps || []) {
      if (step?.id) model.projectedStepsById[step.id] = step;
    }
    for (const slot of workbenchProjection?.facets?.slots || []) {
      if (slot?.value) model.projectedSlotsByValue[slot.value] = slot;
    }
    for (const group of workbenchProjection?.artifact_groups || []) {
      if (group?.id) model.projectedGroupsById[group.id] = group;
    }
    return model;
  }

  function artifactNavigationContext({
    artifacts = [],
    interactionOverlays = [],
    contexts = [],
    context = null,
    activeIndex = 0,
    filters = {},
    iconHref = null,
    projectionModel = null,
  } = {}) {
    const model = projectionModel || artifactProjectionModel(null);
    return {
      artifacts,
      interactionOverlays,
      contexts,
      context,
      activeIndex,
      filters,
      iconHref,
      projectedArtifactsById: model.projectedArtifactsById || {},
      projectedGroupsById: model.projectedGroupsById || {},
      projectedSlotsByValue: model.projectedSlotsByValue || {},
      projectedStepsById: model.projectedStepsById || {},
      workbenchProjection: model.workbenchProjection || null,
    };
  }

  function artifactIndexById(context, artifactId) {
    return (context.artifacts || []).findIndex((item) => item.id === artifactId);
  }

  function artifactAnnotations(context, artifactId) {
    const overlay = PRIMITIVES.interactionOverlay;
    if (overlay && typeof overlay.annotationOverlays === "function") {
      return overlay.annotationOverlays(context.interactionOverlays || [], artifactId);
    }
    return (context.interactionOverlays || []).filter((item) => (
      item?.subtype === "annotation"
      && item.subject?.kind === "artifact"
      && item.subject?.id === artifactId
    ));
  }

  function annotationAnchor(note) {
    return note?.anchor || {};
  }

  function annotationText(note) {
    const overlay = PRIMITIVES.interactionOverlay;
    if (overlay && typeof overlay.annotationText === "function") {
      return overlay.annotationText(note);
    }
    return note?.body?.text || "";
  }

  function anchorSummary(anchor = {}) {
    if (anchor.type === "image_region" && anchor.rect) {
      return `image ${anchor.rect.x},${anchor.rect.y} ${anchor.rect.width}x${anchor.rect.height}`;
    }
    if (anchor.type === "text_range" && anchor.start && anchor.end) {
      return anchor.start.line === anchor.end.line
        ? `line ${anchor.start.line}`
        : `lines ${anchor.start.line}-${anchor.end.line}`;
    }
    if (anchor.type === "html_element") {
      const selector = (anchor.selector_candidates || []).find(Boolean)
        || (anchor.id ? `#${anchor.id}` : "")
        || anchor.tag
        || "element";
      return `element ${selector}`;
    }
    return "unanchored";
  }

  function artifactTypeLabel(context, item) {
    const projected = projectedArtifact(context, item);
    return String(projected?.facets?.artifact_type || projected?.type || item?.type || "file");
  }

  function artifactIconHref(context, name) {
    if (typeof context.iconHref === "function") return context.iconHref(name);
    return `/assets/artifact-workbench-icons.svg#icon-artifact-${name}`;
  }

  function artifactTypeIcon(context, item) {
    const type = artifactTypeLabel(context, item);
    const meta = ARTIFACT_TYPE_META[type] || { icon: "unknown", className: "unknown" };
    return `<span class="artifact-type-icon ${escapeHtml(meta.className)}" title="${escapeHtml(type)}" aria-label="${escapeHtml(type)}" role="img"><svg aria-hidden="true"><use href="${escapeHtml(artifactIconHref(context, meta.icon))}"></use></svg></span>`;
  }

  function artifactSubtypeLabel(context, item) {
    const projected = projectedArtifact(context, item);
    const slot = projectedSlot(context, item);
    return String(slot?.label || projected?.slot || projected?.kind || item?.kind || projected?.facets?.artifact_kind || "").trim();
  }

  function artifactClassLabels(context, item) {
    const projected = projectedArtifact(context, item);
    const slot = projectedSlot(context, item);
    return uniqueValues([
      artifactSubtypeLabel(context, item),
      slot?.label,
      projected?.slot,
      projected?.facets?.artifact_kind,
      item?.kind,
    ].map(formatSlot));
  }

  function artifactSourceSlug(context, item) {
    const projected = projectedArtifact(context, item);
    return String(projected?.source_page?.slug || projected?.facets?.page_slug || "").trim();
  }

  function artifactDisplayName(context, item) {
    const original = String(item?.name || item?.id || "Artifact").replace(/\s+/g, " ").trim();
    const sourceSlug = artifactSourceSlug(context, item);
    if (!sourceSlug) return original;
    const classLabels = artifactClassLabels(context, item)
      .sort((left, right) => normalizedText(right).length - normalizedText(left).length);
    for (const label of classLabels) {
      const normalizedLabel = normalizedText(label);
      if (!normalizedLabel) continue;
      const sourceClassName = new RegExp(`^${flexibleWhitespacePattern(sourceSlug)}\\s+${flexibleWhitespacePattern(label)}$`, "i");
      if (sourceClassName.test(original)) return sourceSlug;
    }
    return original;
  }

  function artifactSubtypeIcon(context, item) {
    const subtype = artifactSubtypeLabel(context, item);
    if (!subtype) return "";
    const label = subtype
      .split(/[._\s-]+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "T";
    return `<span class="artifact-subtype-icon" title="${escapeHtml(formatSlot(subtype))}" aria-label="${escapeHtml(formatSlot(subtype))}">${escapeHtml(label)}</span>`;
  }

  function artifactRowTitle(context, item, values = []) {
    return projectionMetaValues([item?.name, ...values]).join(" · ");
  }

  function artifactStatusBadge(value) {
    const status = String(value || "").trim();
    if (!status) return "";
    const shortLabel = status === "complete" ? "done" : status;
    return `<span class="artifact-row-badge status" title="Status: ${escapeHtml(status)}">${escapeHtml(shortLabel)}</span>`;
  }

  function annotationCountBadge(count = 0) {
    if (!count) return "";
    const label = `${count} ${count === 1 ? "note" : "notes"}`;
    return `<span class="artifact-row-badge note" title="${escapeHtml(label)}">${escapeHtml(String(count))}</span>`;
  }

  function artifactMatchesFilters({ item, filters = {}, projectedArtifactsById = {}, projectedGroupsById = {} }) {
    const projected = projectedArtifactsById[item?.id] || null;
    if (filters.stepId && projected?.produced_by_step_id !== filters.stepId) return false;
    if (filters.slot && projected?.slot !== filters.slot) return false;
    if (filters.compositeId) {
      const group = projectedGroupsById[filters.compositeId];
      if (!group?.artifact_ids?.includes(item.id)) return false;
    }
    return true;
  }

  function visibleArtifactIndexes(context = {}) {
    const indexes = [];
    const artifacts = context.artifacts || [];
    for (let index = 0; index < artifacts.length; index += 1) {
      if (artifactMatchesFilters({ ...context, item: artifacts[index] })) indexes.push(index);
    }
    return indexes;
  }

  function ensureVisibleArtifactIndex({ currentIndex = 0, visibleIndexes = [] } = {}) {
    return visibleIndexes.length && !visibleIndexes.includes(currentIndex) ? visibleIndexes[0] : currentIndex;
  }

  function normalizedFilters(filters = {}) {
    return {
      stepId: filters.stepId || null,
      slot: filters.slot || null,
      compositeId: filters.compositeId || null,
    };
  }

  function artifactFilterPlan(context = {}) {
    const filters = normalizedFilters(context.filters);
    const kind = context.filterKind;
    const value = context.filterValue || null;
    if (kind === "clear") {
      filters.stepId = null;
      filters.slot = null;
      filters.compositeId = null;
    }
    if (kind === "step") filters.stepId = filters.stepId === value ? null : value;
    if (kind === "slot") filters.slot = filters.slot === value ? null : value;
    if (kind === "composite") filters.compositeId = filters.compositeId === value ? null : value;
    const visibleIndexes = visibleArtifactIndexes({ ...context, filters });
    return {
      filters,
      activeIndex: ensureVisibleArtifactIndex({
        currentIndex: context.activeIndex || 0,
        visibleIndexes,
      }),
    };
  }

  function artifactMovePlan(context = {}) {
    const visibleIndexes = visibleArtifactIndexes(context);
    const activeIndex = context.activeIndex || 0;
    if (!visibleIndexes.length) return { activeIndex };
    const current = visibleIndexes.includes(activeIndex) ? visibleIndexes.indexOf(activeIndex) : 0;
    const delta = Number(context.delta || 0);
    return {
      activeIndex: visibleIndexes[(current + delta + visibleIndexes.length) % visibleIndexes.length],
    };
  }

  function artifactProjectionLine(context = {}) {
    const item = context.item || {};
    const projected = projectedArtifact(context, item);
    if (!projected) return `${item.type || "file"} · ${item.path}`;
    const step = projectedStep(context, item);
    const parts = [
      projected.slot || item.type || "file",
      projected.source_page?.slug,
      step?.status,
    ].filter(Boolean);
    return `${parts.join(" · ")} · ${item.path}`;
  }

  function compositeKindLabel(group = {}) {
    return formatSlot(group.kind || "composite");
  }

  function compositeSourceLabel(context = {}, group = {}) {
    const source = group.source || {};
    if (source.kind === "audit_report_step" && source.step_id) {
      const step = context.projectedStepsById?.[source.step_id] || null;
      return `Report step: ${step?.name || source.step_id}`;
    }
    if (source.kind && source.step_id) return `${formatSlot(source.kind)}: ${source.step_id}`;
    if (source.kind) return formatSlot(source.kind);
    return "";
  }

  function compositeMemberEntries(context = {}, group = activeComposite(context)) {
    if (!group) return [];
    return (group.artifact_ids || [])
      .map((artifactId) => {
        const index = artifactIndexById(context, artifactId);
        if (index < 0) return null;
        return {
          index,
          item: (context.artifacts || [])[index],
        };
      })
      .filter(Boolean);
  }

  function renderCompositeMemberHtml(context, entry) {
    const item = entry.item || {};
    return `
      <div class="composite-member" data-composite-member="${escapeHtml(String(entry.index))}">
        ${artifactTypeIcon(context, item)}
        <div class="composite-member-copy">
          <div class="name">${escapeHtml(artifactDisplayName(context, item))}</div>
          <div class="small">${escapeHtml(artifactProjectionLine({ ...context, item }))}</div>
        </div>
      </div>
    `;
  }

  function renderActiveCompositeReadoutHtml(context = {}) {
    const composite = activeComposite(context);
    if (!composite) return "";
    const members = compositeMemberEntries(context, composite);
    const sourceLabel = compositeSourceLabel(context, composite);
    const countLabel = `${members.length} ${members.length === 1 ? "artifact" : "artifacts"}`;
    return `
      <section class="composite-readout" data-composite-id="${escapeHtml(composite.id)}">
        <div class="summary-kicker">Composite</div>
        <div class="composite-readout-title">${escapeHtml(composite.label || composite.id)}</div>
        <div class="projection-meta">
          <span>${escapeHtml(compositeKindLabel(composite))}</span>
          <span>${escapeHtml(countLabel)}</span>
          ${sourceLabel ? `<span>${escapeHtml(sourceLabel)}</span>` : ""}
        </div>
        <div class="composite-members">
          ${members.map((entry) => renderCompositeMemberHtml(context, entry)).join("")}
        </div>
      </section>
    `;
  }

  function renderArtifactTitleHtml(context = {}) {
    const item = (context.artifacts || [])[context.activeIndex || 0] || {};
    const workflow = context.workbenchProjection?.workflow;
    const composite = activeComposite(context);
    const breadcrumbSegments = projectionMetaValues([
      workflow?.name,
      composite?.label || composite?.id,
    ]);
    const breadcrumbHtml = breadcrumbSegments.length
      ? `<span class="artifact-breadcrumb-rail" title="${escapeHtml(breadcrumbSegments.join(" / "))}">${breadcrumbSegments.map((segment) => (
        `<span class="artifact-breadcrumb-segment">${escapeHtml(segment)}</span>`
      )).join('<span class="artifact-breadcrumb-separator" aria-hidden="true">›</span>')}</span>`
      : "";
    return `
      <div class="artifact-identity-strip" title="${escapeHtml(item.name || "")}">
        <span class="artifact-heading">${escapeHtml(artifactDisplayName(context, item))}</span>
        ${breadcrumbHtml}
      </div>
    `;
  }

  function renderOverviewHtml(context = {}) {
    const contexts = context.contexts || [];
    const activeManifest = context.context?.manifest || contexts.find((item) => item.active)?.manifest || "";
    const activeContext = contexts.find((item) => item.manifest === activeManifest) || null;
    const contextPicker = contexts.length ? `
        <div class="context-switcher">
          <label for="workbench-context-select">Workflow</label>
          <select id="workbench-context-select" data-context-select>
            ${contexts.map((item) => `
              <option value="${escapeHtml(item.manifest)}" ${item.manifest === activeManifest ? "selected" : ""}>
                ${escapeHtml(item.label || item.manifest)}
              </option>
            `).join("")}
          </select>
          <div class="small">${escapeHtml(activeContext?.subtitle || activeManifest)}</div>
        </div>
      ` : "";
    const artifacts = context.artifacts || [];
    const artifactButtons = visibleArtifactIndexes(context).map((index) => {
      const item = artifacts[index] || {};
      return `
        <button class="artifact-option ${index === context.activeIndex ? "active" : ""}" type="button" data-index="${index}">
          <span>${escapeHtml(artifactDisplayName(context, item))}</span>
          <span class="small">${escapeHtml(artifactProjectionLine({ ...context, item }))}</span>
        </button>
      `;
    }).join("");
    return contextPicker + artifactButtons;
  }

  function filterSteps(context = {}) {
    const stepIds = [...new Set(
      (context.artifacts || [])
        .map((item) => projectedArtifact(context, item)?.produced_by_step_id)
        .filter(Boolean)
    )];
    return stepIds
      .map((stepId) => context.projectedStepsById?.[stepId])
      .filter(Boolean)
      .sort((a, b) => String(a.name || a.id).localeCompare(String(b.name || b.id)));
  }

  function filterSlots(context = {}) {
    const slotValues = [...new Set(
      (context.artifacts || [])
        .map((item) => projectedArtifact(context, item)?.slot)
        .filter(Boolean)
    )].sort();
    return slotValues.map((slot) => context.projectedSlotsByValue?.[slot] || { value: slot, label: formatSlot(slot) });
  }

  function filterComposites(context = {}) {
    return Object.values(context.projectedGroupsById || {})
      .filter((group) => Array.isArray(group.artifact_ids)
        && group.artifact_ids.some((artifactId) => artifactIndexById(context, artifactId) >= 0))
      .sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)));
  }

  function filterSummaryText({ total = 0, visible = 0 } = {}) {
    return visible === total ? `${total} artifacts` : `${visible} of ${total} artifacts`;
  }

  function statusLabel(value) {
    const raw = String(value || "unknown").replace(/[._-]/g, " ").trim().toLowerCase();
    if (raw === "ok" || raw === "passed") return "complete";
    return raw || "unknown";
  }

  function titleCase(value) {
    return String(value || "").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function pluralize(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
  }

  function artifactHealthText(context = {}) {
    const counts = {};
    for (const item of context.artifacts || []) {
      const projected = projectedArtifact(context, item);
      const label = statusLabel(projected?.status || item.status || projectedStep(context, item)?.status);
      counts[label] = (counts[label] || 0) + 1;
    }
    const priority = ["error", "failed", "warning", "unknown", "complete"];
    return Object.keys(counts)
      .sort((left, right) => {
        const priorityDelta = priority.indexOf(left) - priority.indexOf(right);
        if (priorityDelta !== 0) return priorityDelta;
        return left.localeCompare(right);
      })
      .map((label) => `${counts[label]} ${label}`)
      .join(" · ");
  }

  function artifactSummaryModel(context = {}) {
    const workflow = context.workbenchProjection?.workflow || {};
    const artifacts = context.artifacts || [];
    const steps = workflow.steps || [];
    const slots = filterSlots(context);
    const composites = filterComposites(context);
    const visible = visibleArtifactIndexes(context).length;
    const workbenchProjectionCount = artifacts
      .filter((item) => Boolean(projectedArtifact(context, item))).length;
    return {
      title: workflow.name || "Workflow",
      status: statusLabel(workflow.status),
      statusLabel: titleCase(statusLabel(workflow.status)),
      role: `${visible} visible of ${artifacts.length} artifacts`,
      workbenchReady: `${workbenchProjectionCount} workbench-ready`,
      workflowShape: [
        pluralize(steps.length, "step"),
        pluralize(slots.length, "slot"),
        pluralize(composites.length, "composite"),
      ].join(" · "),
      health: artifactHealthText(context),
    };
  }

  function renderArtifactSummarySection(section = {}) {
    return `
      <div class="artifact-summary-section" data-summary-section="${escapeHtml(section.id)}">
        <div class="summary-section-label">${escapeHtml(section.label)}</div>
        <div class="summary-section-value">${escapeHtml(section.value)}</div>
        ${section.detail ? `<div class="summary-section-detail">${escapeHtml(section.detail)}</div>` : ""}
      </div>
    `;
  }

  function renderArtifactNavigationHeader(context = {}) {
    const workflow = context.workbenchProjection?.workflow;
    if (!workflow) return "";
    const artifacts = context.artifacts || [];
    const filters = context.filters || {};
    const summary = artifactSummaryModel(context);
    const steps = filterSteps(context);
    const slots = filterSlots(context);
    const composites = filterComposites(context);
    const visible = visibleArtifactIndexes(context).length;
    const summarySections = [
      { id: "workflow", label: "Workflow", value: summary.statusLabel, detail: summary.workflowShape },
      { id: "role", label: "Role", value: summary.role, detail: summary.workbenchReady },
      { id: "health", label: "Health", value: summary.health, detail: filterSummaryText({ total: artifacts.length, visible }) },
    ];
    return `
        <div class="artifact-summary">
          <div class="summary-kicker">Audit summary</div>
          <div class="summary-title">${escapeHtml(summary.title)}</div>
          <div class="artifact-summary-sections">
            ${summarySections.map(renderArtifactSummarySection).join("")}
          </div>
          <div class="filter-line">
            <span>${escapeHtml(filterSummaryText({ total: artifacts.length, visible }))}</span>
            ${(filters.stepId || filters.slot || filters.compositeId) ? '<button type="button" data-filter-kind="clear">Clear</button>' : ""}
          </div>
          <div class="filter-group" aria-label="Workflow step filters">
            ${steps.map((step) => `
              <button class="${step.id === filters.stepId ? "active" : ""}" type="button" data-filter-kind="step" data-filter-value="${escapeHtml(step.id)}">
                ${escapeHtml(String(step.name || step.id).replace(/^Capture /, ""))}
              </button>
            `).join("")}
          </div>
          <div class="filter-group" aria-label="Slot filters">
            ${slots.map((slot) => `
              <button class="${slot.value === filters.slot ? "active" : ""}" type="button" data-filter-kind="slot" data-filter-value="${escapeHtml(slot.value)}">
                ${escapeHtml(slot.label || formatSlot(slot.value))}
              </button>
            `).join("")}
          </div>
          <div class="filter-group" aria-label="Composite filters">
            ${composites.map((group) => `
              <button class="${group.id === filters.compositeId ? "active" : ""}" type="button" data-filter-kind="composite" data-filter-value="${escapeHtml(group.id)}">
                ${escapeHtml(group.label || group.id)}
              </button>
            `).join("")}
          </div>
        </div>
      `;
  }

  function renderArtifactRow(context, index) {
    const item = (context.artifacts || [])[index] || {};
    const notes = artifactAnnotations(context, item.id);
    const projected = projectedArtifact(context, item);
    const step = projectedStep(context, item);
    const slot = projectedSlot(context, item);
    const projectionMeta = projected
      ? projectionMetaValues([
        slot?.label || formatSlot(projected.slot),
        projected.source_page?.slug,
        step?.status || projected.status,
      ])
      : [];
    const statusValue = projected ? step?.status || projected.status : "";
    const rowBadges = [
      artifactStatusBadge(statusValue),
      annotationCountBadge(notes.length),
    ].filter(Boolean).join("");
    const rowTitle = artifactRowTitle(context, item, projectionMeta);
    const annotationHtml = notes.length
      ? notes.map((note) => `
            <div class="annotation" draggable="true" data-artifact-id="${escapeHtml(item.id)}" data-annotation-id="${escapeHtml(note.id)}">
              <div class="annotation-text" title="${escapeHtml(annotationText(note))}">${escapeHtml(annotationText(note))}</div>
              <div class="small">${escapeHtml(anchorSummary(annotationAnchor(note)))}</div>
            </div>
          `).join("")
      : "";
    return `
          <div class="artifact-row artifact-row-compact ${index === context.activeIndex ? "active" : ""}" data-index="${index}" title="${escapeHtml(rowTitle)}">
            <div class="row-title">
              ${artifactTypeIcon(context, item)}
              ${artifactSubtypeIcon(context, item)}
              <div class="name">${escapeHtml(artifactDisplayName(context, item))}</div>
              ${rowBadges ? `<div class="artifact-row-badges">${rowBadges}</div>` : ""}
            </div>
            ${annotationHtml}
          </div>
        `;
  }

  function renderSidebarHtml(context = {}) {
    const artifactRows = visibleArtifactIndexes(context)
      .map((index) => renderArtifactRow(context, index))
      .join("");
    return renderArtifactNavigationHeader(context)
      + renderActiveCompositeReadoutHtml(context)
      + (artifactRows || '<div class="empty-filter">No artifacts match the active filters.</div>');
  }

  ROOT.navigation = {
    activeComposite,
    anchorSummary,
    artifactMatchesFilters,
    artifactProjectionLine,
    artifactSummaryModel,
    artifactTypeLabel,
    filterComposites,
    filterSlots,
    filterSteps,
    filterSummaryText,
    formatSlot,
    renderSidebarHtml,
    renderActiveCompositeReadoutHtml,
    renderArtifactTitleHtml,
    renderOverviewHtml,
    renderArtifactNavigationHeader,
    visibleArtifactIndexes,
    ensureVisibleArtifactIndex,
    artifactProjectionModel,
    artifactNavigationContext,
    artifactFilterPlan,
    artifactMovePlan,
  };
}());
