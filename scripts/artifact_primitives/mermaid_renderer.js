(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};
  let renderSequence = 0;
  let initialized = false;

  function setRenderState(figure, state) {
    if (!figure) return;
    const states = ["source", "pending", "complete", "error"];
    figure.dataset.renderState = state;
    for (const item of states) figure.classList.remove(`render-state-${item}`);
    figure.classList.add(`render-state-${state}`);
  }

  function statusNode(figure) {
    return figure?.querySelector("[data-mermaid-status]") || null;
  }

  function setStatus(figure, message) {
    const node = statusNode(figure);
    if (node) node.textContent = message;
  }

  function normalizeSourceVisibility(value) {
    return value === "preview-hidden" ? "preview-hidden" : "visible";
  }

  function setSourceVisibility(figure, value) {
    if (!figure) return;
    figure.dataset.sourceVisibility = normalizeSourceVisibility(value);
  }

  function sourceFromFigure(figure) {
    const raw = figure?.querySelector(".mermaid-source-raw");
    if (raw?.content) return raw.content.textContent || "";
    if (raw) return raw.textContent || "";
    const code = figure?.querySelector(".mermaid-source code");
    return code?.textContent || figure?.dataset.mermaidSource || "";
  }

  function ensureMermaidInitialized(options = {}) {
    if (!window.mermaid) {
      throw new Error("Mermaid library is not loaded");
    }
    if (!initialized) {
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        ...options.mermaidConfig,
      });
      // Config is set once per page load; later mermaidConfig values are ignored.
      initialized = true;
    }
  }

  async function renderMermaid(source, containerEl, options = {}) {
    const figure = options.figure || containerEl?.closest?.("[data-artifact-renderer='mermaid']");
    const sourceVisibility = normalizeSourceVisibility(options.sourceVisibility);
    setSourceVisibility(figure, sourceVisibility);
    setRenderState(figure, "pending");
    setStatus(figure, "Rendering Mermaid preview...");
    try {
      ensureMermaidInitialized(options);
      const id = `artifact-mermaid-${Date.now()}-${++renderSequence}`;
      const result = await window.mermaid.render(id, String(source || ""));
      containerEl.innerHTML = result.svg;
      if (typeof result.bindFunctions === "function") {
        result.bindFunctions(containerEl);
      }
      setRenderState(figure, "complete");
      setStatus(
        figure,
        sourceVisibility === "preview-hidden"
          ? "Mermaid preview rendered."
          : "Mermaid preview rendered. Source remains available below.",
      );
      return { ok: true, state: "complete", errorMessage: "" };
    } catch (error) {
      if (containerEl) containerEl.textContent = "";
      setSourceVisibility(figure, "visible");
      const message = error?.message || String(error || "Mermaid render failed");
      setRenderState(figure, "error");
      setStatus(figure, `Mermaid render error: ${message}`);
      return { ok: false, state: "error", errorMessage: message };
    }
  }

  function upgradeMermaidBlocks(rootEl = document, options = {}) {
    const figures = [...rootEl.querySelectorAll("[data-artifact-renderer='mermaid']")];
    return Promise.all(figures.map((figure) => {
      const target = figure.querySelector("[data-mermaid-target]");
      const source = sourceFromFigure(figure);
      if (!target) return Promise.resolve({ ok: false, state: "error", errorMessage: "Missing target" });
      return renderMermaid(source, target, { ...options, figure });
    }));
  }

  ROOT.mermaid = {
    renderMermaid,
    upgradeMermaidBlocks,
  };
}());
