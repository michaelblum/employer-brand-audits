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

  function prettyBytes(value) {
    const size = Number(value);
    if (!Number.isFinite(size) || size < 0) return "";
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
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

  function renderMetadata(artifact = {}) {
    const metadata = [
      artifact.mimeType || artifact.mime_type,
      artifact.sizeBytes ? prettyBytes(artifact.sizeBytes) : "",
      artifact.path,
    ].filter(Boolean);
    if (!metadata.length) return "";
    return `<div class="document-artifact-meta">${metadata.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
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
    const metadata = renderMetadata(artifact);
    const actions = renderActions(artifact);

    if (!isReadableText) {
      containerEl.innerHTML = `
        <article class="document-artifact" data-artifact-renderer="document" data-document-type="file">
          <header>
            <p class="document-render-status" role="status">No inline renderer is available for this file artifact.</p>
            <h1>${title}</h1>
            ${metadata}
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
          ${metadata}
          ${actions}
          ${status}
        </header>
        <pre class="artifact-document-source" data-document-source><code>${escapeHtml(source)}</code></pre>
      </article>
    `;
    return { ok: true, state: "complete", errorMessage: "" };
  }

  ROOT.document = {
    renderDocumentArtifact,
  };
}());
