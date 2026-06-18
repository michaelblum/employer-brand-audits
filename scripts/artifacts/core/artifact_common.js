(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  const ICON_SPRITE = "/assets/artifact-workbench-icons.svg";

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

  function sharedStageSurfaces() {
    return {
      selectionHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
    };
  }

  function controlsForPolicy(controls = [], { controlPolicy } = {}) {
    if (controlPolicy !== "read-only") return controls;
    return controls.filter((control) => control.readOnlyAllowed);
  }

  function toolbarPlan({ kind, readoutId, readoutLabel, readoutValue, controls = [], controlPolicy = null }) {
    return {
      kind,
      readout: readoutValue ? [{ id: readoutId, label: readoutLabel, value: readoutValue }] : [],
      controls: controlsForPolicy(controls, { controlPolicy }),
    };
  }

  function readoutContext(options = {}) {
    const artifact = options.artifact || {};
    return {
      ...options,
      markdownContent: options.markdownContent ?? options.markdownContentById?.[artifact.id] ?? "",
      documentContent: options.documentContent ?? options.documentContentById?.[artifact.id] ?? "",
      markdown: options.markdown || window.ArtifactPrimitives?.markdown,
      document: options.document || window.ArtifactPrimitives?.document,
    };
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

  function closestElement(target, selector) {
    return typeof target?.closest === "function" ? target.closest(selector) : null;
  }

  function noopUnbind() {}

  ROOT.common = {
    closestElement,
    controlsForPolicy,
    escapeHtml,
    makeAbortScope,
    noopUnbind,
    readoutContext,
    renderIconUse,
    sharedStageSurfaces,
    toolbarPlan,
  };
}());
