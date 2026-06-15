(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const ARTIFACT_TYPE_META = {
    image: { icon: "image", className: "image" },
    markdown: { icon: "markdown", className: "markdown" },
    json: { icon: "text", className: "text" },
    text: { icon: "text", className: "text" },
    log: { icon: "log", className: "log" },
    file: { icon: "unknown", className: "unknown" },
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function formatSlot(value) {
    return String(value || "").replace(/[._-]/g, " ");
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

  function artifactIndexById(context, artifactId) {
    return (context.artifacts || []).findIndex((item) => item.id === artifactId);
  }

  function artifactAnnotations(context, artifactId) {
    return context.annotations?.[artifactId] || [];
  }

  function annotationAnchor(note) {
    return note?.anchor || {};
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
    return "unanchored";
  }

  function artifactTypeLabel(context, item) {
    const projected = projectedArtifact(context, item);
    return String(projected?.facets?.artifact_type || projected?.type || item?.type || "file");
  }

  function artifactIconHref(context, name) {
    if (typeof context.iconHref === "function") return context.iconHref(name);
    return `/assets/workflow-artifact-workbench-icons.svg#icon-artifact-${name}`;
  }

  function artifactTypeIcon(context, item) {
    const type = artifactTypeLabel(context, item);
    const meta = ARTIFACT_TYPE_META[type] || { icon: "unknown", className: "unknown" };
    return `<span class="artifact-type-icon ${escapeHtml(meta.className)}" title="${escapeHtml(type)}" aria-label="${escapeHtml(type)}" role="img"><svg aria-hidden="true"><use href="${escapeHtml(artifactIconHref(context, meta.icon))}"></use></svg></span>`;
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

  function workflowFilterPlan(context = {}) {
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

  function workflowMovePlan(context = {}) {
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

  function renderArtifactTitleHtml(context = {}) {
    const item = (context.artifacts || [])[context.activeIndex || 0] || {};
    const projected = projectedArtifact(context, item);
    const slot = projectedSlot(context, item);
    const workflow = context.workbenchProjection?.workflow;
    const composite = activeComposite(context);
    const slotLabel = slot?.label || projected?.slot;
    const slotHtml = slotLabel ? `<span class="slot-pill">${escapeHtml(slotLabel)}</span>` : "";
    const breadcrumbHtml = composite
      ? `<span class="artifact-breadcrumb">${escapeHtml(workflow?.name || "Workflow")} -&gt; ${escapeHtml(composite.label || composite.id)}</span>`
      : "";
    const formatTime = typeof context.formatTime === "function" ? context.formatTime : () => "";
    return `${breadcrumbHtml}<span class="artifact-heading">${escapeHtml(item.name)} ${slotHtml} <span class="artifact-time">(${escapeHtml(formatTime(item.created_at_epoch))})</span></span>`;
  }

  function renderOverviewHtml(context = {}) {
    const artifacts = context.artifacts || [];
    return visibleArtifactIndexes(context).map((index) => {
      const item = artifacts[index] || {};
      return `
        <button class="artifact-option ${index === context.activeIndex ? "active" : ""}" type="button" data-index="${index}">
          <span>${escapeHtml(item.name)}</span>
          <span class="small">${escapeHtml(artifactProjectionLine({ ...context, item }))}</span>
        </button>
      `;
    }).join("");
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

  function renderWorkflowHeader(context = {}) {
    const workflow = context.workbenchProjection?.workflow;
    if (!workflow) return "";
    const artifacts = context.artifacts || [];
    const filters = context.filters || {};
    const workbenchProjectionCount = artifacts
      .filter((item) => Boolean(projectedArtifact(context, item))).length;
    const steps = filterSteps(context);
    const slots = filterSlots(context);
    const composites = filterComposites(context);
    const visible = visibleArtifactIndexes(context).length;
    return `
        <div class="workflow-summary">
          <div class="summary-kicker">${escapeHtml(workflow.status || "unknown")}</div>
          <div class="summary-title">${escapeHtml(workflow.name || "Workflow")}</div>
          <div class="summary-grid">
            <span>${escapeHtml(String((workflow.steps || []).length))} steps</span>
            <span>${escapeHtml(String(workbenchProjectionCount))} workbench-visible</span>
            <span>${escapeHtml(String(slots.length))} slots</span>
            <span>${escapeHtml(String(composites.length))} composites</span>
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
    const annotationHtml = notes.length
      ? notes.map((note) => `
            <div class="annotation" draggable="true" data-artifact-id="${escapeHtml(item.id)}" data-annotation-id="${escapeHtml(note.id)}">
              <div class="annotation-text" title="${escapeHtml(note.comment)}">${escapeHtml(note.comment)}</div>
              <div class="small">${escapeHtml(anchorSummary(annotationAnchor(note)))}</div>
            </div>
          `).join("")
      : "";
    return `
          <div class="artifact-row ${index === context.activeIndex ? "active" : ""}" data-index="${index}">
            <div class="row-title">
              ${artifactTypeIcon(context, item)}
              <div class="name">${escapeHtml(item.name)}</div>
            </div>
            ${projected ? `
              <div class="projection-meta">
                <span>${escapeHtml(slot?.label || formatSlot(projected.slot))}</span>
                <span>${escapeHtml(projected.source_page?.slug || "")}</span>
                <span>${escapeHtml(step?.status || projected.status || "")}</span>
              </div>
            ` : ""}
            ${annotationHtml}
          </div>
        `;
  }

  function renderSidebarHtml(context = {}) {
    const artifactRows = visibleArtifactIndexes(context)
      .map((index) => renderArtifactRow(context, index))
      .join("");
    return renderWorkflowHeader(context)
      + (artifactRows || '<div class="empty-filter">No artifacts match the active filters.</div>');
  }

  ROOT.workflowSidebar = {
    activeComposite,
    anchorSummary,
    artifactMatchesFilters,
    artifactProjectionLine,
    artifactTypeLabel,
    filterComposites,
    filterSlots,
    filterSteps,
    filterSummaryText,
    formatSlot,
    renderSidebarHtml,
    renderArtifactTitleHtml,
    renderOverviewHtml,
    renderWorkflowHeader,
    visibleArtifactIndexes,
    ensureVisibleArtifactIndex,
    workflowFilterPlan,
    workflowMovePlan,
  };
}());
