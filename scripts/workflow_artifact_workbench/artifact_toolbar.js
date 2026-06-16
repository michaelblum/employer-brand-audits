(function () {
  const ROOT = window.WorkbenchArtifactToolbar = window.WorkbenchArtifactToolbar || {};

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function renderReadoutItem(item = {}) {
    const id = escapeHtml(item.id || "readout");
    const label = String(item.label || "").trim();
    const value = String(item.value || "").trim();
    const tone = item.tone ? ` ${escapeHtml(item.tone)}` : "";
    const title = label ? ` title="${escapeHtml(`${label}: ${value}`)}"` : "";
    return `<span class="artifact-readout-item${tone}" data-readout-id="${id}"${title}>${escapeHtml(value)}</span>`;
  }

  function renderReadout(readout = []) {
    return `
      <div class="artifact-readout" id="artifact-readout" data-slot="readout">
        ${readout.map(renderReadoutItem).join("")}
      </div>
    `;
  }

  function renderIconUse(name) {
    return `<svg aria-hidden="true"><use href="/assets/workflow-artifact-workbench-icons.svg#${name}"></use></svg>`;
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

  function renderControl(control = {}) {
    if (control.kind === "image-zoom") return renderImageZoomControls();
    if (control.kind === "markdown-controls") return renderMarkdownControls();
    return "";
  }

  function renderControls(controls = []) {
    return `
      <div class="artifact-controls" id="artifact-controls" data-slot="controls">
        ${controls.map(renderControl).join("")}
      </div>
    `;
  }

  function renderToolbarHtml(plan = {}) {
    return `${renderReadout(plan.readout || [])}${renderControls(plan.controls || [])}`;
  }

  function mountToolbar(container, plan = {}) {
    if (!container) return;
    container.dataset.artifactKind = plan.kind || "";
    container.innerHTML = renderToolbarHtml(plan);
  }

  ROOT.renderToolbarHtml = renderToolbarHtml;
  ROOT.mountToolbar = mountToolbar;
}());
