(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const THEME_STORAGE_KEY = "eba.workflowArtifactWorkbench.artifactDocumentTheme";
  const LEGACY_THEME_STORAGE_KEY = "eba.workflowArtifactWorkbench.markdownTheme";

  function storedTheme() {
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
        || window.localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
      return stored === "light" ? "light" : "dark";
    } catch (_error) {
      return "dark";
    }
  }

  function syncThemeButton({ buttonEl, theme }) {
    if (!buttonEl) return;
    const isDark = theme === "dark";
    buttonEl.classList.toggle("active", isDark);
    buttonEl.setAttribute("aria-pressed", String(isDark));
    buttonEl.setAttribute("aria-label", isDark ? "Use light markdown theme" : "Use dark markdown theme");
    buttonEl.title = isDark ? "Use light markdown theme" : "Use dark markdown theme";
  }

  function setTheme({ theme, buttonEl }) {
    const nextTheme = theme === "light" ? "light" : "dark";
    document.body.dataset.artifactDocumentTheme = nextTheme;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
      window.localStorage.removeItem(LEGACY_THEME_STORAGE_KEY);
    } catch (_error) {
      // Local storage can be unavailable in constrained browser profiles.
    }
    syncThemeButton({ buttonEl, theme: nextTheme });
    return nextTheme;
  }

  function syncModeButtons({ rootEl = document, mode, themeButtonEl, theme }) {
    for (const button of rootEl.querySelectorAll("[data-markdown-mode]")) {
      const active = button.dataset.markdownMode === mode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    syncThemeButton({ buttonEl: themeButtonEl, theme });
  }

  function renderMarkdownBody({
    content,
    mode,
    dirty,
    previewBodyEl,
    sourceEl,
    previewEl,
    saveButtonEl,
    themeButtonEl,
    theme,
  }) {
    previewBodyEl.innerHTML = ROOT.markdown.renderMarkdown(content);
    if (ROOT.mermaid && mode === "preview") {
      void ROOT.mermaid.upgradeMermaidBlocks(previewBodyEl);
    }
    sourceEl.value = content;
    previewEl.hidden = mode !== "preview";
    sourceEl.hidden = mode !== "source";
    if (saveButtonEl) saveButtonEl.disabled = !dirty;
    syncModeButtons({ mode, themeButtonEl, theme });
  }

  function lineElementsForRange({ anchor, rootEl }) {
    if (!anchor?.start?.line || !anchor?.end?.line) return [];
    const start = Math.min(anchor.start.line, anchor.end.line);
    const end = Math.max(anchor.start.line, anchor.end.line);
    return [...rootEl.querySelectorAll("[data-source-line]")]
      .filter((node) => {
        const line = Number(node.dataset.sourceLine);
        return line >= start && line <= end;
      });
  }

  function displayRectFromAnchor({ anchor, rootEl, wrapEl }) {
    const elements = lineElementsForRange({ anchor, rootEl });
    if (!elements.length) return null;
    const wrapRect = wrapEl.getBoundingClientRect();
    const rects = elements.map((node) => node.getBoundingClientRect());
    const left = Math.min(...rects.map((rect) => rect.left));
    const top = Math.min(...rects.map((rect) => rect.top));
    const right = Math.max(...rects.map((rect) => rect.right));
    const bottom = Math.max(...rects.map((rect) => rect.bottom));
    return {
      x: left - wrapRect.left,
      y: top - wrapRect.top,
      width: right - left,
      height: bottom - top,
    };
  }

  function pointInWrap({ event, wrapEl }) {
    const rect = wrapEl.getBoundingClientRect();
    return {
      x: Math.min(Math.max(event.clientX - rect.left, 0), rect.width),
      y: Math.min(Math.max(event.clientY - rect.top, 0), rect.height),
    };
  }

  function placeSelection({ markerEl, displayRect }) {
    markerEl.style.left = `${displayRect.x}px`;
    markerEl.style.top = `${displayRect.y}px`;
    markerEl.style.width = `${displayRect.width}px`;
    markerEl.style.height = `${displayRect.height}px`;
    markerEl.hidden = false;
  }

  function anchorFromDisplayRect({ displayRect, wrapEl, rootEl, content }) {
    const wrapRect = wrapEl.getBoundingClientRect();
    const selectionRect = {
      left: wrapRect.left + displayRect.x,
      top: wrapRect.top + displayRect.y,
      right: wrapRect.left + displayRect.x + displayRect.width,
      bottom: wrapRect.top + displayRect.y + displayRect.height,
    };
    const hits = [...rootEl.querySelectorAll("[data-source-line]")]
      .map((node) => ({ node, rect: node.getBoundingClientRect(), line: Number(node.dataset.sourceLine) }))
      .filter(({ rect }) => rect.right >= selectionRect.left
        && rect.left <= selectionRect.right
        && rect.bottom >= selectionRect.top
        && rect.top <= selectionRect.bottom)
      .filter(({ line }) => Number.isFinite(line));
    if (!hits.length) return null;
    const startLine = Math.min(...hits.map((hit) => hit.line));
    const endLine = Math.max(...hits.map((hit) => hit.line));
    const lines = String(content || "").split("\n");
    return {
      type: "text_range",
      coordinate_space: "markdown_source",
      start: { line: startLine, column: 1 },
      end: { line: endLine, column: (lines[endLine - 1] || "").length + 1 },
      excerpt: lines.slice(startLine - 1, endLine).join("\n").slice(0, 600),
    };
  }

  function scrollTextRangeIntoView({ anchor, previewBodyEl, sourceEl }) {
    if (!anchor?.start?.line) return;
    const target = previewBodyEl.querySelector(`[data-source-line="${anchor.start.line}"]`);
    if (target) {
      target.scrollIntoView({ block: "center", inline: "nearest" });
      return;
    }
    const lines = String(sourceEl.value || "").split("\n");
    const lineHeight = Number.parseFloat(window.getComputedStyle(sourceEl).lineHeight) || 21;
    sourceEl.scrollTop = Math.max(0, (Math.min(lines.length, Math.max(1, anchor.start.line)) - 3) * lineHeight);
  }

  function indentSelection(inputEl) {
    const start = inputEl.selectionStart;
    const end = inputEl.selectionEnd;
    const prefix = inputEl.value.slice(0, start);
    const suffix = inputEl.value.slice(end);
    inputEl.value = `${prefix}  ${suffix}`;
    inputEl.setSelectionRange(start + 2, start + 2);
    inputEl.dispatchEvent(new Event("input"));
  }

  ROOT.markdownInteractions = {
    anchorFromDisplayRect,
    displayRectFromAnchor,
    indentSelection,
    lineElementsForRange,
    placeSelection,
    pointInWrap,
    renderMarkdownBody,
    scrollTextRangeIntoView,
    setTheme,
    storedTheme,
    syncModeButtons,
    syncThemeButton,
  };
}());
