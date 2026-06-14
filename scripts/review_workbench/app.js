    const DEFAULT_VIEWER_CONFIG = {
      maxZoomOutPercent: 10,
      maxZoomInPercent: 400,
      actualSizePercent: 100,
    };

    const app = {
      collection: null,
      annotations: {},
      index: 0,
      drag: null,
      pendingAnchor: null,
      editorMode: "create",
      editing: null,
      activeMarker: null,
      sidebarVisible: true,
      zoomPercent: 100,
      zoomMode: "stage-fit",
      markdownMode: "preview",
      markdownContent: {},
      markdownSavedContent: {},
      markdownDirty: {},
      hoverMarkerTimers: [],
      workbenchProjection: null,
      projectedArtifactsById: {},
      projectedStepsById: {},
      projectedSlotsByValue: {},
      projectedGroupsById: {},
      filters: {
        stepId: null,
        slot: null,
        compositeId: null,
      },
      viewerConfig: {
        ...DEFAULT_VIEWER_CONFIG,
        ...(window.WORKBENCH_VIEWER_CONFIG || {}),
      },
    };
    const $ = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));
    const artifact = () => app.collection.artifacts[app.index];
    const artifactAnnotations = (id) => app.annotations[id] || [];
    const artifactIndexById = (id) => app.collection.artifacts.findIndex((item) => item.id === id);
    const annotationById = (artifactId, annotationId) => artifactAnnotations(artifactId).find((note) => note.id === annotationId);
    const projectedArtifact = (item = artifact()) => app.projectedArtifactsById[item?.id] || null;
    const projectedStep = (item = artifact()) => {
      const projected = projectedArtifact(item);
      return projected ? app.projectedStepsById[projected.produced_by_step_id] || null : null;
    };
    const projectedSlot = (item = artifact()) => {
      const projected = projectedArtifact(item);
      return projected ? app.projectedSlotsByValue[projected.slot] || null : null;
    };
    const activeComposite = () => app.filters.compositeId ? app.projectedGroupsById[app.filters.compositeId] || null : null;
    const artifactUrl = (item) => `/artifact/${String(item.path || "").split("/").map(encodeURIComponent).join("/")}`;
    const isImageArtifact = (item = artifact()) => item.type === "image";
    const isMarkdownArtifact = (item = artifact()) => item.type === "markdown";
    const annotationAnchor = (note) => note?.anchor || {};
    const imageRectAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "image_region" ? anchor.rect : null;
    };
    const textRangeAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "text_range" ? anchor : null;
    };
    const anchorSummary = (anchor = {}) => {
      if (anchor.type === "image_region" && anchor.rect) {
        return `image ${anchor.rect.x},${anchor.rect.y} ${anchor.rect.width}x${anchor.rect.height}`;
      }
      if (anchor.type === "text_range" && anchor.start && anchor.end) {
        return anchor.start.line === anchor.end.line
          ? `line ${anchor.start.line}`
          : `lines ${anchor.start.line}-${anchor.end.line}`;
      }
      return "unanchored";
    };
    const formatTime = (epoch) => {
      if (!epoch) return "";
      return new Date(epoch * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    };
    const formatSlot = (value) => String(value || "").replace(/[._-]/g, " ");
    const ARTIFACT_TYPE_META = {
      image: { icon: "image", className: "image" },
      markdown: { icon: "markdown", className: "markdown" },
      text: { icon: "text", className: "text" },
      log: { icon: "log", className: "log" },
    };
    const iconHref = (name) => `/assets/review-workbench-icons.svg#icon-artifact-${name}`;

    function artifactMatchesFilters(item) {
      const projected = projectedArtifact(item);
      if (app.filters.stepId && projected?.produced_by_step_id !== app.filters.stepId) return false;
      if (app.filters.slot && projected?.slot !== app.filters.slot) return false;
      if (app.filters.compositeId) {
        const group = app.projectedGroupsById[app.filters.compositeId];
        if (!group?.artifact_ids?.includes(item.id)) return false;
      }
      return true;
    }

    function artifactTypeLabel(item) {
      const projected = projectedArtifact(item);
      return String(projected?.facets?.artifact_type || projected?.type || item?.type || "file");
    }

    function artifactTypeIcon(item) {
      const type = artifactTypeLabel(item);
      const meta = ARTIFACT_TYPE_META[type] || { icon: "unknown", className: "unknown" };
      return `<span class="artifact-type-icon ${escapeHtml(meta.className)}" title="${escapeHtml(type)}" aria-label="${escapeHtml(type)}" role="img"><svg aria-hidden="true"><use href="${escapeHtml(iconHref(meta.icon))}"></use></svg></span>`;
    }

    function visibleArtifactIndexes() {
      const indexes = [];
      for (let index = 0; index < app.collection.artifacts.length; index += 1) {
        if (artifactMatchesFilters(app.collection.artifacts[index])) indexes.push(index);
      }
      return indexes;
    }

    function ensureVisibleArtifactSelected() {
      const indexes = visibleArtifactIndexes();
      if (indexes.length && !indexes.includes(app.index)) app.index = indexes[0];
    }

    function indexProjection(payload) {
      app.workbenchProjection = payload && typeof payload === "object" ? payload : null;
      app.projectedArtifactsById = {};
      app.projectedStepsById = {};
      app.projectedSlotsByValue = {};
      app.projectedGroupsById = {};
      for (const item of app.workbenchProjection?.artifacts || []) {
        if (item?.id) app.projectedArtifactsById[item.id] = item;
      }
      for (const step of app.workbenchProjection?.workflow?.steps || []) {
        if (step?.id) app.projectedStepsById[step.id] = step;
      }
      for (const slot of app.workbenchProjection?.facets?.slots || []) {
        if (slot?.value) app.projectedSlotsByValue[slot.value] = slot;
      }
      const groups = app.workbenchProjection?.artifact_groups || [];
      for (const group of groups) {
        if (group?.id) app.projectedGroupsById[group.id] = group;
      }
    }

    async function fetchWorkbenchProjection() {
      try {
        const response = await fetch("/api/workbench-projection", { cache: "no-store" });
        if (!response.ok) return null;
        return await response.json();
      } catch (_error) {
        return null;
      }
    }

    function showToast(message) {
      const toast = $("toast");
      toast.textContent = message;
      toast.classList.add("visible");
      clearTimeout(showToast.timer);
      showToast.timer = setTimeout(() => toast.classList.remove("visible"), 1400);
    }

    async function copyText(value) {
      await navigator.clipboard.writeText(value);
      showToast("Copied");
    }

    async function syncAnnotations() {
      const response = await fetch("/api/annotation-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ annotations: app.annotations }),
      });
      if (!response.ok) showToast("Annotation sync failed");
    }

    function safeHref(value) {
      const href = String(value || "").trim();
      if (!href || href.startsWith("#") || href.startsWith("/")) return href;
      try {
        const parsed = new URL(href, window.location.href);
        return ["http:", "https:", "mailto:"].includes(parsed.protocol) ? href : "";
      } catch (_error) {
        return "";
      }
    }

    function renderInlineMarkdown(value) {
      const tokens = [];
      const token = (html) => {
        const marker = `@@TOKEN_${tokens.length}@@`;
        tokens.push(html);
        return marker;
      };
      let text = String(value || "");
      text = text.replace(/`([^`]+)`/g, (_match, code) => token(`<code>${escapeHtml(code)}</code>`));
      text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
        const safe = safeHref(href);
        return safe
          ? token(`<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
          : escapeHtml(label);
      });
      let html = escapeHtml(text);
      html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      return html.replace(/@@TOKEN_(\d+)@@/g, (_match, index) => tokens[Number(index)] || "");
    }

    function sourceLineAttribute(index) {
      return ` data-source-line="${index + 1}"`;
    }

    function renderMermaidSourceLines(source, firstLineIndex) {
      const lines = String(source || "").split("\n");
      return lines.map((line, offset) => (
        `<span class="mermaid-source-line"${sourceLineAttribute(firstLineIndex + offset)}>${escapeHtml(line || " ")}</span>`
      )).join("\n");
    }

    function renderMermaidBlock(source, fenceStart) {
      const firstSourceLine = fenceStart + 1;
      return (
        `<figure${sourceLineAttribute(fenceStart)} class="markdown-mermaid render-state-source" data-markdown-diagram="mermaid" data-artifact-renderer="mermaid" data-render-state="source">`
          + "<figcaption>Mermaid diagram</figcaption>"
          + '<div class="mermaid-render-target" data-mermaid-target aria-label="Mermaid preview"></div>'
          + '<div class="mermaid-render-status" data-mermaid-status role="status">Mermaid source is preserved for deterministic preview rendering.</div>'
          + `<pre class="mermaid-source"><code>${renderMermaidSourceLines(source, firstSourceLine)}</code></pre>`
          + `<template class="mermaid-source-raw">${escapeHtml(source)}</template>`
        + "</figure>"
      );
    }

    function renderMarkdown(source) {
      const lines = String(source || "").split("\n");
      let html = "";
      let listTag = null;
      const closeList = () => {
        if (!listTag) return;
        html += `</${listTag}>`;
        listTag = null;
      };
      for (let index = 0; index < lines.length; index += 1) {
        const line = lines[index];
        const fence = line.match(/^```\s*([a-zA-Z0-9_-]+)?\s*$/);
        if (fence) {
          closeList();
          const language = (fence[1] || "").toLowerCase();
          const start = index;
          const body = [];
          index += 1;
          while (index < lines.length && !/^```\s*$/.test(lines[index])) {
            body.push(lines[index]);
            index += 1;
          }
          const blockSource = body.join("\n");
          if (language === "mermaid") {
            html += renderMermaidBlock(blockSource, start);
          } else {
            html += `<pre${sourceLineAttribute(start)}><code${language ? ` data-language="${escapeHtml(language)}"` : ""}>${escapeHtml(blockSource)}</code></pre>`;
          }
          continue;
        }
        const heading = line.match(/^(#{1,3})\s+(.+)/);
        if (heading) {
          closeList();
          const depth = heading[1].length;
          html += `<h${depth}${sourceLineAttribute(index)}>${renderInlineMarkdown(heading[2])}</h${depth}>`;
          continue;
        }
        if (/^---+$/.test(line.trim())) {
          closeList();
          html += `<hr${sourceLineAttribute(index)}>`;
          continue;
        }
        const unordered = line.match(/^[-*]\s+(.+)/);
        if (unordered) {
          if (listTag !== "ul") {
            closeList();
            html += "<ul>";
            listTag = "ul";
          }
          html += `<li${sourceLineAttribute(index)}>${renderInlineMarkdown(unordered[1])}</li>`;
          continue;
        }
        const ordered = line.match(/^\d+\.\s+(.+)/);
        if (ordered) {
          if (listTag !== "ol") {
            closeList();
            html += "<ol>";
            listTag = "ol";
          }
          html += `<li${sourceLineAttribute(index)}>${renderInlineMarkdown(ordered[1])}</li>`;
          continue;
        }
        if (!line.trim()) {
          closeList();
          continue;
        }
        closeList();
        html += `<p${sourceLineAttribute(index)}>${renderInlineMarkdown(line)}</p>`;
      }
      closeList();
      return html;
    }

    function markdownDiagnostics(content) {
      const lines = String(content || "").split("\n");
      const words = String(content || "").trim() ? String(content || "").trim().split(/\s+/).length : 0;
      const headings = lines
        .map((line, index) => ({ match: line.match(/^(#{1,6})\s+(.+)$/), line: index + 1 }))
        .filter((item) => item.match)
        .map((item) => ({ depth: item.match[1].length, text: item.match[2].trim(), line: item.line }));
      return { line_count: content ? lines.length : 0, word_count: words, heading_count: headings.length, headings };
    }

    function formatZoomPercent(value) {
      const rounded = Math.round(value * 10) / 10;
      return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(1)}%`;
    }

    function configuredZoomPercent(key, fallback) {
      const value = Number(app.viewerConfig[key]);
      return Number.isFinite(value) && value > 0 ? value : fallback;
    }

    function effectiveMinimumZoomPercent() {
      const image = $("artifact-image");
      const configuredZoomOut = configuredZoomPercent("maxZoomOutPercent", 10);
      if (!image.naturalWidth || !image.naturalHeight) {
        return configuredZoomOut;
      }
      return Math.min(configuredZoomOut, stageFitZoom());
    }

    function clampZoom(value) {
      const next = Number(value) || configuredZoomPercent("actualSizePercent", 100);
      const minZoom = effectiveMinimumZoomPercent();
      const maxZoom = Math.max(minZoom, configuredZoomPercent("maxZoomInPercent", 400));
      return Math.min(maxZoom, Math.max(minZoom, next));
    }

    function stageViewportSize() {
      const stage = $("stage");
      const style = window.getComputedStyle(stage);
      const width = stage.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      const height = stage.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
      return {
        width: Math.max(1, width),
        height: Math.max(1, height),
      };
    }

    function renderedImageSize(zoomPercent = app.zoomPercent) {
      const image = $("artifact-image");
      return {
        width: image.naturalWidth * zoomPercent / 100,
        height: image.naturalHeight * zoomPercent / 100,
      };
    }

    function updateImageAlignment() {
      const image = $("artifact-image");
      if (!image.naturalWidth) return;
      const stageSize = stageViewportSize();
      const imageSize = renderedImageSize();
      const fitTolerance = 1;
      $("image-wrap").classList.toggle(
        "centered",
        imageSize.width <= stageSize.width + fitTolerance
          && imageSize.height <= stageSize.height + fitTolerance
      );
    }

    function updateMooringOverlays() {
      if (app.editing) {
        placeSelectionForAnchor(app.editing.anchor);
        placePopoverForAnchor(app.editing.anchor);
      } else if (app.pendingAnchor && app.editorMode === "create" && !$("comment-popover").hidden) {
        placeSelectionForAnchor(app.pendingAnchor);
        placePopoverForAnchor(app.pendingAnchor);
      }
      if (app.activeMarker) {
        const note = annotationById(app.activeMarker.artifactId, app.activeMarker.annotationId);
        if (note && artifact().id === app.activeMarker.artifactId) {
          placeMarkerForAnchor(note.anchor);
        }
      }
    }

    function applyZoom(value, mode = "manual") {
      const image = $("artifact-image");
      app.zoomPercent = clampZoom(value);
      app.zoomMode = mode;
      $("zoom-input").value = formatZoomPercent(app.zoomPercent);
      if (image.naturalWidth) {
        image.style.width = `${Math.max(1, image.naturalWidth * app.zoomPercent / 100)}px`;
      }
      updateImageAlignment();
      updateMooringOverlays();
    }

    function stageFitZoom() {
      const image = $("artifact-image");
      if (!image.naturalWidth || !image.naturalHeight) return 100;
      const stageSize = stageViewportSize();
      const smallerThanStageAt100 =
        image.naturalWidth <= stageSize.width && image.naturalHeight <= stageSize.height;
      if (smallerThanStageAt100) {
        return configuredZoomPercent("actualSizePercent", 100);
      }
      return Math.min(stageSize.width / image.naturalWidth, stageSize.height / image.naturalHeight) * 100;
    }

    function smartFit() {
      const image = $("artifact-image");
      if (!image.naturalWidth || !image.naturalHeight) return;
      const stageSize = stageViewportSize();
      const smallerThanStageAt100 =
        image.naturalWidth <= stageSize.width && image.naturalHeight <= stageSize.height;
      if (smallerThanStageAt100 && app.zoomMode !== "actual-size") {
        applyZoom(configuredZoomPercent("actualSizePercent", 100), "actual-size");
        return;
      }
      applyZoom(stageFitZoom(), "stage-fit");
    }

    function updateDimensionReadout() {
      const item = artifact();
      if (isImageArtifact(item)) {
        const dimensions = item.dimensions || {};
        const width = dimensions.width || $("artifact-image").naturalWidth || "unknown";
        const height = dimensions.height || $("artifact-image").naturalHeight || "unknown";
        $("dimension-readout").textContent = `${width} x ${height} px`;
        return;
      }
      const content = app.markdownContent[item.id] || "";
      const diagnostics = markdownDiagnostics(content);
      $("dimension-readout").textContent = `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
    }

    function afterImageReady(callback) {
      const image = $("artifact-image");
      if (image.complete && image.naturalWidth) {
        callback();
        return;
      }
      image.addEventListener("load", callback, { once: true });
    }

    function setArtifact(index) {
      const count = app.collection.artifacts.length;
      app.index = (index + count) % count;
      closeEditor();
      hideAnnotationMarker();
      render();
    }

    function move(delta) {
      const indexes = visibleArtifactIndexes();
      if (!indexes.length) return;
      const current = indexes.includes(app.index) ? indexes.indexOf(app.index) : 0;
      const next = indexes[(current + delta + indexes.length) % indexes.length];
      setArtifact(next);
    }

    function renderTitle() {
      const item = artifact();
      const projected = projectedArtifact(item);
      const slot = projectedSlot(item);
      const workflow = app.workbenchProjection?.workflow;
      const composite = activeComposite();
      const slotLabel = slot?.label || projected?.slot;
      const slotHtml = slotLabel ? `<span class="slot-pill">${escapeHtml(slotLabel)}</span>` : "";
      const breadcrumbHtml = composite
        ? `<span class="artifact-breadcrumb">${escapeHtml(workflow?.name || "Workflow")} -&gt; ${escapeHtml(composite.label || composite.id)}</span>`
        : "";
      $("artifact-title").innerHTML = `${breadcrumbHtml}<span class="artifact-heading">${escapeHtml(item.name)} ${slotHtml} <span class="artifact-time">(${escapeHtml(formatTime(item.created_at_epoch))})</span></span>`;
    }

    function renderImage() {
      const item = artifact();
      const image = $("artifact-image");
      $("stage").classList.remove("markdown-stage");
      $("image-wrap").hidden = false;
      $("markdown-wrap").hidden = true;
      $("image-controls").style.display = "flex";
      $("markdown-controls").classList.remove("visible");
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
      resetHoverMarker();
      $("comment-popover").hidden = true;
      updateDimensionReadout();
      image.onload = () => {
        updateDimensionReadout();
        if (app.zoomMode === "stage-fit") {
          applyZoom(stageFitZoom(), "stage-fit");
        } else if (app.zoomMode === "actual-size") {
          applyZoom(100, "actual-size");
        } else {
          applyZoom(app.zoomPercent, "manual");
        }
      };
      image.src = artifactUrl(item);
      image.alt = item.name;
      if (image.complete && image.naturalWidth) {
        image.onload();
      }
    }

    async function loadMarkdown(item) {
      if (Object.prototype.hasOwnProperty.call(app.markdownContent, item.id)) return app.markdownContent[item.id];
      const response = await fetch(artifactUrl(item), { cache: "no-store" });
      if (!response.ok) throw new Error(`Markdown fetch failed: ${response.status}`);
      const content = await response.text();
      app.markdownContent[item.id] = content;
      app.markdownSavedContent[item.id] = content;
      app.markdownDirty[item.id] = false;
      return content;
    }

    function syncMarkdownModeButtons() {
      for (const button of document.querySelectorAll("[data-markdown-mode]")) {
        const active = button.dataset.markdownMode === app.markdownMode;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      }
    }

    function renderMarkdownBody(item) {
      const content = app.markdownContent[item.id] || "";
      $("markdown-preview").innerHTML = renderMarkdown(content);
      if (window.ArtifactPrimitives?.mermaid && app.markdownMode === "preview") {
        void window.ArtifactPrimitives.mermaid.upgradeMermaidBlocks($("markdown-preview"));
      }
      $("markdown-source").value = content;
      $("markdown-preview").hidden = app.markdownMode !== "preview";
      $("markdown-source").hidden = app.markdownMode !== "source";
      $("markdown-save").disabled = !app.markdownDirty[item.id];
      syncMarkdownModeButtons();
      updateDimensionReadout();
      renderMarkdownHighlights();
    }

    function renderMarkdownHighlights() {
      $("markdown-preview").querySelectorAll(".line-hit").forEach((node) => node.classList.remove("line-hit"));
      if (app.markdownMode !== "preview" || !isMarkdownArtifact()) return;
      for (const note of artifactAnnotations(artifact().id)) {
        const anchor = textRangeAnchor(note);
        if (!anchor) continue;
        for (const node of markdownLineElementsForRange(anchor)) {
          node.classList.add("line-hit");
        }
      }
      if (app.pendingAnchor?.type === "text_range") {
        for (const node of markdownLineElementsForRange(app.pendingAnchor)) {
          node.classList.add("line-hit");
        }
      }
    }

    async function renderMarkdownArtifact() {
      const item = artifact();
      $("stage").classList.add("markdown-stage");
      $("image-wrap").hidden = true;
      $("markdown-wrap").hidden = false;
      $("image-controls").style.display = "none";
      $("markdown-controls").classList.add("visible");
      $("selection").hidden = true;
      resetHoverMarker();
      $("comment-popover").hidden = true;
      try {
        await loadMarkdown(item);
        renderMarkdownBody(item);
      } catch (error) {
        $("markdown-preview").hidden = false;
        $("markdown-source").hidden = true;
        $("markdown-preview").innerHTML = `<p>Failed to load markdown: ${escapeHtml(error.message)}</p>`;
      }
    }

    async function saveMarkdownArtifact() {
      const item = artifact();
      if (!isMarkdownArtifact(item)) return;
      const content = app.markdownContent[item.id] || "";
      const response = await fetch(`/api/artifact-content/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        headers: { "content-type": "text/markdown; charset=utf-8" },
        body: content,
      });
      if (!response.ok) {
        showToast("Markdown save failed");
        return;
      }
      app.markdownSavedContent[item.id] = content;
      app.markdownDirty[item.id] = false;
      renderMarkdownBody(item);
      showToast("Markdown saved");
    }

    function revertMarkdownArtifact() {
      const item = artifact();
      if (!isMarkdownArtifact(item)) return;
      app.markdownContent[item.id] = app.markdownSavedContent[item.id] || "";
      app.markdownDirty[item.id] = false;
      renderMarkdownBody(item);
      showToast("Markdown reverted");
    }

    function setMarkdownMode(mode) {
      app.markdownMode = mode === "source" ? "source" : "preview";
      renderMarkdownBody(artifact());
      if (app.markdownMode === "source") $("markdown-source").focus();
    }

    function renderArtifact() {
      if (isMarkdownArtifact()) {
        void renderMarkdownArtifact();
        return;
      }
      renderImage();
    }

    function renderOverview() {
      $("overview-popover").innerHTML = visibleArtifactIndexes().map((index) => {
        const item = app.collection.artifacts[index];
        return `
        <button class="artifact-option ${index === app.index ? "active" : ""}" type="button" data-index="${index}">
          <span>${escapeHtml(item.name)}</span>
          <span class="small">${escapeHtml(artifactProjectionLine(item))}</span>
        </button>
      `;
      }).join("");
      $("overview-popover").querySelectorAll("[data-index]").forEach((button) => {
        button.addEventListener("click", () => {
          $("overview-popover").hidden = true;
          setArtifact(Number(button.dataset.index));
        });
      });
    }

    function artifactProjectionLine(item) {
      const projected = projectedArtifact(item);
      if (!projected) return `${item.type || "file"} · ${item.path}`;
      const step = projectedStep(item);
      const parts = [
        projected.slot || item.type || "file",
        projected.source_page?.slug,
        step?.status,
      ].filter(Boolean);
      return `${parts.join(" · ")} · ${item.path}`;
    }

    function filterSteps() {
      const stepIds = [...new Set(
        app.collection.artifacts
          .map((item) => projectedArtifact(item)?.produced_by_step_id)
          .filter(Boolean)
      )];
      return stepIds
        .map((stepId) => app.projectedStepsById[stepId])
        .filter(Boolean)
        .sort((a, b) => String(a.name || a.id).localeCompare(String(b.name || b.id)));
    }

    function filterSlots() {
      const slotValues = [...new Set(
        app.collection.artifacts
          .map((item) => projectedArtifact(item)?.slot)
          .filter(Boolean)
      )].sort();
      return slotValues.map((slot) => app.projectedSlotsByValue[slot] || { value: slot, label: formatSlot(slot) });
    }

    function filterComposites() {
      return Object.values(app.projectedGroupsById)
        .filter((group) => Array.isArray(group.artifact_ids)
          && group.artifact_ids.some((artifactId) => artifactIndexById(artifactId) >= 0))
        .sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)));
    }

    function filterSummaryText() {
      const total = app.collection.artifacts.length;
      const visible = visibleArtifactIndexes().length;
      return visible === total ? `${total} artifacts` : `${visible} of ${total} artifacts`;
    }

    function setWorkbenchFilter(kind, value) {
      if (kind === "step") {
        app.filters.stepId = app.filters.stepId === value ? null : value;
      }
      if (kind === "slot") {
        app.filters.slot = app.filters.slot === value ? null : value;
      }
      if (kind === "composite") {
        app.filters.compositeId = app.filters.compositeId === value ? null : value;
      }
      ensureVisibleArtifactSelected();
      closeEditor();
      hideAnnotationMarker();
      render();
    }

    function renderWorkflowHeader() {
      const workflow = app.workbenchProjection?.workflow;
      if (!workflow) {
        return "";
      }
      const reviewableProjectionCount = app.collection.artifacts
        .filter((item) => Boolean(projectedArtifact(item))).length;
      const steps = filterSteps();
      const slots = filterSlots();
      const composites = filterComposites();
      return `
        <div class="workflow-summary">
          <div class="summary-kicker">${escapeHtml(workflow.status || "unknown")}</div>
          <div class="summary-title">${escapeHtml(workflow.name || "Workflow")}</div>
          <div class="summary-grid">
            <span>${escapeHtml(String((workflow.steps || []).length))} steps</span>
            <span>${escapeHtml(String(reviewableProjectionCount))} reviewable</span>
            <span>${escapeHtml(String(slots.length))} slots</span>
            <span>${escapeHtml(String(composites.length))} composites</span>
          </div>
          <div class="filter-line">
            <span>${escapeHtml(filterSummaryText())}</span>
            ${(app.filters.stepId || app.filters.slot || app.filters.compositeId) ? '<button type="button" data-filter-kind="clear">Clear</button>' : ""}
          </div>
          <div class="filter-group" aria-label="Workflow step filters">
            ${steps.map((step) => `
              <button class="${step.id === app.filters.stepId ? "active" : ""}" type="button" data-filter-kind="step" data-filter-value="${escapeHtml(step.id)}">
                ${escapeHtml(String(step.name || step.id).replace(/^Capture /, ""))}
              </button>
            `).join("")}
          </div>
          <div class="filter-group" aria-label="Slot filters">
            ${slots.map((slot) => `
              <button class="${slot.value === app.filters.slot ? "active" : ""}" type="button" data-filter-kind="slot" data-filter-value="${escapeHtml(slot.value)}">
                ${escapeHtml(slot.label || formatSlot(slot.value))}
              </button>
            `).join("")}
          </div>
          <div class="filter-group" aria-label="Composite filters">
            ${composites.map((group) => `
              <button class="${group.id === app.filters.compositeId ? "active" : ""}" type="button" data-filter-kind="composite" data-filter-value="${escapeHtml(group.id)}">
                ${escapeHtml(group.label || group.id)}
              </button>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderSidebar() {
      const artifactRows = visibleArtifactIndexes().map((index) => {
        const item = app.collection.artifacts[index];
        const notes = artifactAnnotations(item.id);
        const projected = projectedArtifact(item);
        const step = projectedStep(item);
        const slot = projectedSlot(item);
        const annotationHtml = notes.length
          ? notes.map((note) => `
            <div class="annotation" draggable="true" data-artifact-id="${escapeHtml(item.id)}" data-annotation-id="${escapeHtml(note.id)}">
              <div class="annotation-text" title="${escapeHtml(note.comment)}">${escapeHtml(note.comment)}</div>
              <div class="small">${escapeHtml(anchorSummary(note.anchor))}</div>
            </div>
          `).join("")
          : "";
        return `
          <div class="artifact-row ${index === app.index ? "active" : ""}" data-index="${index}">
            <div class="row-title">
              ${artifactTypeIcon(item)}
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
      }).join("");
      $("sidebar").innerHTML = renderWorkflowHeader()
        + (artifactRows || '<div class="empty-filter">No artifacts match the active filters.</div>');
      $("sidebar").querySelectorAll("[data-filter-kind]").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          if (button.dataset.filterKind === "clear") {
            app.filters.stepId = null;
            app.filters.slot = null;
            app.filters.compositeId = null;
            ensureVisibleArtifactSelected();
            render();
            return;
          }
          setWorkbenchFilter(button.dataset.filterKind, button.dataset.filterValue);
        });
      });
      $("sidebar").querySelectorAll(".artifact-row[data-index]").forEach((row) => {
        row.addEventListener("click", (event) => {
          if (event.target.closest(".annotation")) return;
          setArtifact(Number(row.dataset.index));
        });
      });
      $("sidebar").querySelectorAll(".annotation").forEach((row) => {
        row.addEventListener("mouseenter", () => showAnnotationMarker(row.dataset.artifactId, row.dataset.annotationId));
        row.addEventListener("mouseleave", hideAnnotationMarker);
        row.addEventListener("click", (event) => {
          event.stopPropagation();
          selectAnnotation(row.dataset.artifactId, row.dataset.annotationId);
        });
        row.addEventListener("dragstart", (event) => {
          row.classList.add("dragging");
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", JSON.stringify({
            artifactId: row.dataset.artifactId,
            annotationId: row.dataset.annotationId,
          }));
        });
        row.addEventListener("dragend", () => row.classList.remove("dragging"));
        row.addEventListener("dragover", (event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
        });
        row.addEventListener("drop", async (event) => {
          event.preventDefault();
          const targetArtifactId = row.dataset.artifactId;
          const targetAnnotationId = row.dataset.annotationId;
          const payload = JSON.parse(event.dataTransfer.getData("text/plain") || "{}");
          if (payload.artifactId !== targetArtifactId || payload.annotationId === targetAnnotationId) return;
          const notes = [...artifactAnnotations(targetArtifactId)];
          const from = notes.findIndex((note) => note.id === payload.annotationId);
          const to = notes.findIndex((note) => note.id === targetAnnotationId);
          if (from < 0 || to < 0) return;
          const [moved] = notes.splice(from, 1);
          notes.splice(to, 0, moved);
          app.annotations[targetArtifactId] = notes;
          await syncAnnotations();
          renderSidebar();
        });
      });
    }

    function renderShell() {
      $("shell").classList.toggle("sidebar-hidden", !app.sidebarVisible);
    }

    function render() {
      renderTitle();
      renderArtifact();
      renderOverview();
      renderSidebar();
      renderShell();
    }

    function imagePoint(event) {
      const image = $("artifact-image");
      const rect = image.getBoundingClientRect();
      const x = Math.min(Math.max(event.clientX - rect.left, 0), rect.width);
      const y = Math.min(Math.max(event.clientY - rect.top, 0), rect.height);
      return { x, y };
    }

    function placeSelection(displayRect) {
      const selection = $("selection");
      const imageRect = $("artifact-image").getBoundingClientRect();
      const wrapRect = $("image-wrap").getBoundingClientRect();
      selection.style.left = `${displayRect.x + imageRect.left - wrapRect.left}px`;
      selection.style.top = `${displayRect.y + imageRect.top - wrapRect.top}px`;
      selection.style.width = `${displayRect.width}px`;
      selection.style.height = `${displayRect.height}px`;
      selection.hidden = false;
    }

    function displayRectFromNatural(rect) {
      const image = $("artifact-image");
      const imageRect = image.getBoundingClientRect();
      const sx = imageRect.width / image.naturalWidth;
      const sy = imageRect.height / image.naturalHeight;
      return {
        x: rect.x * sx,
        y: rect.y * sy,
        width: rect.width * sx,
        height: rect.height * sy,
      };
    }

    function markdownLineElementsForRange(anchor) {
      if (!anchor?.start?.line || !anchor?.end?.line) return [];
      const start = Math.min(anchor.start.line, anchor.end.line);
      const end = Math.max(anchor.start.line, anchor.end.line);
      return [...$("markdown-preview").querySelectorAll("[data-source-line]")]
        .filter((node) => {
          const line = Number(node.dataset.sourceLine);
          return line >= start && line <= end;
        });
    }

    function markdownDisplayRectFromAnchor(anchor) {
      const elements = markdownLineElementsForRange(anchor);
      if (!elements.length) return null;
      const wrapRect = $("markdown-wrap").getBoundingClientRect();
      const rects = elements.map((node) => node.getBoundingClientRect());
      const left = Math.min(...rects.map((rect) => rect.left));
      const top = Math.min(...rects.map((rect) => rect.top));
      const right = Math.max(...rects.map((rect) => rect.right));
      const bottom = Math.max(...rects.map((rect) => rect.bottom));
      return {
        x: left - wrapRect.left,
        y: top - wrapRect.top,
        width: right - left,
        height: bottom - top,
      };
    }

    function placeSelectionForRect(rect) {
      placeSelection(displayRectFromNatural(rect));
    }

    function placePopoverForRect(rect) {
      openComment(displayRectFromNatural(rect));
    }

    function placeSelectionForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        $("markdown-marker").hidden = true;
        placeSelectionForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        $("selection").hidden = true;
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (!displayRect) return;
        const marker = $("markdown-marker");
        marker.style.left = `${displayRect.x}px`;
        marker.style.top = `${displayRect.y}px`;
        marker.style.width = `${displayRect.width}px`;
        marker.style.height = `${displayRect.height}px`;
        marker.hidden = false;
      }
    }

    function placePopoverForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        placePopoverForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (displayRect) openComment(displayRect, $("markdown-wrap"));
      }
    }

    function placeMarkerForRect(rect) {
      const marker = $("hover-marker");
      const displayRect = displayRectFromNatural(rect);
      const imageRect = $("artifact-image").getBoundingClientRect();
      const wrapRect = $("image-wrap").getBoundingClientRect();
      marker.style.left = `${displayRect.x + displayRect.width / 2 + imageRect.left - wrapRect.left}px`;
      marker.style.top = `${displayRect.y + displayRect.height / 2 + imageRect.top - wrapRect.top}px`;
      showHoverMarker();
    }

    function clearHoverMarkerTimers() {
      for (const timer of app.hoverMarkerTimers) clearTimeout(timer);
      app.hoverMarkerTimers = [];
    }

    function queueHoverMarkerStep(delay, callback) {
      const timer = setTimeout(() => {
        app.hoverMarkerTimers = app.hoverMarkerTimers.filter((item) => item !== timer);
        callback();
      }, delay);
      app.hoverMarkerTimers.push(timer);
    }

    function showHoverMarker() {
      const marker = $("hover-marker");
      clearHoverMarkerTimers();
      marker.classList.remove("is-visible", "has-glow");
      marker.hidden = false;
      void marker.offsetWidth;
      marker.classList.add("is-visible");
      queueHoverMarkerStep(350, () => marker.classList.add("has-glow"));
      queueHoverMarkerStep(450, () => marker.classList.remove("has-glow"));
      queueHoverMarkerStep(550, () => marker.classList.add("has-glow"));
    }

    function hideHoverMarker() {
      const marker = $("hover-marker");
      clearHoverMarkerTimers();
      marker.classList.remove("has-glow", "is-visible");
      queueHoverMarkerStep(250, () => {
        if (!marker.classList.contains("is-visible")) marker.hidden = true;
      });
    }

    function resetHoverMarker() {
      const marker = $("hover-marker");
      clearHoverMarkerTimers();
      marker.classList.remove("has-glow", "is-visible");
      marker.hidden = true;
    }

    function placeMarkerForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        $("markdown-marker").hidden = true;
        placeMarkerForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        hideHoverMarker();
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (!displayRect) return;
        const marker = $("markdown-marker");
        marker.style.left = `${displayRect.x}px`;
        marker.style.top = `${displayRect.y}px`;
        marker.style.width = `${displayRect.width}px`;
        marker.style.height = `${displayRect.height}px`;
        marker.hidden = false;
      }
    }

    function hideAnnotationMarker() {
      app.activeMarker = null;
      hideHoverMarker();
      $("markdown-marker").hidden = true;
    }

    function showAnnotationMarker(artifactId, annotationId) {
      const note = annotationById(artifactId, annotationId);
      if (!note) return;
      app.activeMarker = { artifactId, annotationId };
      const index = artifactIndexById(artifactId);
      if (index !== app.index) {
        setArtifact(index);
        app.activeMarker = { artifactId, annotationId };
        window.requestAnimationFrame(() => {
          if (isImageArtifact()) afterImageReady(() => placeMarkerForAnchor(note.anchor));
          else placeMarkerForAnchor(note.anchor);
        });
        return;
      }
      placeMarkerForAnchor(note.anchor);
    }

    function naturalRect(displayRect) {
      const image = $("artifact-image");
      const imageRect = image.getBoundingClientRect();
      const sx = image.naturalWidth / imageRect.width;
      const sy = image.naturalHeight / imageRect.height;
      return {
        x: Math.round(displayRect.x * sx),
        y: Math.round(displayRect.y * sy),
        width: Math.round(displayRect.width * sx),
        height: Math.round(displayRect.height * sy),
      };
    }

    function markdownPoint(event) {
      const rect = $("markdown-wrap").getBoundingClientRect();
      return {
        x: Math.min(Math.max(event.clientX - rect.left, 0), rect.width),
        y: Math.min(Math.max(event.clientY - rect.top, 0), rect.height),
      };
    }

    function placeMarkdownSelection(displayRect) {
      const marker = $("markdown-marker");
      marker.style.left = `${displayRect.x}px`;
      marker.style.top = `${displayRect.y}px`;
      marker.style.width = `${displayRect.width}px`;
      marker.style.height = `${displayRect.height}px`;
      marker.hidden = false;
    }

    function markdownAnchorFromDisplayRect(displayRect) {
      const wrapRect = $("markdown-wrap").getBoundingClientRect();
      const selectionRect = {
        left: wrapRect.left + displayRect.x,
        top: wrapRect.top + displayRect.y,
        right: wrapRect.left + displayRect.x + displayRect.width,
        bottom: wrapRect.top + displayRect.y + displayRect.height,
      };
      const hits = [...$("markdown-preview").querySelectorAll("[data-source-line]")]
        .map((node) => ({ node, rect: node.getBoundingClientRect(), line: Number(node.dataset.sourceLine) }))
        .filter(({ rect }) => rect.right >= selectionRect.left
          && rect.left <= selectionRect.right
          && rect.bottom >= selectionRect.top
          && rect.top <= selectionRect.bottom)
        .filter(({ line }) => Number.isFinite(line));
      if (!hits.length) return null;
      const startLine = Math.min(...hits.map((hit) => hit.line));
      const endLine = Math.max(...hits.map((hit) => hit.line));
      const content = app.markdownContent[artifact().id] || "";
      const lines = content.split("\n");
      const excerpt = lines.slice(startLine - 1, endLine).join("\n").slice(0, 600);
      return {
        type: "text_range",
        coordinate_space: "markdown_source",
        start: { line: startLine, column: 1 },
        end: { line: endLine, column: (lines[endLine - 1] || "").length + 1 },
        excerpt,
      };
    }

    function openComment(displayRect, relativeTo = $("artifact-image")) {
      const popover = $("comment-popover");
      const baseRect = relativeTo.getBoundingClientRect();
      const left = Math.min(baseRect.left + displayRect.x + displayRect.width + 10, window.innerWidth - 434);
      const top = Math.min(baseRect.top + displayRect.y, window.innerHeight - 190);
      popover.style.left = `${Math.max(14, left)}px`;
      popover.style.top = `${Math.max(14, top)}px`;
      popover.hidden = false;
      $("comment-text").focus();
    }

    function openCreateEditor(displayRect, relativeTo = $("artifact-image")) {
      app.editorMode = "create";
      app.editing = null;
      $("comment-text").value = "";
      $("secondary-comment-action").textContent = "Cancel";
      $("primary-comment-action").textContent = "Add Comment";
      openComment(displayRect, relativeTo);
    }

    function scrollRectIntoView(rect) {
      const image = $("artifact-image");
      const wrap = $("image-wrap");
      const stage = $("stage");
      if (!image.naturalWidth) return;
      const displayRect = displayRectFromNatural(rect);
      const targetLeft = wrap.offsetLeft + displayRect.x + displayRect.width / 2;
      const targetTop = wrap.offsetTop + displayRect.y + displayRect.height / 2;
      stage.scrollTo({
        left: Math.max(0, targetLeft - stage.clientWidth / 2),
        top: Math.max(0, targetTop - stage.clientHeight / 2),
        behavior: "auto",
      });
    }

    function scrollTextRangeIntoView(anchor) {
      if (!anchor?.start?.line) return;
      const target = $("markdown-preview").querySelector(`[data-source-line="${anchor.start.line}"]`);
      if (target) {
        target.scrollIntoView({ block: "center", inline: "nearest" });
        return;
      }
      const source = $("markdown-source");
      const lines = String(source.value || "").split("\n");
      const lineHeight = Number.parseFloat(window.getComputedStyle(source).lineHeight) || 21;
      source.scrollTop = Math.max(0, (Math.max(1, anchor.start.line) - 3) * lineHeight);
    }

    function openExistingEditor(note) {
      app.editorMode = "edit";
      app.editing = note;
      $("comment-text").value = note.comment;
      $("secondary-comment-action").textContent = "Delete";
      $("primary-comment-action").textContent = "Update";
      const anchor = note.anchor;
      if (anchor?.type === "image_region" && anchor.rect) {
        afterImageReady(() => {
          scrollRectIntoView(anchor.rect);
          window.requestAnimationFrame(() => {
            placeSelectionForAnchor(anchor);
            placePopoverForAnchor(anchor);
          });
        });
        return;
      }
      if (anchor?.type === "text_range") {
        if (app.markdownMode !== "preview") {
          app.markdownMode = "preview";
          renderMarkdownBody(artifact());
        }
        scrollTextRangeIntoView(anchor);
        window.requestAnimationFrame(() => {
          renderMarkdownHighlights();
          placeSelectionForAnchor(anchor);
          placePopoverForAnchor(anchor);
        });
      }
    }

    function closeEditor() {
      app.pendingAnchor = null;
      app.editing = null;
      app.editorMode = "create";
      $("comment-popover").hidden = true;
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
    }

    function selectAnnotation(artifactId, annotationId) {
      const index = artifactIndexById(artifactId);
      const note = annotationById(artifactId, annotationId);
      if (index < 0 || !note) return;
      if (index !== app.index) {
        app.index = index;
        render();
        window.requestAnimationFrame(() => openExistingEditor(note));
        return;
      }
      openExistingEditor(note);
    }

    function startDrag(event) {
      if (event.button !== 0) return;
      if (event.target.closest("#image-wrap")) {
        const point = imagePoint(event);
        app.drag = { type: "image", startX: point.x, startY: point.y };
        app.pendingAnchor = null;
        $("comment-popover").hidden = true;
        placeSelection({ x: point.x, y: point.y, width: 0, height: 0 });
        return;
      }
      if (app.markdownMode === "preview" && event.target.closest("#markdown-preview")) {
        const point = markdownPoint(event);
        app.drag = { type: "markdown", startX: point.x, startY: point.y };
        app.pendingAnchor = null;
        $("comment-popover").hidden = true;
        placeMarkdownSelection({ x: point.x, y: point.y, width: 0, height: 0 });
      }
    }

    function dragDisplayRect(point) {
      return {
        x: Math.min(app.drag.startX, point.x),
        y: Math.min(app.drag.startY, point.y),
        width: Math.abs(point.x - app.drag.startX),
        height: Math.abs(point.y - app.drag.startY),
      };
    }

    function moveDrag(event) {
      if (!app.drag) return;
      if (app.drag.type === "image") {
        placeSelection(dragDisplayRect(imagePoint(event)));
        return;
      }
      if (app.drag.type === "markdown") {
        placeMarkdownSelection(dragDisplayRect(markdownPoint(event)));
      }
    }

    function endDrag(event) {
      if (!app.drag) return;
      const type = app.drag.type;
      const displayRect = type === "markdown"
        ? dragDisplayRect(markdownPoint(event))
        : dragDisplayRect(imagePoint(event));
      app.drag = null;
      if (displayRect.width < 8 || displayRect.height < 8) {
        $("selection").hidden = true;
        $("markdown-marker").hidden = true;
        return;
      }
      if (type === "markdown") {
        const anchor = markdownAnchorFromDisplayRect(displayRect);
        if (!anchor) {
          $("markdown-marker").hidden = true;
          return;
        }
        app.pendingAnchor = anchor;
        renderMarkdownHighlights();
        openCreateEditor(displayRect, $("markdown-wrap"));
        return;
      }
      app.pendingAnchor = {
        type: "image_region",
        coordinate_space: "natural_image",
        rect: naturalRect(displayRect),
      };
      $("comment-popover").hidden = true;
      openCreateEditor(displayRect);
    }

    async function commitEditor() {
      const comment = $("comment-text").value.trim();
      if (!comment) return;
      if (app.editorMode === "edit" && app.editing) {
        app.editing.comment = comment;
        app.editing.updated_at_epoch = Math.floor(Date.now() / 1000);
        closeEditor();
        await syncAnnotations();
        renderSidebar();
        showToast("Comment updated");
        return;
      }
      if (!app.pendingAnchor) return;
      const item = artifact();
      const note = {
        id: `${item.id}-${Date.now().toString(36)}`,
        artifact_id: item.id,
        kind: "comment",
        anchor: app.pendingAnchor,
        comment,
        created_at_epoch: Math.floor(Date.now() / 1000),
        updated_at_epoch: null,
      };
      app.annotations[item.id] = [...artifactAnnotations(item.id), note];
      closeEditor();
      await syncAnnotations();
      renderSidebar();
      showToast("Comment added");
    }

    async function secondaryEditorAction() {
      if (app.editorMode === "edit" && app.editing) {
        const artifactId = app.editing.artifact_id;
        const noteId = app.editing.id;
        app.annotations[artifactId] = artifactAnnotations(artifactId).filter((note) => note.id !== noteId);
        closeEditor();
        await syncAnnotations();
        renderSidebar();
        showToast("Comment deleted");
        return;
      }
      closeEditor();
    }

    function insertTextAtCursor(input, value) {
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? input.value.length;
      const before = input.value.slice(0, start);
      const after = input.value.slice(end);
      const spacer = before && !before.endsWith(" ") ? " " : "";
      const text = `${spacer}${value}`.trimStart();
      input.value = `${before}${text}${after}`;
      const caret = before.length + text.length;
      input.focus();
      input.setSelectionRange(caret, caret);
    }

    function setupDictationControl({ buttonId, inputId }) {
      const button = $(buttonId);
      const input = $(inputId);
      let recognition = null;
      let state = "idle";

      const setState = (nextState) => {
        state = nextState;
        button.classList.toggle("recording", state === "recording");
        button.classList.toggle("transcribing", state === "transcribing");
        button.classList.toggle("error", state === "error");
        if (state === "recording") {
          button.title = "Stop dictation";
          button.setAttribute("aria-label", "Stop dictation");
        } else if (state === "transcribing") {
          button.title = "Transcribing";
          button.setAttribute("aria-label", "Transcribing");
        } else if (state === "error") {
          button.title = "Dictation unavailable";
          button.setAttribute("aria-label", "Dictation unavailable");
        } else {
          button.title = "Start dictation";
          button.setAttribute("aria-label", "Start dictation");
        }
      };

      button.addEventListener("click", () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          setState("error");
          showToast("Dictation unavailable");
          return;
        }
        if (state === "recording" && recognition) {
          setState("transcribing");
          recognition.stop();
          return;
        }
        recognition = new SpeechRecognition();
        recognition.interimResults = false;
        recognition.continuous = false;
        recognition.onstart = () => setState("recording");
        recognition.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map((result) => result[0]?.transcript || "")
            .join(" ")
            .trim();
          if (transcript) insertTextAtCursor(input, transcript);
        };
        recognition.onerror = () => {
          setState("error");
          showToast("Dictation unavailable");
        };
        recognition.onend = () => {
          recognition = null;
          if (state !== "error") setState("idle");
        };
        try {
          recognition.start();
        } catch (_error) {
          recognition = null;
          setState("error");
          showToast("Dictation unavailable");
        }
      });
    }

    function setupDictation() {
      setupDictationControl({ buttonId: "comment-dictation", inputId: "comment-text" });
    }

    function wireEvents() {
      $("prev").addEventListener("click", () => move(-1));
      $("next").addEventListener("click", () => move(1));
      $("overview").addEventListener("click", () => {
        $("overview-popover").hidden = !$("overview-popover").hidden;
        $("artifact-menu").hidden = true;
      });
      $("menu-button").addEventListener("click", () => {
        $("artifact-menu").hidden = !$("artifact-menu").hidden;
        $("overview-popover").hidden = true;
      });
      $("toggle-sidebar").addEventListener("click", () => {
        app.sidebarVisible = !app.sidebarVisible;
        renderShell();
      });
      $("copy-artifact").addEventListener("click", () => copyText(JSON.stringify(artifact(), null, 2)));
      $("copy-path").addEventListener("click", () => copyText(artifact().path));
      $("secondary-comment-action").addEventListener("click", secondaryEditorAction);
      $("primary-comment-action").addEventListener("click", commitEditor);
      $("zoom-in").addEventListener("click", () => applyZoom(app.zoomPercent + 10));
      $("zoom-out").addEventListener("click", () => applyZoom(app.zoomPercent - 10));
      $("zoom-input").addEventListener("change", () => applyZoom($("zoom-input").value.replace("%", "")));
      $("zoom-fit").addEventListener("click", smartFit);
      $("zoom-control").addEventListener("wheel", (event) => {
        event.preventDefault();
        applyZoom(app.zoomPercent + (event.deltaY < 0 ? 5 : -5));
      });
      $("markdown-preview-mode").addEventListener("click", () => setMarkdownMode("preview"));
      $("markdown-source-mode").addEventListener("click", () => setMarkdownMode("source"));
      $("markdown-save").addEventListener("click", saveMarkdownArtifact);
      $("markdown-revert").addEventListener("click", revertMarkdownArtifact);
      $("markdown-source").addEventListener("input", () => {
        const item = artifact();
        app.markdownContent[item.id] = $("markdown-source").value;
        app.markdownDirty[item.id] = app.markdownContent[item.id] !== app.markdownSavedContent[item.id];
        $("markdown-save").disabled = !app.markdownDirty[item.id];
        updateDimensionReadout();
      });
      $("markdown-source").addEventListener("keydown", (event) => {
        const key = String(event.key || "").toLowerCase();
        if ((event.metaKey || event.ctrlKey) && key === "s") {
          event.preventDefault();
          void saveMarkdownArtifact();
        }
        if (event.key !== "Tab") return;
        event.preventDefault();
        const input = $("markdown-source");
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const prefix = input.value.slice(0, start);
        const suffix = input.value.slice(end);
        input.value = `${prefix}  ${suffix}`;
        input.setSelectionRange(start + 2, start + 2);
        input.dispatchEvent(new Event("input"));
      });
      $("image-wrap").addEventListener("mousedown", startDrag);
      $("markdown-preview").addEventListener("mousedown", startDrag);
      $("artifact-image").addEventListener("dragstart", (event) => event.preventDefault());
      window.addEventListener("resize", () => {
        if (!isImageArtifact()) {
          updateMooringOverlays();
        } else if (app.zoomMode === "stage-fit") {
          applyZoom(stageFitZoom(), "stage-fit");
        } else {
          updateImageAlignment();
          updateMooringOverlays();
        }
      });
      $("stage").addEventListener("scroll", updateMooringOverlays);
      $("markdown-preview").addEventListener("scroll", updateMooringOverlays);
      $("markdown-source").addEventListener("scroll", updateMooringOverlays);
      $("stage").addEventListener("wheel", (event) => {
        if (!event.ctrlKey || !isImageArtifact()) return;
        event.preventDefault();
        applyZoom(app.zoomPercent + (event.deltaY < 0 ? 5 : -5));
      }, { passive: false });
      window.addEventListener("mousemove", moveDrag);
      window.addEventListener("mouseup", endDrag);
      document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") move(-1);
        if (event.key === "ArrowRight") move(1);
        if (event.key === "Escape") {
          $("overview-popover").hidden = true;
          $("artifact-menu").hidden = true;
          closeEditor();
          hideAnnotationMarker();
        }
      });
      document.addEventListener("click", (event) => {
        if (!event.target.closest(".popover") && !event.target.closest("#overview")) {
          $("overview-popover").hidden = true;
        }
        if (!event.target.closest(".menu") && !event.target.closest("#menu-button")) {
          $("artifact-menu").hidden = true;
        }
      });
      setupDictation();
    }

    async function boot() {
      const [stateResponse, projectionPayload] = await Promise.all([
        fetch("/api/annotation-state"),
        fetchWorkbenchProjection(),
      ]);
      const payload = await stateResponse.json();
      app.collection = payload.collection;
      app.annotations = payload.annotations || {};
      indexProjection(projectionPayload);
      if (!app.collection.artifacts.length) {
        $("stage").innerHTML = "<div class='small'>No artifacts found.</div>";
        return;
      }
      wireEvents();
      render();
    }

    boot().catch((error) => {
      $("stage").innerHTML = `<div class="small">Failed to load artifacts: ${escapeHtml(error.message)}</div>`;
    });
