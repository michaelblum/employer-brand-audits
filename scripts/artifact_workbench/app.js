    const DEFAULT_VIEWER_CONFIG = {
      maxZoomOutPercent: 10,
      maxZoomInPercent: 400,
      actualSizePercent: 100,
    };
    const app = {
      collection: null,
      interactionOverlays: [],
      contexts: [],
      context: null,
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
      artifactProjectionModel: null,
      markdownPreviewBodyClass: "",
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
    const escapeHtml = (value) => window.Artifacts.common.escapeHtml(value);
    const artifact = () => app.collection.artifacts[app.index];
    const artifactAnnotations = (id) => interactionOverlay().annotationOverlays(app.interactionOverlays, id);
    const artifactIndexById = (id) => app.collection.artifacts.findIndex((item) => item.id === id);
    const annotationById = (artifactId, annotationId) => artifactAnnotations(artifactId).find((note) => note.id === annotationId);
    const artifactUrl = (item) => `/artifact/${String(item.path || "").split("/").map(encodeURIComponent).join("/")}`;
    const artifactRegistry = () => window.Artifacts.registry;
    const artifactRenderer = () => window.ArtifactPrimitives.artifactRenderer;
    const artifactToolbar = () => window.WorkbenchArtifactToolbar;
    const artifactBinding = () => window.WorkbenchArtifactBinding;
    const documentRenderer = () => window.ArtifactPrimitives.document;
    const htmlRenderer = () => window.ArtifactPrimitives.html;
    const targetLink = () => window.ArtifactPrimitives.targetLink;
    const markdownPreviewBody = () => $("markdown-preview-body");
    const annotationAnchor = (note) => note?.anchor || {};
    const textRangeAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "text_range" ? anchor : null;
    };
    const formatTime = (epoch) => {
      if (!epoch) return "";
      return new Date(epoch * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    };
    const iconHref = (name) => `/assets/artifact-workbench-icons.svg#icon-artifact-${name}`;
    const interactionOverlay = () => window.ArtifactPrimitives.interactionOverlay;
    let overlayControllerInstance = null;
    let workflowTargetLinkEffect = null;
    let unbindHtmlInspector = null;
    let mooringOverlayFrame = null;
    let mooringOverlayRetry = null;
    function overlayController() {
      if (!overlayControllerInstance) {
        overlayControllerInstance = window.ArtifactPrimitives.interactionOverlayController
          .createInteractionOverlayController({
            overlay: interactionOverlay(),
            effects: {
              editor: {
                setInteractionOverlays: (interactionOverlays) => { app.interactionOverlays = interactionOverlays || []; },
                closeEditor,
                syncInteractionOverlays,
                renderSidebar,
                showToast,
              },
              editorShell: {
                setEditorSession: (session) => { Object.assign(app, session); },
                setCommentValue: (value) => { $("comment-text").value = value; },
                setActionLabels: (labels) => {
                  $("secondary-comment-action").textContent = labels.secondary;
                  $("primary-comment-action").textContent = labels.primary;
                },
                openComment: (displayRect, relativeTo) => openComment(
                  displayRect,
                  relativeTo === "markdown" ? $("markdown-wrap") : $("artifact-image"),
                ),
                hidePopover: () => { $("comment-popover").hidden = true; },
                hideSelection: () => { $("selection").hidden = true; },
                hideMarkdownMarker: () => { $("markdown-marker").hidden = true; },
                afterImageReady,
                scrollRectIntoView,
                requestAnimationFrame: (callback) => window.requestAnimationFrame(callback),
                placeSelectionForAnchor,
                placePopoverForAnchor,
                ensureMarkdownPreview: () => {
                  app.markdownMode = "preview";
                  renderMarkdownBody(artifact());
                },
                scrollTextRangeIntoView: (anchor) => {
                  window.ArtifactPrimitives.markdownInteractions.scrollTextRangeIntoView({
                    anchor,
                    previewBodyEl: markdownPreviewBody(),
                    sourceEl: $("markdown-source"),
                  });
                },
                scrollHtmlElementIntoView,
                renderMarkdownHighlights,
              },
              annotationTarget: {
                setActiveMarker: (marker) => { app.activeMarker = marker; },
                setArtifact,
                setIndex: (index) => { app.index = index; },
                render,
                requestAnimationFrame: (callback) => window.requestAnimationFrame(callback),
                afterImageReady,
                shouldWaitForImageReady: supportsImageRegionAnnotations,
                placeMarkerForAnchor,
                openExistingEditor,
              },
              draftStart: {
                setDrag: (drag) => { app.drag = drag; },
                setPendingAnchor: (pendingAnchor) => { app.pendingAnchor = pendingAnchor; },
                setPopoverHidden: (hidden) => { $("comment-popover").hidden = hidden; },
              },
              draftCompletion: {
                setDrag: (drag) => { app.drag = drag; },
                hideSelection: () => { $("selection").hidden = true; },
                hideMarkdownMarker: () => { $("markdown-marker").hidden = true; },
                setPendingAnchor: (pendingAnchor) => { app.pendingAnchor = pendingAnchor; },
                renderMarkdownHighlights,
                setPopoverHidden: (hidden) => { $("comment-popover").hidden = hidden; },
                openCreateEditor: (displayRect, relativeTo) => openCreateEditor(
                  displayRect,
                  relativeTo === "markdown" ? $("markdown-wrap") : $("artifact-image"),
                ),
              },
            },
          });
      }
      return overlayControllerInstance;
    }
    function workflowTargetLink() {
      if (!workflowTargetLinkEffect) {
        workflowTargetLinkEffect = targetLink().createTargetLinkEffect({
          targetClass: "workflow-paired",
        });
      }
      return workflowTargetLinkEffect;
    }
    const artifactNavigation = () => window.Artifacts.navigation;
    const workflowPairing = () => window.Artifacts.workflowPairing;
    const boundedInputControls = () => window.Artifacts.boundedInputControls;
    let artifactBindingInstance = null;
    const artifactNavigationContext = () => artifactNavigation().artifactNavigationContext({
      artifacts: app.collection.artifacts,
      interactionOverlays: app.interactionOverlays,
      contexts: app.contexts,
      context: app.context,
      activeIndex: app.index,
      filters: app.filters,
      iconHref,
      projectionModel: app.artifactProjectionModel,
    });

    function boundedInputDefinitionsForArtifact(item = artifact()) {
      const definitions = app.artifactProjectionModel?.workbenchProjection?.workflow?.input_overlays || [];
      return boundedInputControls().definitionsForArtifact(definitions, item);
    }

    function boundedInputValues() {
      const values = interactionOverlay().boundedInputOverlayValues(app.interactionOverlays);
      return values || {};
    }

    function renderBoundedInputLayer(item = artifact()) {
      const layer = $("bounded-input-layer");
      const definitions = boundedInputDefinitionsForArtifact(item);
      if (!definitions.length) {
        layer.hidden = true;
        layer.innerHTML = "";
        scheduleMooringOverlayUpdate();
        return;
      }
      layer.hidden = false;
      layer.innerHTML = boundedInputControls().renderLayerHtml(definitions, boundedInputValues());
      bindBoundedInputControls(definitions);
      scheduleMooringOverlayUpdate();
    }

    function closeBoundedSelectMenus(exceptRoot = null) {
      boundedInputControls().closeSelectMenus($("bounded-input-layer"), exceptRoot);
    }

    function bindBoundedInputControls(definitions = []) {
      boundedInputControls().bindControls({
        layerEl: $("bounded-input-layer"),
        definitions,
        onChange: ({ definition, value }) => {
          app.interactionOverlays = interactionOverlay().upsertBoundedInputOverlay({
            interactionOverlays: app.interactionOverlays,
            definition,
            value,
          });
          void syncInteractionOverlays();
        },
      });
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

    function hasUnsavedInteractionOverlays() {
      return app.interactionOverlays.some((overlay) => !overlay.resolved_at_epoch);
    }

    function applyWorkbenchStatePayload(payload) {
      app.collection = payload.collection;
      app.interactionOverlays = payload.interaction_overlays || [];
      app.contexts = payload.contexts || [];
      app.context = payload.context || null;
      app.artifactProjectionModel = artifactNavigation().artifactProjectionModel(payload.workbench_projection || null);
    }

    async function switchWorkbenchContext(manifest) {
      if (!manifest || manifest === app.context?.manifest) return;
      if (hasUnsavedInteractionOverlays()) {
        const discard = window.confirm("Switching workflows will discard current notes and input drafts.");
        if (!discard) {
          renderOverview();
          return;
        }
      }
      const response = await fetch("/api/workbench-context", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ manifest, changed_by: "human" }),
      });
      if (!response.ok) {
        showToast("Context switch failed");
        renderOverview();
        return;
      }
      const payload = await response.json();
      closeEditor();
      hideAnnotationMarker();
      app.index = 0;
      app.filters = { stepId: null, slot: null, compositeId: null };
      applyWorkbenchStatePayload(payload);
      render();
    }

    async function syncInteractionOverlays() {
      const response = await fetch("/api/workbench-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ interaction_overlays: app.interactionOverlays }),
      });
      if (!response.ok) {
        showToast("Overlay sync failed");
        return;
      }
      const payload = await response.json();
      app.interactionOverlays = payload.interaction_overlays || app.interactionOverlays;
    }

    async function syncWorkbenchViewState() {
      const current = artifact();
      if (!current) return;
      await fetch("/api/workbench-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          view: {
            active_artifact_id: current.id,
            active_index: app.index,
          },
        }),
      });
    }

    function scheduleMooringOverlayUpdate() {
      if (mooringOverlayFrame !== null) window.cancelAnimationFrame(mooringOverlayFrame);
      if (mooringOverlayRetry !== null) window.clearTimeout(mooringOverlayRetry);
      mooringOverlayFrame = window.requestAnimationFrame(() => {
        mooringOverlayFrame = null;
        updateMooringOverlays();
        mooringOverlayRetry = window.setTimeout(() => {
          mooringOverlayRetry = null;
          updateMooringOverlays();
        }, 160);
      });
    }

    function workflowPairingDefinition(item = artifact()) {
      return workflowPairing().definitionForArtifact(boundedInputDefinitionsForArtifact(item), item);
    }

    function elementForSelectorCandidates(rootEl, selectors = []) {
      if (!rootEl || typeof rootEl.querySelector !== "function") return null;
      for (const selector of selectors) {
        try {
          const match = rootEl.querySelector(selector);
          if (match) return match;
        } catch (_error) {
          // Selector candidates are fallbacks; invalid candidates should not block later selectors.
        }
      }
      return null;
    }

    function workflowDomAnchorForDefinition(definition) {
      return workflowPairing().domAnchorForDefinition(definition, { artifactId: artifact()?.id || "" });
    }

    function displayRectForDomAnchor(anchor, rootEl = markdownPreviewBody()) {
      return interactionOverlay().displayRectForAnchor({
        anchor,
        rootEl,
        relativeToEl: $("stage"),
      });
    }

    function displayRectForStageSelector(selector) {
      return displayRectForDomAnchor({
        type: "dom_element",
        coordinate_space: "workbench_stage",
        selector_candidates: [selector],
      }, $("stage"));
    }

    function clearWorkflowPairingOverlay() {
      const panel = $("bounded-input-layer").querySelector("[data-bounded-input-panel]");
      workflowTargetLink().clear({
        layerEl: $("target-pairing-layer"),
        highlightEl: $("target-pairing-highlight"),
        connectorSvgEl: $("target-pairing-connectors"),
        connectorPathEl: $("target-pairing-connector-path"),
        targetEl: panel,
        datasetKeys: ["workflowStepId"],
        targetDatasetKeys: ["pairing"],
      });
    }

    function updateWorkflowPairingOverlay() {
      const definition = workflowPairingDefinition();
      const panel = $("bounded-input-layer").querySelector("[data-bounded-input-panel]");
      if (!definition || !panel || $("bounded-input-layer").hidden || app.markdownMode !== "preview") {
        clearWorkflowPairingOverlay();
        return;
      }
      const workflowAnchor = workflowDomAnchorForDefinition(definition);
      const workflowElement = elementForSelectorCandidates(
        markdownPreviewBody(),
        workflowAnchor?.selector_candidates || [],
      );
      if (!workflowAnchor || !workflowElement) {
        clearWorkflowPairingOverlay();
        return;
      }
      workflowElement.dataset.workflowStepId = definition.step_id;
      const workflowRect = displayRectForDomAnchor(workflowAnchor);
      const panelRect = displayRectForStageSelector("[data-bounded-input-panel]");
      if (!workflowRect || !panelRect) {
        clearWorkflowPairingOverlay();
        return;
      }
      const layer = $("target-pairing-layer");
      const highlight = $("target-pairing-highlight");
      const svg = $("target-pairing-connectors");
      const path = $("target-pairing-connector-path");
      const result = workflowTargetLink().render({
        layerEl: layer,
        highlightEl: highlight,
        connectorSvgEl: svg,
        connectorPathEl: path,
        sourceRect: workflowRect,
        targetRect: panelRect,
        targetEl: panel,
        stageEl: $("stage"),
        interactionOverlay: interactionOverlay(),
        options: workflowPairing().targetLinkOptionsForDefinition(definition),
        dataset: { workflowStepId: definition.step_id },
        targetDataset: { pairing: "workflow-step" },
      });
      if (result.status !== "rendered") clearWorkflowPairingOverlay();
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
      updateWorkflowPairingOverlay();
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

    function supportsImageRegionAnnotations(item = artifact()) {
      return workbenchArtifactBinding().supports("imageRegionAnnotations", item);
    }

    function supportsImageZoom(item = artifact()) {
      return workbenchArtifactBinding().supports("imageZoom", item);
    }

    function supportsMarkdownEditing(item = artifact()) {
      return workbenchArtifactBinding().supports("markdownEditing", item);
    }

    function supportsTextRangeAnnotations(item = artifact()) {
      return workbenchArtifactBinding().supports("textRangeAnnotations", item);
    }

    function supportsHtmlElementAnnotations(item = artifact()) {
      return workbenchArtifactBinding().supports("htmlElementAnnotations", item);
    }

    function artifactControlActions() {
      return {
        applyZoom: (value, options = {}) => applyZoom(options.relative ? app.zoomPercent + value : value),
        revertMarkdownArtifact,
        saveMarkdownArtifact,
        setMarkdownMode,
        smartFit,
        toggleMarkdownTheme,
      };
    }

    function workbenchArtifactBinding() {
      if (!artifactBindingInstance) {
        artifactBindingInstance = artifactBinding().createArtifactBinding({
          getDefaultArtifact: artifact,
          registry: artifactRegistry,
          toolbar: artifactToolbar,
          elements: {
            toolbarRoot: () => $("artifact-toolbar"),
            image: () => $("artifact-image"),
          },
          documentRenderer,
          html: htmlRenderer,
          markdown: () => window.ArtifactPrimitives.markdown,
          getContext: () => ({
            artifactDocumentTheme: app.artifactDocumentTheme,
            markdownContentById: app.markdownContent,
            markdownDirty: app.markdownDirty,
            markdownMode: app.markdownMode,
            controlPolicy: app.context?.artifact_control_policy,
            mermaidSourceVisibility: app.context?.mermaid_source_visibility,
            zoomMode: app.zoomMode,
            zoomPercent: app.zoomPercent,
            documentContentById: app.documentContent,
          }),
          actions: artifactControlActions,
        });
      }
      return artifactBindingInstance;
    }

    function updateArtifactToolbar(item = artifact()) {
      workbenchArtifactBinding().updateToolbar(item);
    }

    function artifactStagePlan(item = artifact()) {
      return workbenchArtifactBinding().stagePlan(item);
    }

    function applyMarkdownPreviewBodyClass(className) {
      const nextClass = typeof className === "string" ? className.trim() : "";
      const previewBody = markdownPreviewBody();
      if (app.markdownPreviewBodyClass && app.markdownPreviewBodyClass !== nextClass) {
        previewBody.classList.remove(app.markdownPreviewBodyClass);
      }
      if (nextClass && app.markdownPreviewBodyClass !== nextClass) {
        previewBody.classList.add(nextClass);
      }
      app.markdownPreviewBodyClass = nextClass;
    }

    function applyArtifactStagePlan(plan) {
      const { stage = {}, surfaces = {} } = plan || {};
      $("stage").classList.toggle("markdown-stage", Boolean(stage.markdownStage));
      if (stage.resetScroll) $("stage").scrollTo({ left: 0, top: 0 });
      if (typeof surfaces.imageWrapHidden === "boolean") $("image-wrap").hidden = surfaces.imageWrapHidden;
      if (typeof surfaces.markdownWrapHidden === "boolean") $("markdown-wrap").hidden = surfaces.markdownWrapHidden;
      if (typeof surfaces.selectionHidden === "boolean") $("selection").hidden = surfaces.selectionHidden;
      if (typeof surfaces.markdownMarkerHidden === "boolean") $("markdown-marker").hidden = surfaces.markdownMarkerHidden;
      if (typeof surfaces.markdownPreviewHidden === "boolean") $("markdown-preview").hidden = surfaces.markdownPreviewHidden;
      if (typeof surfaces.markdownSourceHidden === "boolean") $("markdown-source").hidden = surfaces.markdownSourceHidden;
      applyMarkdownPreviewBodyClass(surfaces.markdownPreviewBodyClass);
      if (surfaces.resetHoverMarker) resetHoverMarker();
      if (typeof surfaces.commentPopoverHidden === "boolean") $("comment-popover").hidden = surfaces.commentPopoverHidden;
    }

    function applyArtifactFallbackPlan(plan = {}) {
      const { surfaces = {} } = plan;
      if (typeof surfaces.markdownPreviewHidden === "boolean") $("markdown-preview").hidden = surfaces.markdownPreviewHidden;
      if (typeof surfaces.markdownSourceHidden === "boolean") $("markdown-source").hidden = surfaces.markdownSourceHidden;
      markdownPreviewBody().innerHTML = plan.html || "";
      if (plan.updateReadout) updateArtifactToolbar();
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
      const plan = artifactRenderer().artifactSelectionPlan({
        requestedIndex: index,
        artifactCount: app.collection.artifacts.length,
      });
      if (!plan.canSelect) return;
      app.index = plan.activeIndex;
      if (plan.closeEditor) closeEditor();
      if (plan.hideAnnotationMarker) hideAnnotationMarker();
      if (plan.render) render();
    }

    function move(delta) {
      const plan = artifactNavigation().artifactMovePlan({
        ...artifactNavigationContext(),
        delta,
      });
      if (plan.activeIndex === app.index) return;
      setArtifact(plan.activeIndex);
    }

    function renderTitle() {
      $("artifact-title").innerHTML = artifactNavigation().renderArtifactTitleHtml({
        ...artifactNavigationContext(),
        formatTime,
      });
    }

    function renderImage({ artifact: item = artifact() } = {}) {
      clearHtmlInspector();
      const image = $("artifact-image");
      updateArtifactToolbar();
      image.onload = () => {
        updateArtifactToolbar();
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

    function renderDocument({ artifact: item = artifact(), content = "" } = {}) {
      clearHtmlInspector();
      if (!window.ArtifactPrimitives?.document) {
        throw new Error("Document renderer primitive is not loaded");
      }
      documentRenderer().renderDocumentArtifact(
        artifactRenderer().documentRenderPayload(item, {
          content,
          url: artifactUrl(item),
        }),
        markdownPreviewBody(),
      );
      updateArtifactToolbar();
    }

    function sourceUrlForHtmlArtifact(item = artifact()) {
      const projected = app.artifactProjectionModel?.projectedArtifactsById?.[item.id] || {};
      return projected.source_page?.url || item.source_url || item.url || item.path || "";
    }

    function clearHtmlInspector() {
      if (typeof unbindHtmlInspector === "function") unbindHtmlInspector();
      unbindHtmlInspector = null;
    }

    function htmlFrameElement() {
      return markdownPreviewBody().querySelector("[data-html-frame]");
    }

    function liveHtmlElementForAnchor(anchor) {
      const documentRoot = htmlFrameElement()?.contentDocument;
      for (const selector of anchor?.selector_candidates || []) {
        try {
          const match = documentRoot?.querySelector?.(selector);
          if (match) return match;
        } catch (_error) {
          // Invalid fallback selectors should not block saved rect placement.
        }
      }
      return null;
    }

    function liveHtmlAnchor(anchor) {
      const match = liveHtmlElementForAnchor(anchor);
      if (!match || typeof htmlRenderer()?.htmlElementAnchorForElement !== "function") return null;
      return htmlRenderer().htmlElementAnchorForElement(match, {
        sourceUrl: anchor?.source_url || sourceUrlForHtmlArtifact(),
      });
    }

    function displayRectForHtmlElementAnchor(anchor) {
      const resolvedAnchor = liveHtmlAnchor(anchor) || anchor;
      return htmlRenderer()?.displayRectForHtmlElementAnchor?.({
        anchor: resolvedAnchor,
        frameEl: htmlFrameElement(),
        wrapEl: $("markdown-wrap"),
      }) || null;
    }

    function bindHtmlInspector(item = artifact()) {
      clearHtmlInspector();
      if (!supportsHtmlElementAnnotations(item)) return;
      const component = workbenchArtifactBinding().selectedComponent(item);
      if (typeof component?.bindInspector !== "function") return;
      unbindHtmlInspector = component.bindInspector({
        rootEl: markdownPreviewBody(),
        artifact: item,
        sourceUrl: sourceUrlForHtmlArtifact(item),
        wrapEl: $("markdown-wrap"),
        html: htmlRenderer(),
        onHover: ({ displayRect }) => {
          if (!displayRect) return;
          hideHoverMarker();
          interactionOverlay().placeOverlayBox({
            overlayEl: $("markdown-marker"),
            displayRect,
          });
        },
        onLeave: () => {
          if (!app.activeMarker && app.pendingAnchor?.type !== "html_element") {
            $("markdown-marker").hidden = true;
          }
        },
        onSelect: ({ anchor, displayRect }) => {
          if (!anchor || !displayRect) return;
          app.pendingAnchor = anchor;
          hideHoverMarker();
          interactionOverlay().placeOverlayBox({
            overlayEl: $("markdown-marker"),
            displayRect,
          });
          overlayController().openCreateEditor({
            pendingAnchor: anchor,
            displayRect,
            relativeTo: "markdown",
          });
        },
      });
    }

    function renderHtml({ artifact: item = artifact(), content = "" } = {}) {
      if (!htmlRenderer()) {
        throw new Error("HTML renderer primitive is not loaded");
      }
      htmlRenderer().renderHtmlArtifact(
        artifactRenderer().htmlRenderPayload(item, {
          content,
          url: artifactUrl(item),
        }),
        markdownPreviewBody(),
      );
      updateArtifactToolbar();
      bindHtmlInspector(item);
    }

    function renderArtifactFallback({ renderKind, error } = {}) {
      applyArtifactFallbackPlan(artifactRenderer().artifactFallbackPlan({ renderKind, error }));
    }

    async function loadMarkdown(item) {
      const hasCachedContent = Object.prototype.hasOwnProperty.call(app.markdownContent, item.id);
      const plan = artifactRenderer().markdownLoadPlan(item, {
        hasCachedContent,
        cachedContent: app.markdownContent[item.id],
        url: artifactUrl(item),
      });
      if (plan.action === "use-cache") return plan.content;
      const response = await fetch(plan.url, { cache: plan.cache });
      if (!response.ok) throw new Error(`${plan.errorPrefix}: ${response.status}`);
      const result = artifactRenderer().markdownLoadResultPlan({ content: await response.text() });
      app.markdownContent[item.id] = result.content;
      app.markdownSavedContent[item.id] = result.savedContent;
      app.markdownDirty[item.id] = result.dirty;
      return result.content;
    }

    async function loadDocument(item) {
      const hasCachedContent = Object.prototype.hasOwnProperty.call(app.documentContent, item.id);
      const plan = artifactRenderer().documentLoadPlan(item, {
        hasCachedContent,
        cachedContent: app.documentContent[item.id],
        url: artifactUrl(item),
      });
      let fetchedContent = "";
      if (plan.action === "fetch-text") {
        const response = await fetch(plan.url, { cache: plan.cache });
        if (!response.ok) throw new Error(`${plan.errorPrefix}: ${response.status}`);
        fetchedContent = await response.text();
      }
      const result = artifactRenderer().documentLoadResultPlan(plan, { fetchedContent });
      if (result.cacheContent !== null) app.documentContent[item.id] = result.cacheContent;
      return result.content;
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
      clearHtmlInspector();
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
        mermaidSourceVisibility: app.context?.mermaid_source_visibility,
      });
      updateArtifactToolbar();
      renderMarkdownHighlights();
      scheduleMooringOverlayUpdate();
    }

    function renderMarkdownHighlights() {
      markdownPreviewBody().querySelectorAll(".line-hit").forEach((node) => node.classList.remove("line-hit"));
      if (app.markdownMode !== "preview" || !supportsTextRangeAnnotations()) return;
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

    async function saveMarkdownArtifact() {
      const item = artifact();
      if (!supportsMarkdownEditing(item)) return;
      const content = app.markdownContent[item.id] || "";
      const response = await fetch(`/api/artifact-content/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        headers: { "content-type": "text/markdown; charset=utf-8" },
        body: content,
      });
      const plan = artifactRenderer().markdownSavePlan({ content, responseOk: response.ok });
      if (plan.status !== "saved") {
        showToast(plan.toast);
        return;
      }
      app.markdownSavedContent[item.id] = plan.savedContent;
      app.markdownDirty[item.id] = plan.dirty;
      if (plan.renderBody) renderMarkdownBody(item);
      showToast(plan.toast);
    }

    function revertMarkdownArtifact() {
      const item = artifact();
      if (!supportsMarkdownEditing(item)) return;
      const plan = artifactRenderer().markdownRevertPlan({ savedContent: app.markdownSavedContent[item.id] });
      app.markdownContent[item.id] = plan.content;
      app.markdownDirty[item.id] = plan.dirty;
      if (plan.renderBody) renderMarkdownBody(item);
      showToast(plan.toast);
    }

    function setMarkdownMode(mode) {
      const plan = artifactRenderer().markdownModePlan(mode);
      app.markdownMode = plan.mode;
      if (plan.renderBody) renderMarkdownBody(artifact());
      if (plan.focusSource) $("markdown-source").focus();
    }

    function toggleMarkdownTheme() {
      setArtifactDocumentTheme(app.artifactDocumentTheme === "dark" ? "light" : "dark");
    }

    function renderArtifact() {
      const item = artifact();
      updateArtifactToolbar(item);
      void artifactRenderer().renderArtifact({
        artifact: item,
        stagePlan: artifactStagePlan(item),
        effects: {
          applyStagePlan: applyArtifactStagePlan,
          renderImage,
          loadMarkdown,
          renderMarkdown: ({ artifact: renderedArtifact }) => renderMarkdownBody(renderedArtifact),
          loadDocument,
          renderDocument,
          renderHtml,
          renderArtifactError: renderArtifactFallback,
        },
      });
    }

    function renderOverview() {
      $("overview-popover").innerHTML = artifactNavigation().renderOverviewHtml(artifactNavigationContext());
      const select = $("overview-popover").querySelector("[data-context-select]");
      if (select) {
        select.addEventListener("change", () => {
          void switchWorkbenchContext(select.value);
        });
      }
      $("overview-popover").querySelectorAll("[data-index]").forEach((button) => {
        button.addEventListener("click", () => {
          $("overview-popover").hidden = true;
          setArtifact(Number(button.dataset.index));
        });
      });
    }

    function applyArtifactFilterPlan(plan = {}) {
      if (plan.filters) app.filters = plan.filters;
      if (Number.isInteger(plan.activeIndex)) app.index = plan.activeIndex;
      closeEditor();
      hideAnnotationMarker();
      render();
    }

    function renderSidebar() {
      $("sidebar").innerHTML = artifactNavigation().renderSidebarHtml(artifactNavigationContext());
      $("sidebar").querySelectorAll("[data-filter-kind]").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          applyArtifactFilterPlan(artifactNavigation().artifactFilterPlan({
            ...artifactNavigationContext(),
            filterKind: button.dataset.filterKind,
            filterValue: button.dataset.filterValue,
          }));
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
          const plan = interactionOverlay().annotationReorderPlan({
            interactionOverlays: app.interactionOverlays,
            artifactId: targetArtifactId,
            sourceArtifactId: payload.artifactId,
            sourceAnnotationId: payload.annotationId,
            targetAnnotationId,
          });
          if (!plan) return;
          app.interactionOverlays = plan.interactionOverlays;
          await syncInteractionOverlays();
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
      renderBoundedInputLayer();
      renderOverview();
      renderSidebar();
      renderShell();
      void syncWorkbenchViewState();
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
        htmlElementRect: (htmlAnchor) => displayRectForHtmlElementAnchor(htmlAnchor),
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
      if (anchor?.type === "html_element") {
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
      if (anchor?.type === "html_element") {
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
      if (anchor?.type === "html_element") {
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
      overlayController().showAnnotationMarker({
        artifactId,
        annotationId,
        artifactIndex: index,
        currentIndex: app.index,
        note,
      });
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

    function openCreateEditor(displayRect, relativeTo = $("artifact-image")) {
      overlayController().openCreateEditor({
        pendingAnchor: app.pendingAnchor,
        displayRect,
        relativeTo: relativeTo === $("markdown-wrap") ? "markdown" : "image",
      });
    }

    function scrollRectIntoView(rect) {
      window.ArtifactPrimitives.imageViewer.scrollRectIntoView({
        rect,
        imageEl: $("artifact-image"),
        wrapEl: $("image-wrap"),
        stageEl: $("stage"),
      });
    }

    function scrollHtmlElementIntoView(anchor) {
      liveHtmlElementForAnchor(anchor)?.scrollIntoView({ block: "center", inline: "center" });
    }

    function openExistingEditor(note) {
      overlayController().openExistingEditor({
        note,
        markdownMode: app.markdownMode,
      });
    }

    function closeEditor() {
      overlayController().closeEditor();
    }

    function selectAnnotation(artifactId, annotationId) {
      const index = artifactIndexById(artifactId);
      const note = annotationById(artifactId, annotationId);
      overlayController().selectAnnotation({
        artifactId,
        annotationId,
        artifactIndex: index,
        currentIndex: app.index,
        note,
      });
    }

    function applyOverlayDraftStart(draft, placeDraftSelection) {
      overlayController().runDraftStart(draft, placeDraftSelection);
    }

    function startDrag(event) {
      if (event.button !== 0) return;
      if (supportsImageRegionAnnotations() && event.target.closest("#image-wrap")) {
        const point = imagePoint(event);
        applyOverlayDraftStart(interactionOverlay().beginOverlayDraft({
          type: "image",
          point,
        }), placeSelection);
        return;
      }
      if (supportsTextRangeAnnotations() && app.markdownMode === "preview" && event.target.closest("#markdown-preview")) {
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
      return overlayController().runDraftCompletion(intent);
    }

    function resolveOverlayDraftAnchor({ type, displayRect }) {
      if (type === "markdown") {
        return window.ArtifactPrimitives.markdownInteractions.anchorFromDisplayRect({
          displayRect,
          wrapEl: $("markdown-wrap"),
          rootEl: markdownPreviewBody(),
          content: app.markdownContent[artifact().id] || "",
        });
      }
      return {
        type: "image_region",
        coordinate_space: "natural_image",
        rect: naturalRect(displayRect),
      };
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
      applyOverlayDraftCompletion(interactionOverlay().completeResolvedOverlayDraft({
        type,
        displayRect,
        resolveAnchor: resolveOverlayDraftAnchor,
      }));
    }

    async function applyOverlayEditorIntent(intent) {
      await overlayController().runEditorIntent(intent);
    }

    async function commitEditor() {
      await applyOverlayEditorIntent(interactionOverlay().commitOverlayEditorIntent({
        interactionOverlays: app.interactionOverlays,
        artifact: artifact(),
        editorMode: app.editorMode,
        editing: app.editing,
        pendingAnchor: app.pendingAnchor,
        comment: $("comment-text").value,
      }));
    }

    async function secondaryEditorAction() {
      await applyOverlayEditorIntent(interactionOverlay().secondaryOverlayEditorIntent({
        interactionOverlays: app.interactionOverlays,
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
      document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-bounded-input-select]")) {
          closeBoundedSelectMenus();
        }
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeBoundedSelectMenus();
      });
      $("copy-artifact").addEventListener("click", () => copyText(JSON.stringify(artifact(), null, 2)));
      $("copy-path").addEventListener("click", () => copyText(artifact().path));
      $("secondary-comment-action").addEventListener("click", secondaryEditorAction);
      $("primary-comment-action").addEventListener("click", commitEditor);
      $("markdown-source").addEventListener("input", () => {
        const item = artifact();
        const plan = artifactRenderer().markdownInputPlan({
          content: $("markdown-source").value,
          savedContent: app.markdownSavedContent[item.id],
        });
        app.markdownContent[item.id] = plan.content;
        app.markdownDirty[item.id] = plan.dirty;
        if (plan.updateReadout) updateArtifactToolbar();
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
        if (!supportsImageZoom()) {
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
        if (!event.ctrlKey || !supportsImageZoom()) return;
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
      const stateResponse = await fetch("/api/workbench-state");
      const payload = await stateResponse.json();
      applyWorkbenchStatePayload(payload);
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
