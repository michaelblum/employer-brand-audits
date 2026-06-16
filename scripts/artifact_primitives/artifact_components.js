(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const DOCUMENT_TYPES = ["json", "text", "log", "file"];
  const ICON_SPRITE = "/assets/workflow-artifact-workbench-icons.svg";

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function renderIconUse(name) {
    return `<svg aria-hidden="true"><use href="${ICON_SPRITE}#${name}"></use></svg>`;
  }

  function fallbackIsDocumentArtifact(artifact = {}) {
    return DOCUMENT_TYPES.includes(String(artifact.type || "").toLowerCase());
  }

  function documentPrimitive(options = {}) {
    return options.document || ROOT.document;
  }

  function markdownPrimitive(options = {}) {
    return options.markdown || ROOT.markdown;
  }

  function sharedSurfaces() {
    return {
      selectionHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
    };
  }

  function imageStagePlan() {
    return {
      renderKind: "image",
      stage: { markdownStage: false, resetScroll: true },
      surfaces: {
        imageWrapHidden: false,
        markdownWrapHidden: true,
        ...sharedSurfaces(),
        markdownMarkerHidden: true,
        markdownPreviewHidden: null,
        markdownSourceHidden: null,
      },
    };
  }

  function markdownStagePlan() {
    return {
      renderKind: "markdown",
      stage: { markdownStage: true, resetScroll: false },
      surfaces: {
        imageWrapHidden: true,
        markdownWrapHidden: false,
        ...sharedSurfaces(),
        markdownMarkerHidden: null,
        markdownPreviewHidden: null,
        markdownSourceHidden: null,
      },
    };
  }

  function documentStagePlan() {
    return {
      renderKind: "document",
      stage: { markdownStage: true, resetScroll: true },
      surfaces: {
        imageWrapHidden: true,
        markdownWrapHidden: false,
        ...sharedSurfaces(),
        markdownMarkerHidden: true,
        markdownPreviewHidden: false,
        markdownSourceHidden: true,
      },
    };
  }

  function imageReadout({ artifact = {}, imageNaturalWidth = null, imageNaturalHeight = null } = {}) {
    const dimensions = artifact.dimensions || {};
    const width = dimensions.width || imageNaturalWidth || "unknown";
    const height = dimensions.height || imageNaturalHeight || "unknown";
    return `${width} x ${height} px`;
  }

  function markdownReadout({ markdownContent = "", markdown = ROOT.markdown } = {}) {
    if (typeof markdown?.markdownDiagnostics !== "function") return "";
    const diagnostics = markdown.markdownDiagnostics(markdownContent);
    return `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
  }

  function documentReadout({ artifact = {}, documentContent = "", document = ROOT.document } = {}) {
    return typeof document?.documentReadout === "function"
      ? document.documentReadout(artifact, documentContent)
      : "";
  }

  function readoutContext(options = {}) {
    const artifact = options.artifact || {};
    return {
      ...options,
      markdownContent: options.markdownContent ?? options.markdownContentById?.[artifact.id] ?? "",
      documentContent: options.documentContent ?? options.documentContentById?.[artifact.id] ?? "",
      markdown: markdownPrimitive(options),
      document: documentPrimitive(options),
    };
  }

  function toolbarPlan({ kind, readoutId, readoutLabel, readoutValue, controls = [] }) {
    return {
      kind,
      readout: readoutValue ? [{ id: readoutId, label: readoutLabel, value: readoutValue }] : [],
      controls,
    };
  }

  function renderImageZoomControls() {
    return `
      <div class="image-controls" id="image-controls" data-control-kind="image-zoom">
        <div class="zoom-control" id="zoom-control">
          <button class="zoom-fit" id="zoom-fit" type="button" aria-label="Smart fit" title="Smart fit">
            ${renderIconUse("icon-fit")}
          </button>
          <input id="zoom-input" type="text" inputmode="numeric" aria-label="Zoom percentage">
          <div class="zoom-steps">
            <button id="zoom-in" type="button" aria-label="Zoom in">+</button>
            <button id="zoom-out" type="button" aria-label="Zoom out">-</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderMarkdownControls() {
    return `
      <div class="markdown-controls visible" id="markdown-controls" data-control-kind="markdown-controls">
        <div class="segmented" role="group" aria-label="Markdown view mode">
          <button id="markdown-preview-mode" class="tool-button" type="button" data-markdown-mode="preview" aria-label="Preview" title="Preview">
            ${renderIconUse("icon-preview")}
          </button>
          <button id="markdown-source-mode" class="tool-button" type="button" data-markdown-mode="source" aria-label="Edit" title="Edit">
            <span aria-hidden="true">&lt;/&gt;</span>
          </button>
        </div>
        <button class="action-button icon-only" id="markdown-theme-toggle" type="button" aria-label="Use light markdown theme" title="Use light markdown theme">
          ${renderIconUse("icon-theme")}
        </button>
        <button class="action-button icon-only" id="markdown-revert" type="button" aria-label="Revert" title="Revert">
          ${renderIconUse("icon-revert")}
        </button>
        <button class="action-button icon-only primary" id="markdown-save" type="button" aria-label="Save" title="Save">
          ${renderIconUse("icon-save")}
        </button>
      </div>
    `;
  }

  function makeAbortScope() {
    if (typeof AbortController === "undefined") {
      const removals = [];
      return {
        add: (target, type, handler, options) => {
          target.addEventListener(type, handler, options);
          removals.push(() => target.removeEventListener(type, handler, options));
        },
        done: () => removals.splice(0).forEach((remove) => remove()),
      };
    }
    const controller = new AbortController();
    return {
      add: (target, type, handler, options = {}) => {
        target.addEventListener(type, handler, { ...options, signal: controller.signal });
      },
      done: () => controller.abort(),
    };
  }

  function noopUnbind() {}

  function closestElement(target, selector) {
    return typeof target?.closest === "function" ? target.closest(selector) : null;
  }

  const imageComponent = {
    kind: "image",
    matches: () => true,
    stagePlan: imageStagePlan,
    readout: imageReadout,
    toolbarPlan: (options = {}) => toolbarPlan({
      kind: "image",
      readoutId: "image-dimensions",
      readoutLabel: "Dimensions",
      readoutValue: imageReadout(options),
      controls: [{ id: "image-zoom", html: renderImageZoomControls() }],
    }),
    bindControls: ({ rootEl, actions = {} } = {}) => {
      if (!rootEl) return noopUnbind;
      const scope = makeAbortScope();
      scope.add(rootEl, "click", (event) => {
        const button = closestElement(event.target, "button");
        if (!button || !rootEl.contains(button)) return;
        if (button.id === "zoom-in") actions.applyZoom?.(10, { relative: true });
        if (button.id === "zoom-out") actions.applyZoom?.(-10, { relative: true });
        if (button.id === "zoom-fit") actions.smartFit?.();
      });
      scope.add(rootEl, "change", (event) => {
        if (event.target?.id === "zoom-input") actions.applyZoom?.(event.target.value.replace("%", ""));
      });
      scope.add(rootEl, "wheel", (event) => {
        if (!closestElement(event.target, "#zoom-control")) return;
        event.preventDefault();
        actions.applyZoom?.(event.deltaY < 0 ? 5 : -5, { relative: true });
      }, { passive: false });
      return scope.done;
    },
  };

  const markdownComponent = {
    kind: "markdown",
    matches: (artifact = {}) => String(artifact.type || "").toLowerCase() === "markdown",
    stagePlan: markdownStagePlan,
    readout: markdownReadout,
    toolbarPlan: (options = {}) => toolbarPlan({
      kind: "markdown",
      readoutId: "markdown-diagnostics",
      readoutLabel: "Markdown",
      readoutValue: markdownReadout(options),
      controls: [{ id: "markdown-controls", html: renderMarkdownControls() }],
    }),
    bindControls: ({ rootEl, actions = {} } = {}) => {
      if (!rootEl) return noopUnbind;
      const scope = makeAbortScope();
      scope.add(rootEl, "click", (event) => {
        const button = closestElement(event.target, "button");
        if (!button || !rootEl.contains(button)) return;
        if (button.id === "markdown-preview-mode") actions.setMarkdownMode?.("preview");
        if (button.id === "markdown-source-mode") actions.setMarkdownMode?.("source");
        if (button.id === "markdown-theme-toggle") actions.toggleMarkdownTheme?.();
        if (button.id === "markdown-save") void actions.saveMarkdownArtifact?.();
        if (button.id === "markdown-revert") actions.revertMarkdownArtifact?.();
      });
      return scope.done;
    },
    syncControls: ({ rootEl, state = {}, artifact = {} } = {}) => {
      if (!rootEl) return;
      const themeButton = rootEl.querySelector("#markdown-theme-toggle");
      const saveButton = rootEl.querySelector("#markdown-save");
      if (saveButton) saveButton.disabled = !state.markdownDirty?.[artifact.id];
      if (ROOT.markdownInteractions) {
        ROOT.markdownInteractions.syncModeButtons({
          rootEl,
          mode: state.markdownMode,
          themeButtonEl: themeButton,
          theme: state.artifactDocumentTheme,
        });
      }
    },
  };

  const documentComponent = {
    kind: "document",
    matches: (artifact = {}, options = {}) => {
      const document = documentPrimitive(options);
      return typeof document?.isDocumentArtifact === "function"
        ? document.isDocumentArtifact(artifact)
        : fallbackIsDocumentArtifact(artifact);
    },
    stagePlan: documentStagePlan,
    readout: documentReadout,
    toolbarPlan: (options = {}) => toolbarPlan({
      kind: "document",
      readoutId: "document-summary",
      readoutLabel: "Document",
      readoutValue: documentReadout(options),
      controls: [],
    }),
  };

  const defaultComponents = [markdownComponent, documentComponent, imageComponent];

  function resolveArtifactComponent(artifact = {}, options = {}) {
    return defaultComponents.find((component) => component.matches(artifact, options)) || imageComponent;
  }

  function artifactRenderKind(artifact = {}, options = {}) {
    return resolveArtifactComponent(artifact, options).kind;
  }

  function artifactStagePlan(artifact = {}, options = {}) {
    return resolveArtifactComponent(artifact, options).stagePlan(artifact, options);
  }

  function artifactReadout(options = {}) {
    const context = readoutContext(options);
    return resolveArtifactComponent(context.artifact, context).readout(context);
  }

  function artifactToolbarPlan(options = {}) {
    const context = readoutContext(options);
    return resolveArtifactComponent(context.artifact, context).toolbarPlan(context);
  }

  ROOT.artifactComponents = {
    artifactReadout,
    artifactRenderKind,
    artifactStagePlan,
    artifactToolbarPlan,
    resolveArtifactComponent,
  };
}());
