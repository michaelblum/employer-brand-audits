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

  function compactText(value, limit = 240) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > limit ? `${text.slice(0, limit - 1).trim()}...` : text;
  }

  function isHtmlArtifact(artifact = {}) {
    const type = String(artifact.type || "").toLowerCase();
    const mimeType = String(artifact.mime_type || artifact.mimeType || "").toLowerCase();
    const path = String(artifact.path || artifact.file_path || artifact.url || "").toLowerCase();
    return type === "html" || mimeType === "text/html" || path.endsWith(".html") || path.endsWith(".htm");
  }

  function htmlElementCount(content = "") {
    const source = String(content || "")
      .replace(/<!--[\s\S]*?-->/g, "")
      .replace(/<!doctype[\s\S]*?>/gi, "");
    return (source.match(/<\s*[a-z][\w:-]*(?:\s|\/?>)/gi) || []).length;
  }

  function htmlReadout(artifact = {}, content = "") {
    const count = htmlElementCount(content);
    const size = artifact.size_bytes ?? artifact.sizeBytes;
    return [
      "html",
      `${count} ${count === 1 ? "element" : "elements"}`,
      size ? `${size} bytes` : "",
    ].filter(Boolean).join(" · ");
  }

  function renderMetadata(artifact = {}) {
    const metadata = [
      artifact.mimeType || artifact.mime_type || "text/html",
      artifact.sizeBytes ? `${artifact.sizeBytes} bytes` : "",
      artifact.path,
    ].filter(Boolean);
    if (!metadata.length) return "";
    return `<div class="html-artifact-meta">${metadata.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
  }

  function htmlDocumentHeight(doc) {
    if (!doc) return 0;
    return Math.max(
      doc.body?.scrollHeight || 0,
      doc.body?.offsetHeight || 0,
      doc.documentElement?.scrollHeight || 0,
      doc.documentElement?.offsetHeight || 0,
      doc.documentElement?.clientHeight || 0,
    );
  }

  function syncHtmlFrameHeight(frame) {
    const doc = frame?.contentDocument;
    if (!doc) return;
    if (doc.documentElement?.style) doc.documentElement.style.overflow = "hidden";
    if (doc.body?.style) doc.body.style.overflow = "hidden";
    const height = Math.max(560, htmlDocumentHeight(doc));
    if (frame.style) frame.style.height = `${height}px`;
  }

  function scheduleHtmlFrameHeightSync(frame) {
    if (!frame) return;
    frame.setAttribute?.("scrolling", "no");
    frame.scrolling = "no";
    const schedule = () => {
      const requestFrame = typeof window.requestAnimationFrame === "function"
        ? window.requestAnimationFrame.bind(window)
        : (callback) => callback();
      requestFrame(() => syncHtmlFrameHeight(frame));
      requestFrame(() => requestFrame(() => syncHtmlFrameHeight(frame)));
    };
    frame.addEventListener?.("load", schedule);
    schedule();
  }

  function renderHtmlArtifact(artifact = {}, containerEl) {
    if (!containerEl) {
      return { ok: false, state: "error", errorMessage: "Missing HTML container" };
    }
    const title = artifact.name || artifact.id || "HTML artifact";
    containerEl.innerHTML = `
      <article class="html-artifact" data-artifact-renderer="html">
        <header>
          <h1>${escapeHtml(title)}</h1>
          ${renderMetadata(artifact)}
        </header>
        <div class="html-artifact-frame-wrap">
          <iframe class="html-artifact-frame" data-html-frame sandbox="allow-same-origin" scrolling="no" title="${escapeHtml(title)}"></iframe>
        </div>
      </article>
    `;
    const frame = containerEl.querySelector("[data-html-frame]");
    if (frame) {
      scheduleHtmlFrameHeightSync(frame);
      frame.srcdoc = String(artifact.content || "");
    }
    return { ok: true, state: "complete", errorMessage: "" };
  }

  function elementClasses(element) {
    if (!element) return [];
    if (Array.isArray(element.classList)) return [...element.classList].filter(Boolean);
    if (element.classList && typeof element.classList[Symbol.iterator] === "function") {
      return [...element.classList].filter(Boolean);
    }
    return String(element.className || element.getAttribute?.("class") || "").split(/\s+/).filter(Boolean);
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(String(value));
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function selectorCandidates(element) {
    const tag = String(element?.tagName || "").toLowerCase();
    const id = element?.id || element?.getAttribute?.("id") || "";
    const classes = elementClasses(element);
    const classSelector = classes.map((item) => `.${cssEscape(item)}`).join("");
    const candidates = [];
    if (id) candidates.push(`#${cssEscape(id)}`);
    if (tag && (id || classSelector)) candidates.push(`${tag}${id ? `#${cssEscape(id)}` : ""}${classSelector}`);
    if (tag && classSelector) candidates.push(`${tag}${classSelector}`);
    if (tag) candidates.push(tag);
    return [...new Set(candidates)];
  }

  function elementRect(element) {
    const rect = element?.getBoundingClientRect?.();
    if (!rect) return null;
    return {
      x: Math.round(Number(rect.left || 0)),
      y: Math.round(Number(rect.top || 0)),
      width: Math.round(Number(rect.width || 0)),
      height: Math.round(Number(rect.height || 0)),
    };
  }

  function ancestorTrail(element) {
    const trail = [];
    let current = element?.parentElement || null;
    while (current && trail.length < 6) {
      const tag = String(current.tagName || "").toLowerCase();
      if (tag && !["html", "body"].includes(tag)) {
        trail.push({
          tag,
          id: current.id || current.getAttribute?.("id") || "",
          classes: elementClasses(current),
        });
      }
      current = current.parentElement || null;
    }
    return trail;
  }

  function accessibleName(element) {
    return compactText(
      element?.getAttribute?.("aria-label")
      || element?.getAttribute?.("title")
      || element?.getAttribute?.("alt")
      || element?.textContent
      || "",
      160,
    );
  }

  function htmlElementAnchorForElement(element, { sourceUrl = "" } = {}) {
    const tag = String(element?.tagName || "").toLowerCase();
    return {
      type: "html_element",
      coordinate_space: "html_document",
      selector_candidates: selectorCandidates(element),
      tag,
      id: element?.id || element?.getAttribute?.("id") || "",
      classes: elementClasses(element),
      role: element?.getAttribute?.("role") || "",
      accessible_name: accessibleName(element),
      text: compactText(element?.textContent || ""),
      rect: elementRect(element),
      ancestor_trail: ancestorTrail(element),
      source_url: sourceUrl,
    };
  }

  function displayRectForHtmlElementAnchor({ anchor, frameEl, wrapEl } = {}) {
    if (!anchor?.rect || !frameEl || !wrapEl) return null;
    const frameRect = frameEl.getBoundingClientRect?.();
    const wrapRect = wrapEl.getBoundingClientRect?.();
    if (!frameRect || !wrapRect) return null;
    return {
      x: Math.round(Number(frameRect.left || 0) - Number(wrapRect.left || 0) + Number(anchor.rect.x || 0)),
      y: Math.round(Number(frameRect.top || 0) - Number(wrapRect.top || 0) + Number(anchor.rect.y || 0)),
      width: Math.round(Number(anchor.rect.width || 0)),
      height: Math.round(Number(anchor.rect.height || 0)),
    };
  }

  function bindElementInspector({
    rootEl,
    artifact = {},
    sourceUrl = "",
    wrapEl = null,
    onHover,
    onLeave,
    onSelect,
  } = {}) {
    const frame = rootEl?.querySelector?.("[data-html-frame]");
    if (!frame) return () => {};
    const abort = new AbortController();
    let boundDocument = null;
    const bindFrame = () => {
      const doc = frame.contentDocument;
      if (!doc || doc === boundDocument) return;
      boundDocument = doc;
      const elementFromEvent = (event) => {
        const target = event.target;
        if (!target || !target.tagName || ["html", "body"].includes(String(target.tagName).toLowerCase())) {
          return null;
        }
        return target;
      };
      const emit = (event, callback) => {
        const target = elementFromEvent(event);
        if (!target || typeof callback !== "function") return;
        const anchor = htmlElementAnchorForElement(target, {
          sourceUrl: sourceUrl || artifact.source_url || artifact.url || artifact.path || "",
        });
        callback({
          anchor,
          displayRect: displayRectForHtmlElementAnchor({ anchor, frameEl: frame, wrapEl }),
          element: target,
        });
      };
      doc.addEventListener("mousemove", (event) => emit(event, onHover), { signal: abort.signal });
      doc.addEventListener("mouseleave", () => onLeave?.(), { signal: abort.signal });
      doc.addEventListener("click", (event) => {
        const target = elementFromEvent(event);
        if (!target) return;
        event.preventDefault();
        event.stopPropagation();
        emit(event, onSelect);
      }, { signal: abort.signal });
    };
    frame.addEventListener("load", bindFrame, { signal: abort.signal });
    bindFrame();
    return () => abort.abort();
  }

  ROOT.html = {
    bindElementInspector,
    displayRectForHtmlElementAnchor,
    htmlElementAnchorForElement,
    htmlReadout,
    isHtmlArtifact,
    renderHtmlArtifact,
  };
}());
