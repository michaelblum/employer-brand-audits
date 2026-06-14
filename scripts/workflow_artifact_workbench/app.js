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
      documentContent: {},
      artifactDocumentTheme: "dark",
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
    const isDocumentArtifact = (item = artifact()) => ["json", "text", "log", "file"].includes(item.type);
    const markdownPreviewBody = () => $("markdown-preview-body");
    const annotationAnchor = (note) => note?.anchor || {};
    const imageRectAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "image_region" ? anchor.rect : null;
    };
    const textRangeAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "text_range" ? anchor : null;
    };
    const formatTime = (epoch) => {
      if (!epoch) return "";
      return new Date(epoch * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    };
    const formatSlot = (value) => String(value || "").replace(/[._-]/g, " ");
    const iconHref = (name) => `/assets/workflow-artifact-workbench-icons.svg#icon-artifact-${name}`;
    const interactionOverlay = () => window.ArtifactPrimitives.interactionOverlay;
    const workflowSidebar = () => window.ArtifactPrimitives.workflowSidebar;
    const workflowSidebarContext = () => ({
      artifacts: app.collection.artifacts,
      annotations: app.annotations,
      activeIndex: app.index,
      filters: app.filters,
      iconHref,
      projectedArtifactsById: app.projectedArtifactsById,
      projectedGroupsById: app.projectedGroupsById,
      projectedSlotsByValue: app.projectedSlotsByValue,
      projectedStepsById: app.projectedStepsById,
      workbenchProjection: app.workbenchProjection,
    });

    function visibleArtifactIndexes() {
      return workflowSidebar().visibleArtifactIndexes(workflowSidebarContext());
    }

    function ensureVisibleArtifactSelected() {
      const indexes = visibleArtifactIndexes();
      app.index = workflowSidebar().ensureVisibleArtifactIndex({
        currentIndex: app.index,
        visibleIndexes: indexes,
      });
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

    function imageViewerOptions() {
      return {
        imageEl: $("artifact-image"),
        wrapEl: $("image-wrap"),
        stageEl: $("stage"),
        zoomInputEl: $("zoom-input"),
        viewerConfig: app.viewerConfig,
      };
    }

    function updateImageAlignment() {
      window.ArtifactPrimitives.imageViewer.updateAlignment({
        ...imageViewerOptions(),
        zoomPercent: app.zoomPercent,
      });
    }

    function updateMooringOverlays() {
      const editorAnchor = interactionOverlay().mooredEditorAnchor({
        editing: app.editing,
        pendingAnchor: app.pendingAnchor,
        editorMode: app.editorMode,
        popoverHidden: $("comment-popover").hidden,
      });
      if (editorAnchor) {
        placeSelectionForAnchor(editorAnchor);
        placePopoverForAnchor(editorAnchor);
      }
      if (app.activeMarker) {
        const note = annotationById(app.activeMarker.artifactId, app.activeMarker.annotationId);
        const markerAnchor = interactionOverlay().mooredActiveMarkerAnchor({
          activeMarker: app.activeMarker,
          note,
          currentArtifactId: artifact().id,
        });
        if (markerAnchor) placeMarkerForAnchor(markerAnchor);
      }
    }

    function applyZoom(value, mode = "manual") {
      const result = window.ArtifactPrimitives.imageViewer.applyZoom({
        ...imageViewerOptions(),
        value,
        mode,
      });
      app.zoomPercent = result.zoomPercent;
      app.zoomMode = result.zoomMode;
      updateMooringOverlays();
    }

    function stageFitZoom() {
      return window.ArtifactPrimitives.imageViewer.stageFitZoom(imageViewerOptions());
    }

    function smartFitZoom() {
      return window.ArtifactPrimitives.imageViewer.smartFitZoom(imageViewerOptions());
    }

    function smartFit() {
      const result = window.ArtifactPrimitives.imageViewer.smartFit({
        ...imageViewerOptions(),
        currentZoomMode: app.zoomMode,
      });
      if (!result) return;
      applyZoom(result.value, result.mode);
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
      const diagnostics = window.ArtifactPrimitives.markdown.markdownDiagnostics(content);
      $("dimension-readout").textContent = `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
    }

    function updateDocumentReadout(item) {
      const content = app.documentContent[item.id] || "";
      const lines = content ? content.split("\n").length : 0;
      const size = item.size_bytes ? `${item.size_bytes} bytes` : "";
      $("dimension-readout").textContent = [item.type || "file", lines ? `${lines} lines` : "", size]
        .filter(Boolean)
        .join(" · ");
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
      $("stage").scrollTo({ left: 0, top: 0 });
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
          applyZoom(smartFitZoom(), "stage-fit");
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

    async function loadDocument(item) {
      if (Object.prototype.hasOwnProperty.call(app.documentContent, item.id)) return app.documentContent[item.id];
      if (item.type === "file") {
        app.documentContent[item.id] = "";
        return "";
      }
      const response = await fetch(artifactUrl(item), { cache: "no-store" });
      if (!response.ok) throw new Error(`Artifact fetch failed: ${response.status}`);
      const content = await response.text();
      app.documentContent[item.id] = content;
      return content;
    }

    function storedArtifactDocumentTheme() {
      return window.ArtifactPrimitives.markdownInteractions.storedTheme();
    }

    function setArtifactDocumentTheme(theme) {
      app.artifactDocumentTheme = window.ArtifactPrimitives.markdownInteractions.setTheme({
        theme,
        buttonEl: $("markdown-theme-toggle"),
      });
    }

    function renderMarkdownBody(item) {
      const content = app.markdownContent[item.id] || "";
      window.ArtifactPrimitives.markdownInteractions.renderMarkdownBody({
        content,
        mode: app.markdownMode,
        dirty: app.markdownDirty[item.id],
        previewBodyEl: markdownPreviewBody(),
        sourceEl: $("markdown-source"),
        previewEl: $("markdown-preview"),
        saveButtonEl: $("markdown-save"),
        themeButtonEl: $("markdown-theme-toggle"),
        theme: app.artifactDocumentTheme,
      });
      updateDimensionReadout();
      renderMarkdownHighlights();
    }

    function renderMarkdownHighlights() {
      markdownPreviewBody().querySelectorAll(".line-hit").forEach((node) => node.classList.remove("line-hit"));
      if (app.markdownMode !== "preview" || !isMarkdownArtifact()) return;
      for (const note of artifactAnnotations(artifact().id)) {
        const anchor = textRangeAnchor(note);
        if (!anchor) continue;
        for (const node of window.ArtifactPrimitives.markdownInteractions.lineElementsForRange({
          anchor,
          rootEl: markdownPreviewBody(),
        })) {
          node.classList.add("line-hit");
        }
      }
      if (app.pendingAnchor?.type === "text_range") {
        for (const node of window.ArtifactPrimitives.markdownInteractions.lineElementsForRange({
          anchor: app.pendingAnchor,
          rootEl: markdownPreviewBody(),
        })) {
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
        markdownPreviewBody().innerHTML = `<p>Failed to load markdown: ${escapeHtml(error.message)}</p>`;
      }
    }

    async function renderDocumentArtifact() {
      const item = artifact();
      $("stage").classList.add("markdown-stage");
      $("stage").scrollTo({ left: 0, top: 0 });
      $("image-wrap").hidden = true;
      $("markdown-wrap").hidden = false;
      $("image-controls").style.display = "none";
      $("markdown-controls").classList.remove("visible");
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
      resetHoverMarker();
      $("comment-popover").hidden = true;
      $("markdown-preview").hidden = false;
      $("markdown-source").hidden = true;
      try {
        const content = await loadDocument(item);
        if (!window.ArtifactPrimitives?.document) {
          throw new Error("Document renderer primitive is not loaded");
        }
        window.ArtifactPrimitives.document.renderDocumentArtifact(
          {
            ...item,
            content,
            url: artifactUrl(item),
            mimeType: item.mime_type,
            sizeBytes: item.size_bytes,
          },
          markdownPreviewBody(),
        );
      } catch (error) {
        markdownPreviewBody().innerHTML = `<p>Failed to load artifact: ${escapeHtml(error.message)}</p>`;
      }
      updateDocumentReadout(item);
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

    function toggleMarkdownTheme() {
      setArtifactDocumentTheme(app.artifactDocumentTheme === "dark" ? "light" : "dark");
    }

    function renderArtifact() {
      if (isMarkdownArtifact()) {
        void renderMarkdownArtifact();
        return;
      }
      if (isDocumentArtifact()) {
        void renderDocumentArtifact();
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
      return workflowSidebar().artifactProjectionLine({
        ...workflowSidebarContext(),
        item,
      });
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

    function renderSidebar() {
      $("sidebar").innerHTML = workflowSidebar().renderSidebarHtml(workflowSidebarContext());
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
      return window.ArtifactPrimitives.imageViewer.imagePoint({
        event,
        imageEl: $("artifact-image"),
      });
    }

    function placeSelection(displayRect) {
      window.ArtifactPrimitives.imageViewer.placeSelection({
        selectionEl: $("selection"),
        imageEl: $("artifact-image"),
        wrapEl: $("image-wrap"),
        displayRect,
      });
    }

    function displayRectFromNatural(rect) {
      return window.ArtifactPrimitives.imageViewer.displayRectFromNatural({
        rect,
        imageEl: $("artifact-image"),
      });
    }

    function placeSelectionForRect(rect) {
      placeSelection(displayRectFromNatural(rect));
    }

    function displayRectForAnchor(anchor) {
      return interactionOverlay().displayRectForAnchor({
        anchor,
        imageRegionRect: (rect) => displayRectFromNatural(rect),
        textRangeRect: (textAnchor) => window.ArtifactPrimitives.markdownInteractions.displayRectFromAnchor({
          anchor: textAnchor,
          rootEl: markdownPreviewBody(),
          wrapEl: $("markdown-wrap"),
        }),
      });
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
        const displayRect = displayRectForAnchor(anchor);
        if (!displayRect) return;
        interactionOverlay().placeOverlayBox({
          overlayEl: $("markdown-marker"),
          displayRect,
        });
      }
    }

    function placePopoverForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        placePopoverForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        const displayRect = displayRectForAnchor(anchor);
        if (displayRect) openComment(displayRect, $("markdown-wrap"));
      }
    }

    function placeMarkerForRect(rect) {
      window.ArtifactPrimitives.imageViewer.placeHoverMarker({
        markerEl: $("hover-marker"),
        imageEl: $("artifact-image"),
        wrapEl: $("image-wrap"),
        rect,
      });
    }

    function hideHoverMarker() {
      window.ArtifactPrimitives.imageViewer.hideHoverMarker($("hover-marker"));
    }

    function resetHoverMarker() {
      window.ArtifactPrimitives.imageViewer.resetHoverMarker($("hover-marker"));
    }

    function placeMarkerForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        $("markdown-marker").hidden = true;
        placeMarkerForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        hideHoverMarker();
        const displayRect = displayRectForAnchor(anchor);
        if (!displayRect) return;
        interactionOverlay().placeOverlayBox({
          overlayEl: $("markdown-marker"),
          displayRect,
        });
      }
    }

    function hideAnnotationMarker() {
      app.activeMarker = null;
      hideHoverMarker();
      $("markdown-marker").hidden = true;
    }

    function showAnnotationMarker(artifactId, annotationId) {
      const note = annotationById(artifactId, annotationId);
      const index = artifactIndexById(artifactId);
      const target = interactionOverlay().annotationOverlayTarget({
        artifactId,
        annotationId,
        artifactIndex: index,
        currentIndex: app.index,
        note,
      });
      if (!target) return;
      app.activeMarker = target.activeMarker;
      if (target.requiresArtifactSwitch) {
        setArtifact(target.artifactIndex);
        app.activeMarker = target.activeMarker;
        window.requestAnimationFrame(() => {
          if (isImageArtifact()) afterImageReady(() => placeMarkerForAnchor(target.note.anchor));
          else placeMarkerForAnchor(target.note.anchor);
        });
        return;
      }
      placeMarkerForAnchor(target.note.anchor);
    }

    function naturalRect(displayRect) {
      return window.ArtifactPrimitives.imageViewer.naturalRect({
        displayRect,
        imageEl: $("artifact-image"),
      });
    }

    function openComment(displayRect, relativeTo = $("artifact-image")) {
      window.ArtifactPrimitives.imageViewer.openAnchoredPopover({
        popoverEl: $("comment-popover"),
        inputEl: $("comment-text"),
        displayRect,
        relativeToEl: relativeTo,
      });
    }

    function setCommentActionLabels(mode) {
      const labels = interactionOverlay().editorLabels({ subtype: "annotation", mode });
      $("secondary-comment-action").textContent = labels.secondary;
      $("primary-comment-action").textContent = labels.primary;
    }

    function openCreateEditor(displayRect, relativeTo = $("artifact-image")) {
      Object.assign(app, interactionOverlay().createEditorSession({
        anchor: app.pendingAnchor,
      }));
      $("comment-text").value = "";
      setCommentActionLabels("create");
      openComment(displayRect, relativeTo);
    }

    function scrollRectIntoView(rect) {
      window.ArtifactPrimitives.imageViewer.scrollRectIntoView({
        rect,
        imageEl: $("artifact-image"),
        wrapEl: $("image-wrap"),
        stageEl: $("stage"),
      });
    }

    function openExistingEditor(note) {
      const plan = interactionOverlay().existingOverlayEditorPlan({
        note,
        markdownMode: app.markdownMode,
      });
      if (!plan) return;
      Object.assign(app, {
        editorMode: plan.editorMode,
        editing: plan.editing,
        pendingAnchor: plan.pendingAnchor,
      });
      $("comment-text").value = plan.comment;
      setCommentActionLabels(plan.actionMode);
      const anchor = plan.anchor;
      if (plan.placement?.type === "image_region") {
        afterImageReady(() => {
          scrollRectIntoView(plan.placement.rect);
          window.requestAnimationFrame(() => {
            placeSelectionForAnchor(anchor);
            placePopoverForAnchor(anchor);
          });
        });
        return;
      }
      if (plan.placement?.type === "text_range") {
        if (plan.placement.ensurePreview) {
          app.markdownMode = "preview";
          renderMarkdownBody(artifact());
        }
        window.ArtifactPrimitives.markdownInteractions.scrollTextRangeIntoView({
          anchor,
          previewBodyEl: markdownPreviewBody(),
          sourceEl: $("markdown-source"),
        });
        window.requestAnimationFrame(() => {
          renderMarkdownHighlights();
          placeSelectionForAnchor(anchor);
          placePopoverForAnchor(anchor);
        });
      }
    }

    function closeEditor() {
      Object.assign(app, interactionOverlay().closedEditorSession());
      $("comment-popover").hidden = true;
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
    }

    function selectAnnotation(artifactId, annotationId) {
      const index = artifactIndexById(artifactId);
      const note = annotationById(artifactId, annotationId);
      const target = interactionOverlay().annotationOverlayTarget({
        artifactId,
        annotationId,
        artifactIndex: index,
        currentIndex: app.index,
        note,
      });
      if (!target) return;
      if (target.requiresArtifactSwitch) {
        app.index = target.artifactIndex;
        render();
        window.requestAnimationFrame(() => openExistingEditor(target.note));
        return;
      }
      openExistingEditor(target.note);
    }

    function applyOverlayDraftStart(draft, placeDraftSelection) {
      if (!draft) return;
      app.drag = draft.drag;
      app.pendingAnchor = draft.pendingAnchor;
      $("comment-popover").hidden = draft.popoverHidden;
      placeDraftSelection(draft.displayRect);
    }

    function startDrag(event) {
      if (event.button !== 0) return;
      if (event.target.closest("#image-wrap")) {
        const point = imagePoint(event);
        applyOverlayDraftStart(interactionOverlay().beginOverlayDraft({
          type: "image",
          point,
        }), placeSelection);
        return;
      }
      if (isMarkdownArtifact() && app.markdownMode === "preview" && event.target.closest("#markdown-preview")) {
        const point = window.ArtifactPrimitives.markdownInteractions.pointInWrap({
          event,
          wrapEl: $("markdown-wrap"),
        });
        applyOverlayDraftStart(interactionOverlay().beginOverlayDraft({
          type: "markdown",
          point,
        }), (displayRect) => {
          window.ArtifactPrimitives.markdownInteractions.placeSelection({
            markerEl: $("markdown-marker"),
            displayRect,
          });
        });
      }
    }

    function dragDisplayRect(point) {
      return window.ArtifactPrimitives.imageViewer.dragDisplayRect({
        drag: app.drag,
        point,
      });
    }

    function moveDrag(event) {
      if (!app.drag) return;
      if (app.drag.type === "image") {
        placeSelection(dragDisplayRect(imagePoint(event)));
        return;
      }
      if (app.drag.type === "markdown") {
        window.ArtifactPrimitives.markdownInteractions.placeSelection({
          markerEl: $("markdown-marker"),
          displayRect: dragDisplayRect(window.ArtifactPrimitives.markdownInteractions.pointInWrap({
            event,
            wrapEl: $("markdown-wrap"),
          })),
        });
      }
    }

    function applyOverlayDraftCompletion(intent) {
      if (!intent) return true;
      app.drag = intent.drag;
      if (intent.action === "discard") {
        if (intent.hideSelection) $("selection").hidden = true;
        if (intent.hideMarkdownMarker) $("markdown-marker").hidden = true;
        return true;
      }
      if (intent.action === "create") {
        app.pendingAnchor = intent.pendingAnchor;
        if (intent.renderMarkdownHighlights) renderMarkdownHighlights();
        if (intent.hidePopover) $("comment-popover").hidden = true;
        openCreateEditor(
          intent.displayRect,
          intent.relativeTo === "markdown" ? $("markdown-wrap") : $("artifact-image"),
        );
        return true;
      }
      return false;
    }

    function endDrag(event) {
      if (!app.drag) return;
      const type = app.drag.type;
      const displayRect = type === "markdown"
        ? dragDisplayRect(window.ArtifactPrimitives.markdownInteractions.pointInWrap({
          event,
          wrapEl: $("markdown-wrap"),
        }))
        : dragDisplayRect(imagePoint(event));
      const draftCompletion = interactionOverlay().completeOverlayDraft({ type, displayRect });
      if (applyOverlayDraftCompletion(draftCompletion)) return;
      const anchor = type === "markdown"
        ? window.ArtifactPrimitives.markdownInteractions.anchorFromDisplayRect({
          displayRect,
          wrapEl: $("markdown-wrap"),
          rootEl: markdownPreviewBody(),
          content: app.markdownContent[artifact().id] || "",
        })
        : {
          type: "image_region",
          coordinate_space: "natural_image",
          rect: naturalRect(displayRect),
        };
      applyOverlayDraftCompletion(interactionOverlay().completeOverlayDraft({
        type,
        displayRect,
        anchorResolved: true,
        anchor,
      }));
    }

    async function applyOverlayEditorIntent(intent) {
      if (!intent) return;
      app.annotations = intent.annotations;
      if (intent.closeEditor) closeEditor();
      if (intent.syncAnnotations) await syncAnnotations();
      if (intent.renderSidebar) renderSidebar();
      if (intent.toast) showToast(intent.toast);
    }

    async function commitEditor() {
      await applyOverlayEditorIntent(interactionOverlay().commitOverlayEditorIntent({
        annotations: app.annotations,
        artifact: artifact(),
        editorMode: app.editorMode,
        editing: app.editing,
        pendingAnchor: app.pendingAnchor,
        comment: $("comment-text").value,
      }));
    }

    async function secondaryEditorAction() {
      await applyOverlayEditorIntent(interactionOverlay().secondaryOverlayEditorIntent({
        annotations: app.annotations,
        editorMode: app.editorMode,
        editing: app.editing,
      }));
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
      $("markdown-theme-toggle").addEventListener("click", toggleMarkdownTheme);
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
        window.ArtifactPrimitives.markdownInteractions.indentSelection($("markdown-source"));
      });
      $("image-wrap").addEventListener("mousedown", startDrag);
      $("markdown-preview").addEventListener("mousedown", startDrag);
      $("artifact-image").addEventListener("dragstart", (event) => event.preventDefault());
      window.addEventListener("resize", () => {
        if (!isImageArtifact()) {
          updateMooringOverlays();
        } else if (app.zoomMode === "stage-fit") {
          applyZoom(smartFitZoom(), "stage-fit");
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
      setArtifactDocumentTheme(storedArtifactDocumentTheme());
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
