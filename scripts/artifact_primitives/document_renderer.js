(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function formatJson(content) {
    try {
      return {
        ok: true,
        content: JSON.stringify(JSON.parse(String(content || "")), null, 2),
      };
    } catch (error) {
      return {
        ok: false,
        content: String(content || ""),
        errorMessage: error?.message || "Invalid JSON",
      };
    }
  }

  function isDocumentArtifact(artifact = {}) {
    return ["json", "text", "log", "file"].includes(String(artifact.type || "").toLowerCase());
  }

  function documentReadout(artifact = {}, content = "") {
    const source = String(content || "");
    const lines = source ? source.split("\n").length : 0;
    const size = artifact.size_bytes ? `${artifact.size_bytes} bytes` : "";
    return [artifact.type || "file", lines ? `${lines} lines` : "", size]
      .filter(Boolean)
      .join(" · ");
  }

  function renderActions(artifact = {}) {
    if (!artifact.url) return "";
    return `<div class="document-artifact-actions"><a href="${escapeHtml(artifact.url)}" target="_blank" rel="noopener noreferrer">Open source file</a></div>`;
  }

  function renderDocumentArtifact(artifact = {}, containerEl) {
    if (!containerEl) {
      return { ok: false, state: "error", errorMessage: "Missing document container" };
    }
    const type = String(artifact.type || "").toLowerCase();
    const mimeType = String(artifact.mimeType || artifact.mime_type || "").toLowerCase();
    const isJson = type === "json" || mimeType.includes("json");
    const isReadableText = isJson || type === "text" || type === "log" || mimeType.startsWith("text/");
    const title = escapeHtml(artifact.name || artifact.id || "Artifact");
    const actions = renderActions(artifact);

    if (!isReadableText) {
      containerEl.innerHTML = `
        <article class="document-artifact" data-artifact-renderer="document" data-document-type="file">
          <header>
            <p class="document-render-status" role="status">No inline renderer is available for this file artifact.</p>
            <h1>${title}</h1>
            ${actions}
          </header>
        </article>
      `;
      return { ok: true, state: "metadata", errorMessage: "" };
    }

    let source = String(artifact.content || "");
    let status = "";
    let language = "text";
    if (isJson) {
      const formatted = formatJson(source);
      source = formatted.content;
      language = "json";
      if (!formatted.ok) status = `<p class="document-render-status" role="status">JSON parse error: ${escapeHtml(formatted.errorMessage)}</p>`;
    }

    containerEl.innerHTML = `
      <article class="document-artifact" data-artifact-renderer="document" data-document-type="${escapeHtml(language)}">
        <header>
          <h1>${title}</h1>
          ${actions}
          ${status}
        </header>
        <pre class="artifact-document-source" data-document-source><code>${escapeHtml(source)}</code></pre>
      </article>
    `;
    return { ok: true, state: "complete", errorMessage: "" };
  }

  ROOT.document = {
    documentReadout,
    isDocumentArtifact,
    renderDocumentArtifact,
  };
}());
