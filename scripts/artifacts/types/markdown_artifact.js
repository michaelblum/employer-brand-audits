(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;

  function stagePlan() {
    return {
      renderKind: "markdown",
      stage: { markdownStage: true, resetScroll: false },
      surfaces: {
        imageWrapHidden: true,
        markdownWrapHidden: false,
        ...common.sharedStageSurfaces(),
        markdownMarkerHidden: null,
        markdownPreviewHidden: null,
        markdownSourceHidden: null,
      },
    };
  }

  function readout({ markdownContent = "", markdown = window.ArtifactPrimitives?.markdown } = {}) {
    if (typeof markdown?.markdownDiagnostics !== "function") return "";
    const diagnostics = markdown.markdownDiagnostics(markdownContent);
    return `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
  }

  function renderControls() {
    return `
      <div class="markdown-controls visible" id="markdown-controls" data-control-kind="markdown-controls">
        <div class="segmented" role="group" aria-label="Markdown view mode">
          <button id="markdown-preview-mode" class="tool-button" type="button" data-markdown-mode="preview" aria-label="Preview" title="Preview">
            ${common.renderIconUse("icon-preview")}
          </button>
          <button id="markdown-source-mode" class="tool-button" type="button" data-markdown-mode="source" aria-label="Edit" title="Edit">
            <span aria-hidden="true">&lt;/&gt;</span>
          </button>
        </div>
        <button class="action-button icon-only" id="markdown-theme-toggle" type="button" aria-label="Use light markdown theme" title="Use light markdown theme">
          ${common.renderIconUse("icon-theme")}
        </button>
        <button class="action-button icon-only" id="markdown-revert" type="button" aria-label="Revert" title="Revert">
          ${common.renderIconUse("icon-revert")}
        </button>
        <button class="action-button icon-only primary" id="markdown-save" type="button" aria-label="Save" title="Save">
          ${common.renderIconUse("icon-save")}
        </button>
      </div>
    `;
  }

  function toolbarPlan(options = {}) {
    return common.toolbarPlan({
      kind: "markdown",
      readoutId: "markdown-diagnostics",
      readoutLabel: "Markdown",
      readoutValue: readout(options),
      controls: [{ id: "markdown-controls", html: renderControls() }],
    });
  }

  function bindControls({ rootEl, actions = {} } = {}) {
    if (!rootEl) return common.noopUnbind;
    const scope = common.makeAbortScope();
    scope.add(rootEl, "click", (event) => {
      const button = common.closestElement(event.target, "button");
      if (!button || !rootEl.contains(button)) return;
      if (button.id === "markdown-preview-mode") actions.setMarkdownMode?.("preview");
      if (button.id === "markdown-source-mode") actions.setMarkdownMode?.("source");
      if (button.id === "markdown-theme-toggle") actions.toggleMarkdownTheme?.();
      if (button.id === "markdown-save") void actions.saveMarkdownArtifact?.();
      if (button.id === "markdown-revert") actions.revertMarkdownArtifact?.();
    });
    return scope.done;
  }

  function syncControls({ rootEl, state = {}, artifact = {} } = {}) {
    if (!rootEl) return;
    const themeButton = rootEl.querySelector("#markdown-theme-toggle");
    const saveButton = rootEl.querySelector("#markdown-save");
    if (saveButton) saveButton.disabled = !state.markdownDirty?.[artifact.id];
    if (window.ArtifactPrimitives?.markdownInteractions) {
      window.ArtifactPrimitives.markdownInteractions.syncModeButtons({
        rootEl,
        mode: state.markdownMode,
        themeButtonEl: themeButton,
        theme: state.artifactDocumentTheme,
      });
    }
  }

  ROOT.types.markdown = {
    bindControls,
    kind: "markdown",
    matches: (artifact = {}) => String(artifact.type || "").toLowerCase() === "markdown",
    readout,
    stagePlan,
    syncControls,
    toolbarPlan,
  };
}());
