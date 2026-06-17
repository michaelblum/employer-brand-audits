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

  function safeHref(value) {
    const href = String(value || "").trim();
    if (!href || href.startsWith("#") || href.startsWith("/")) return href;
    try {
      const parsed = new URL(href, window.location.href);
      return ["http:", "https:", "mailto:"].includes(parsed.protocol) ? href : "";
    } catch (_error) {
      return "";
    }
  }

  function renderInlineMarkdown(value) {
    const tokens = [];
    const token = (html) => {
      const marker = `@@TOKEN_${tokens.length}@@`;
      tokens.push(html);
      return marker;
    };
    let text = String(value || "");
    text = text.replace(/`([^`]+)`/g, (_match, code) => token(`<code>${escapeHtml(code)}</code>`));
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
      const safe = safeHref(href);
      return safe
        ? token(`<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
        : escapeHtml(label);
    });
    let html = escapeHtml(text);
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    return html.replace(/@@TOKEN_(\d+)@@/g, (_match, index) => tokens[Number(index)] || "");
  }

  function sourceLineAttribute(index) {
    return ` data-source-line="${index + 1}"`;
  }

  function renderMermaidSourceLines(source, firstLineIndex) {
    const lines = String(source || "").split("\n");
    return lines.map((line, offset) => (
      `<span class="mermaid-source-line"${sourceLineAttribute(firstLineIndex + offset)}>${escapeHtml(line || " ")}</span>`
    )).join("\n");
  }

  function renderMermaidBlock(source, fenceStart) {
    const firstSourceLine = fenceStart + 1;
    return (
      `<figure${sourceLineAttribute(fenceStart)} class="markdown-mermaid render-state-source" data-markdown-diagram="mermaid" data-artifact-renderer="mermaid" data-render-state="source">`
        + '<div class="mermaid-render-target" data-mermaid-target aria-label="Mermaid preview"></div>'
        + '<div class="mermaid-render-status" data-mermaid-status role="status">Mermaid source is preserved for deterministic preview rendering.</div>'
        + `<pre class="mermaid-source"><code>${renderMermaidSourceLines(source, firstSourceLine)}</code></pre>`
        + `<template class="mermaid-source-raw">${escapeHtml(source)}</template>`
      + "</figure>"
    );
  }

  function splitMarkdownTableRow(line) {
    return String(line || "")
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
  }

  function isMarkdownTableSeparator(line) {
    const cells = splitMarkdownTableRow(line);
    return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  }

  function renderMarkdownTable(headerLine, separatorLine, rows, firstLineIndex) {
    const headers = splitMarkdownTableRow(headerLine);
    const aligns = splitMarkdownTableRow(separatorLine).map((cell) => {
      if (cell.startsWith(":") && cell.endsWith(":")) return "center";
      if (cell.endsWith(":")) return "right";
      return "left";
    });
    const headerHtml = headers.map((cell, cellIndex) => (
      `<th style="text-align: ${aligns[cellIndex] || "left"}">${renderInlineMarkdown(cell)}</th>`
    )).join("");
    const bodyHtml = rows.map(({ line, index }) => {
      const cells = splitMarkdownTableRow(line);
      return `<tr${sourceLineAttribute(index)}>${headers.map((_header, cellIndex) => (
        `<td style="text-align: ${aligns[cellIndex] || "left"}">${renderInlineMarkdown(cells[cellIndex] || "")}</td>`
      )).join("")}</tr>`;
    }).join("");
    return (
      `<div class="artifact-document-table-scroll"${sourceLineAttribute(firstLineIndex)}><table>`
        + `<thead><tr>${headerHtml}</tr></thead>`
        + `<tbody>${bodyHtml}</tbody>`
      + "</table></div>"
    );
  }

  function renderMarkdown(source) {
    const lines = String(source || "").split("\n");
    let html = "";
    let listTag = null;
    const closeList = () => {
      if (!listTag) return;
      html += `</${listTag}>`;
      listTag = null;
    };
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      const fence = line.match(/^```\s*([a-zA-Z0-9_-]+)?\s*$/);
      if (fence) {
        closeList();
        const language = (fence[1] || "").toLowerCase();
        const start = index;
        const body = [];
        index += 1;
        while (index < lines.length && !/^```\s*$/.test(lines[index])) {
          body.push(lines[index]);
          index += 1;
        }
        const blockSource = body.join("\n");
        if (language === "mermaid") {
          html += renderMermaidBlock(blockSource, start);
        } else {
          html += `<pre${sourceLineAttribute(start)}><code${language ? ` data-language="${escapeHtml(language)}"` : ""}>${escapeHtml(blockSource)}</code></pre>`;
        }
        continue;
      }
      if (line.includes("|") && lines[index + 1]?.includes("|") && isMarkdownTableSeparator(lines[index + 1])) {
        closeList();
        const firstLineIndex = index;
        const separatorLine = lines[index + 1];
        const rows = [];
        index += 2;
        while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
          rows.push({ line: lines[index], index });
          index += 1;
        }
        index -= 1;
        html += renderMarkdownTable(line, separatorLine, rows, firstLineIndex);
        continue;
      }
      const heading = line.match(/^(#{1,3})\s+(.+)/);
      if (heading) {
        closeList();
        const depth = heading[1].length;
        html += `<h${depth}${sourceLineAttribute(index)}>${renderInlineMarkdown(heading[2])}</h${depth}>`;
        continue;
      }
      if (/^---+$/.test(line.trim())) {
        closeList();
        html += `<hr${sourceLineAttribute(index)}>`;
        continue;
      }
      const unordered = line.match(/^[-*]\s+(.+)/);
      if (unordered) {
        if (listTag !== "ul") {
          closeList();
          html += "<ul>";
          listTag = "ul";
        }
        html += `<li${sourceLineAttribute(index)}>${renderInlineMarkdown(unordered[1])}</li>`;
        continue;
      }
      const ordered = line.match(/^\d+\.\s+(.+)/);
      if (ordered) {
        if (listTag !== "ol") {
          closeList();
          html += "<ol>";
          listTag = "ol";
        }
        html += `<li${sourceLineAttribute(index)}>${renderInlineMarkdown(ordered[1])}</li>`;
        continue;
      }
      if (!line.trim()) {
        closeList();
        continue;
      }
      closeList();
      html += `<p${sourceLineAttribute(index)}>${renderInlineMarkdown(line)}</p>`;
    }
    closeList();
    return html;
  }

  function markdownDiagnostics(content) {
    const lines = String(content || "").split("\n");
    const words = String(content || "").trim() ? String(content || "").trim().split(/\s+/).length : 0;
    const headings = lines
      .map((line, index) => ({ match: line.match(/^(#{1,6})\s+(.+)$/), line: index + 1 }))
      .filter((item) => item.match)
      .map((item) => ({ depth: item.match[1].length, text: item.match[2].trim(), line: item.line }));
    return { line_count: content ? lines.length : 0, word_count: words, heading_count: headings.length, headings };
  }

  ROOT.markdown = {
    renderMarkdown,
    markdownDiagnostics,
  };
}());
