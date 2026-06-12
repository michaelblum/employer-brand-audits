#!/usr/bin/env python3
"""Serve a local artifact viewer with transient annotation state."""

import argparse
import json
import mimetypes
import posixpath
import shutil
import sys
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "playwright-cli-public-page-matrix" / "latest" / "manifest.json"
)
IMAGE_ARTIFACT_KEYS = {
    "viewport": "Viewport",
    "full_page": "Full Page",
    "element": "Element",
}
MARKDOWN_ARTIFACT_KEYS = {
    "markdown": "Markdown",
    "md": "Markdown",
    "report": "Report",
    "summary": "Summary",
    "analysis": "Analysis",
    "synthesis": "Synthesis",
}

HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Artifacts</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0d0d0f;
      --bar: #141416;
      --panel: #18181b;
      --panel-2: #202024;
      --ink: #d6d6da;
      --muted: #8f8f98;
      --line: #2b2b31;
      --accent: #6ea8ff;
      --selection: rgba(110, 168, 255, 0.26);
      --selection-line: #6ea8ff;
      --shadow: 0 12px 34px rgba(0, 0, 0, 0.38);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      overflow: hidden;
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button {
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }
    button:hover { background: var(--panel-2); }
    .toolbar {
      position: relative;
      z-index: 10;
      height: 52px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 14px;
      background: var(--bar);
      border-bottom: 1px solid var(--line);
    }
    .toolbar.primary {
      width: 100%;
      z-index: 90;
    }
    .toolbar.secondary {
      height: 56px;
      justify-content: space-between;
    }
    .group {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .icon-button {
      width: 38px;
      height: 38px;
      display: inline-grid;
      place-items: center;
      color: var(--muted);
      font-size: 20px;
    }
    .overview-button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      height: 38px;
      padding: 0 12px;
      color: var(--ink);
      background: var(--panel);
      border: 1px solid var(--line);
    }
    .artifact-title {
      flex: 0 1 auto;
      max-width: min(56vw, 780px);
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .artifact-time {
      color: var(--muted);
      font-weight: 500;
    }
    .top-spacer { flex: 1; }
    .popover, .menu {
      position: absolute;
      z-index: 120;
      min-width: 300px;
      max-width: min(520px, calc(100vw - 24px));
      max-height: min(520px, calc(100vh - 120px));
      overflow: auto;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }
    .popover[hidden], .menu[hidden] { display: none; }
    .popover { left: 14px; top: 46px; }
    .menu { right: 58px; top: 44px; min-width: 210px; }
    .artifact-option, .menu button {
      width: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 2px;
      padding: 10px;
      text-align: left;
      letter-spacing: 0;
    }
    .artifact-option.active { background: var(--panel-2); }
    .small {
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .shell {
      height: calc(100vh - 52px);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      min-width: 0;
    }
    .shell.sidebar-hidden { grid-template-columns: minmax(0, 1fr) 0; }
    .shell.sidebar-hidden .sidebar { display: none; }
    .stage-column {
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: 56px minmax(0, 1fr);
    }
    .stage {
      position: relative;
      min-width: 0;
      min-height: 0;
      overflow: auto;
      display: grid;
      place-items: start center;
      padding: 32px;
      background: #101012;
    }
    .image-controls {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
    }
    .dimension-readout {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .zoom-control {
      display: grid;
      grid-template-columns: 34px 74px 24px;
      align-items: center;
      height: 38px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 9px;
      background: var(--panel);
    }
    .zoom-fit {
      width: 34px;
      height: 38px;
      display: grid;
      place-items: center;
      border-right: 1px solid var(--line);
      border-radius: 0;
      color: var(--muted);
    }
    .zoom-fit svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }
    .zoom-control input {
      width: 74px;
      height: 38px;
      border: 0;
      outline: 0;
      padding: 0 8px;
      color: var(--ink);
      background: transparent;
      font: inherit;
      text-align: right;
    }
    .zoom-steps {
      display: grid;
      grid-template-rows: 1fr 1fr;
      height: 38px;
      border-left: 1px solid var(--line);
    }
    .zoom-steps button {
      width: 24px;
      height: 19px;
      border-radius: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1;
    }
    .zoom-steps button + button { border-top: 1px solid var(--line); }
    .image-wrap {
      position: relative;
      display: inline-block;
      user-select: none;
    }
    .image-wrap.centered {
      align-self: center;
      justify-self: center;
    }
    .image-wrap img {
      display: block;
      width: auto;
      max-width: none;
      height: auto;
      background: #000;
      box-shadow: 0 0 0 1px #27364d, 0 16px 40px rgba(0, 0, 0, 0.42);
    }
    .markdown-wrap {
      position: relative;
      width: min(980px, 100%);
      min-height: 100%;
      align-self: stretch;
      justify-self: center;
      display: grid;
      grid-template-rows: minmax(0, 1fr);
      color: #ececf0;
      background: #18181b;
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.34);
      overflow: hidden;
    }
    .markdown-wrap[hidden] { display: none; }
    .markdown-preview {
      overflow: auto;
      padding: 36px 44px 72px;
      background: #f4f0e8;
      color: #1f1f21;
      font: 16px/1.62 Georgia, "Times New Roman", serif;
    }
    .markdown-preview h1,
    .markdown-preview h2,
    .markdown-preview h3 {
      margin: 1.15em 0 0.42em;
      color: #111113;
      font-family: ui-serif, Georgia, "Times New Roman", serif;
      line-height: 1.12;
    }
    .markdown-preview h1 { font-size: 34px; }
    .markdown-preview h2 { font-size: 25px; }
    .markdown-preview h3 { font-size: 20px; }
    .markdown-preview p,
    .markdown-preview li {
      max-width: 76ch;
    }
    .markdown-preview code,
    .markdown-preview pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .markdown-preview pre {
      padding: 14px 16px;
      overflow: auto;
      border-radius: 10px;
      background: #171717;
      color: #f4f4f5;
      font-size: 13px;
    }
    .markdown-preview [data-source-line].line-hit {
      outline: 2px solid rgba(45, 108, 223, 0.72);
      background: rgba(45, 108, 223, 0.12);
    }
    .markdown-source {
      width: 100%;
      height: 100%;
      min-height: 60vh;
      resize: none;
      border: 0;
      outline: 0;
      padding: 24px 28px 72px;
      color: #f4f4f5;
      background: #171717;
      font: 13px/1.62 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      tab-size: 2;
    }
    .markdown-source[hidden],
    .markdown-preview[hidden] {
      display: none;
    }
    .markdown-controls {
      display: none;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
    }
    .markdown-controls.visible { display: flex; }
    .segmented {
      display: inline-flex;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 9px;
      background: var(--panel);
    }
    .segmented button {
      height: 36px;
      padding: 0 12px;
      border-radius: 0;
      color: var(--muted);
    }
    .segmented button.active {
      color: var(--ink);
      background: var(--panel-2);
    }
    .selection {
      position: absolute;
      border: 2px solid var(--selection-line);
      background: var(--selection);
      pointer-events: none;
    }
    .hover-marker {
      position: absolute;
      width: 20px;
      height: 20px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: #1f7cff;
      color: #fff;
      font-size: 13px;
      box-shadow: 0 0 0 3px rgba(31, 124, 255, 0.24), 0 8px 20px rgba(0, 0, 0, 0.35);
      transform: translate(-50%, -50%);
      pointer-events: none;
      z-index: 4;
    }
    .hover-marker[hidden] { display: none; }
    .markdown-marker {
      position: absolute;
      z-index: 4;
      border: 2px solid var(--selection-line);
      border-radius: 8px;
      background: rgba(110, 168, 255, 0.13);
      pointer-events: none;
    }
    .markdown-marker[hidden] { display: none; }
    .comment-popover {
      position: fixed;
      z-index: 50;
      width: min(420px, calc(100vw - 28px));
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }
    .comment-popover[hidden] { display: none; }
    .dictation-field {
      position: relative;
    }
    .comment-popover textarea, .edit-box textarea {
      width: 100%;
      min-height: 64px;
      resize: vertical;
      color: var(--ink);
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
    }
    .dictation-field textarea {
      padding-right: 74px;
    }
    .dictation-control {
      position: absolute;
      right: 10px;
      bottom: 10px;
      min-width: 52px;
      height: 30px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      padding: 0 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #171a20;
      color: var(--muted);
    }
    .dictation-control:hover { color: var(--ink); }
    .dictation-control.recording {
      border-color: rgba(110, 168, 255, 0.72);
      color: #dbeafe;
      background: #1a2942;
    }
    .dictation-control.error {
      border-color: #78350f;
      color: #fed7aa;
      background: #2b1709;
    }
    .dictation-icon {
      width: 15px;
      height: 15px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    .dictation-icon svg {
      width: 15px;
      height: 15px;
      display: block;
      fill: currentColor;
    }
    .dictation-wave {
      display: none;
      align-items: center;
      gap: 2px;
      height: 14px;
    }
    .dictation-control.recording .dictation-wave,
    .dictation-control.transcribing .dictation-wave {
      display: inline-flex;
    }
    .dictation-wave i {
      width: 2px;
      height: 7px;
      border-radius: 999px;
      background: currentColor;
      opacity: 0.95;
      transform-origin: center bottom;
      animation: dictation-wave 0.9s ease-in-out infinite;
    }
    .dictation-wave i:nth-child(2) {
      animation-delay: 0.15s;
      height: 11px;
    }
    .dictation-wave i:nth-child(3) {
      animation-delay: 0.3s;
      height: 8px;
    }
    .dictation-wave i:nth-child(4) {
      animation-delay: 0.45s;
      height: 10px;
    }
    @keyframes dictation-wave {
      0%, 100% { transform: scaleY(0.48); opacity: 0.54; }
      50% { transform: scaleY(1); opacity: 1; }
    }
    .comment-actions {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
    }
    .action-button {
      height: 36px;
      padding: 0 12px;
      border-radius: 8px;
      background: var(--panel-2);
      color: var(--ink);
    }
    .action-button.primary { background: #2d6cdf; }
    .sidebar {
      min-width: 0;
      overflow: auto;
      border-left: 1px solid var(--line);
      background: #111113;
    }
    .artifact-row {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 8px;
    }
    .artifact-row.active { background: #17191f; }
    .row-title {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      min-width: 0;
    }
    .name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
    }
    .annotation {
      margin-left: 14px;
      padding: 8px 0 8px 10px;
      border-left: 2px solid var(--line);
      cursor: grab;
    }
    .annotation:hover { border-left-color: var(--accent); }
    .annotation.dragging {
      opacity: 0.45;
      cursor: grabbing;
    }
    .annotation-text {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--accent);
    }
    .toast {
      position: fixed;
      right: 16px;
      bottom: 16px;
      max-width: 360px;
      padding: 12px 14px;
      border-radius: 8px;
      color: #fff;
      background: #111827;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 160ms ease, transform 160ms ease;
      pointer-events: none;
      z-index: 60;
    }
    .toast.visible {
      opacity: 1;
      transform: translateY(0);
    }
    @media (max-width: 900px) {
      .shell { grid-template-columns: 1fr; }
      .stage-column { min-height: 64vh; }
      .sidebar {
        height: 36vh;
        border-left: 0;
        border-top: 1px solid var(--line);
      }
      .stage { padding: 16px; }
    }
  </style>
</head>
<body>
  <div class="toolbar primary">
    <button class="overview-button" id="overview" type="button"><span>☰</span><span>Overview</span></button>
    <button class="icon-button" id="prev" type="button" title="Previous artifact">‹</button>
    <div class="artifact-title" id="artifact-title"></div>
    <button class="icon-button" id="next" type="button" title="Next artifact">›</button>
    <div class="popover" id="overview-popover" hidden></div>
    <div class="top-spacer"></div>
    <div class="group">
      <button class="icon-button" id="menu-button" type="button" title="Artifact menu">⋮</button>
      <div class="menu" id="artifact-menu" hidden>
        <button type="button" id="copy-artifact">Copy</button>
        <button type="button" id="copy-path">Copy Path</button>
      </div>
      <button class="icon-button" id="toggle-sidebar" type="button" title="Toggle sidebar">▣</button>
    </div>
  </div>
  <main class="shell" id="shell">
    <div class="stage-column">
      <div class="toolbar secondary">
        <div class="dimension-readout" id="dimension-readout"></div>
        <div class="image-controls" id="image-controls">
          <div class="zoom-control" id="zoom-control">
            <button class="zoom-fit" id="zoom-fit" type="button" aria-label="Smart fit" title="Smart fit">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8 3H5a2 2 0 0 0-2 2v3"></path>
                <path d="M16 3h3a2 2 0 0 1 2 2v3"></path>
                <path d="M8 21H5a2 2 0 0 1-2-2v-3"></path>
                <path d="M16 21h3a2 2 0 0 0 2-2v-3"></path>
                <path d="M9 12h6"></path>
                <path d="M12 9v6"></path>
              </svg>
            </button>
            <input id="zoom-input" type="text" inputmode="numeric" aria-label="Zoom percentage">
            <div class="zoom-steps">
              <button id="zoom-in" type="button" aria-label="Zoom in">+</button>
              <button id="zoom-out" type="button" aria-label="Zoom out">-</button>
            </div>
          </div>
        </div>
        <div class="markdown-controls" id="markdown-controls">
          <div class="segmented" role="group" aria-label="Markdown view mode">
            <button id="markdown-preview-mode" type="button" data-markdown-mode="preview">Preview</button>
            <button id="markdown-source-mode" type="button" data-markdown-mode="source">Edit</button>
          </div>
          <button class="action-button" id="markdown-revert" type="button">Revert</button>
          <button class="action-button primary" id="markdown-save" type="button">Save</button>
        </div>
      </div>
      <section class="stage" id="stage">
        <div class="image-wrap" id="image-wrap">
          <img id="artifact-image" alt="" draggable="false">
          <div class="selection" id="selection" hidden></div>
          <div class="hover-marker" id="hover-marker" hidden>💡</div>
        </div>
        <div class="markdown-wrap" id="markdown-wrap" hidden>
          <div class="markdown-preview" id="markdown-preview"></div>
          <textarea class="markdown-source" id="markdown-source" spellcheck="true" hidden></textarea>
          <div class="markdown-marker" id="markdown-marker" hidden></div>
        </div>
        <div class="comment-popover" id="comment-popover" hidden>
          <div class="dictation-field">
            <textarea id="comment-text" placeholder="Leave a comment"></textarea>
            <button class="dictation-control" id="comment-dictation" type="button" aria-label="Start dictation" title="Start dictation">
              <span class="dictation-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-4a1 1 0 1 1 2 0 7 7 0 0 1-6 6.92V20h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-3.08A7 7 0 0 1 5 10a1 1 0 1 1 2 0 5 5 0 0 0 10 0Z"></path>
                </svg>
              </span>
              <span class="dictation-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
            </button>
          </div>
          <div class="comment-actions">
            <div class="group">
              <button class="action-button" id="secondary-comment-action" type="button">Cancel</button>
              <button class="action-button primary" id="primary-comment-action" type="button">Add Comment</button>
            </div>
          </div>
        </div>
      </section>
    </div>
    <aside class="sidebar" id="sidebar"></aside>
  </main>
  <div class="toast" id="toast"></div>
  <script>
    const app = {
      collection: null,
      annotations: {},
      index: 0,
      drag: null,
      pendingAnchor: null,
      editorMode: "create",
      editing: null,
      activeMarker: null,
      sidebarVisible: true,
      zoomPercent: 100,
      zoomMode: "stage-fit",
      markdownMode: "preview",
      markdownContent: {},
      markdownSavedContent: {},
      markdownDirty: {},
    };
    const $ = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));
    const artifact = () => app.collection.artifacts[app.index];
    const artifactAnnotations = (id) => app.annotations[id] || [];
    const artifactIndexById = (id) => app.collection.artifacts.findIndex((item) => item.id === id);
    const annotationById = (artifactId, annotationId) => artifactAnnotations(artifactId).find((note) => note.id === annotationId);
    const artifactUrl = (item) => `/artifact/${String(item.path || "").split("/").map(encodeURIComponent).join("/")}`;
    const isImageArtifact = (item = artifact()) => item.type === "image";
    const isMarkdownArtifact = (item = artifact()) => item.type === "markdown";
    const annotationAnchor = (note) => note?.anchor || {};
    const imageRectAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "image_region" ? anchor.rect : null;
    };
    const textRangeAnchor = (note) => {
      const anchor = annotationAnchor(note);
      return anchor.type === "text_range" ? anchor : null;
    };
    const anchorSummary = (anchor = {}) => {
      if (anchor.type === "image_region" && anchor.rect) {
        return `image ${anchor.rect.x},${anchor.rect.y} ${anchor.rect.width}x${anchor.rect.height}`;
      }
      if (anchor.type === "text_range" && anchor.start && anchor.end) {
        return anchor.start.line === anchor.end.line
          ? `line ${anchor.start.line}`
          : `lines ${anchor.start.line}-${anchor.end.line}`;
      }
      return "unanchored";
    };
    const formatTime = (epoch) => {
      if (!epoch) return "";
      return new Date(epoch * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    };

    function showToast(message) {
      const toast = $("toast");
      toast.textContent = message;
      toast.classList.add("visible");
      clearTimeout(showToast.timer);
      showToast.timer = setTimeout(() => toast.classList.remove("visible"), 1400);
    }

    async function copyText(value) {
      await navigator.clipboard.writeText(value);
      showToast("Copied");
    }

    async function syncAnnotations() {
      const response = await fetch("/api/annotation-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ annotations: app.annotations }),
      });
      if (!response.ok) showToast("Annotation sync failed");
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
          const language = fence[1] || "";
          const start = index;
          const body = [];
          index += 1;
          while (index < lines.length && !/^```\s*$/.test(lines[index])) {
            body.push(lines[index]);
            index += 1;
          }
          html += `<pre${sourceLineAttribute(start)}><code${language ? ` data-language="${escapeHtml(language)}"` : ""}>${escapeHtml(body.join("\n"))}</code></pre>`;
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

    function clampZoom(value) {
      return Math.min(400, Math.max(10, Math.round(Number(value) || 100)));
    }

    function stageViewportSize() {
      const stage = $("stage");
      const style = window.getComputedStyle(stage);
      const width = stage.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      const height = stage.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
      return {
        width: Math.max(1, width),
        height: Math.max(1, height),
      };
    }

    function renderedImageSize(zoomPercent = app.zoomPercent) {
      const image = $("artifact-image");
      return {
        width: image.naturalWidth * zoomPercent / 100,
        height: image.naturalHeight * zoomPercent / 100,
      };
    }

    function updateImageAlignment() {
      const image = $("artifact-image");
      if (!image.naturalWidth) return;
      const stageSize = stageViewportSize();
      const imageSize = renderedImageSize();
      $("image-wrap").classList.toggle(
        "centered",
        imageSize.width <= stageSize.width && imageSize.height <= stageSize.height
      );
    }

    function updateMooringOverlays() {
      if (app.editing) {
        placeSelectionForAnchor(app.editing.anchor);
        placePopoverForAnchor(app.editing.anchor);
      } else if (app.pendingAnchor && app.editorMode === "create" && !$("comment-popover").hidden) {
        placeSelectionForAnchor(app.pendingAnchor);
        placePopoverForAnchor(app.pendingAnchor);
      }
      if (app.activeMarker) {
        const note = annotationById(app.activeMarker.artifactId, app.activeMarker.annotationId);
        if (note && artifact().id === app.activeMarker.artifactId) {
          placeMarkerForAnchor(note.anchor);
        }
      }
    }

    function applyZoom(value, mode = "manual") {
      const image = $("artifact-image");
      app.zoomPercent = clampZoom(value);
      app.zoomMode = mode;
      $("zoom-input").value = `${app.zoomPercent}%`;
      if (image.naturalWidth) {
        image.style.width = `${Math.max(1, Math.round(image.naturalWidth * app.zoomPercent / 100))}px`;
      }
      updateImageAlignment();
      updateMooringOverlays();
    }

    function stageFitZoom() {
      const image = $("artifact-image");
      if (!image.naturalWidth || !image.naturalHeight) return 100;
      const stageSize = stageViewportSize();
      const smallerThanStageAt100 =
        image.naturalWidth <= stageSize.width && image.naturalHeight <= stageSize.height;
      if (!smallerThanStageAt100) {
        return Math.min(stageSize.width / image.naturalWidth, stageSize.height / image.naturalHeight) * 100;
      }
      if (image.naturalWidth >= image.naturalHeight) {
        return stageSize.width / image.naturalWidth * 100;
      }
      return stageSize.height / image.naturalHeight * 100;
    }

    function smartFit() {
      const image = $("artifact-image");
      if (!image.naturalWidth || !image.naturalHeight) return;
      const stageSize = stageViewportSize();
      const smallerThanStageAt100 =
        image.naturalWidth <= stageSize.width && image.naturalHeight <= stageSize.height;
      if (smallerThanStageAt100 && app.zoomMode !== "actual-size") {
        applyZoom(100, "actual-size");
        return;
      }
      applyZoom(stageFitZoom(), "stage-fit");
    }

    function updateDimensionReadout() {
      const item = artifact();
      if (isImageArtifact(item)) {
        const dimensions = item.dimensions || {};
        const width = dimensions.width || $("artifact-image").naturalWidth || "unknown";
        const height = dimensions.height || $("artifact-image").naturalHeight || "unknown";
        $("dimension-readout").textContent = `${width} x ${height} px`;
        return;
      }
      const content = app.markdownContent[item.id] || "";
      const diagnostics = markdownDiagnostics(content);
      $("dimension-readout").textContent = `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
    }

    function afterImageReady(callback) {
      const image = $("artifact-image");
      if (image.complete && image.naturalWidth) {
        callback();
        return;
      }
      image.addEventListener("load", callback, { once: true });
    }

    function setArtifact(index) {
      const count = app.collection.artifacts.length;
      app.index = (index + count) % count;
      closeEditor();
      hideAnnotationMarker();
      render();
    }

    function move(delta) {
      setArtifact(app.index + delta);
    }

    function renderTitle() {
      const item = artifact();
      $("artifact-title").innerHTML = `${escapeHtml(item.name)} <span class="artifact-time">(${escapeHtml(formatTime(item.created_at_epoch))})</span>`;
    }

    function renderImage() {
      const item = artifact();
      const image = $("artifact-image");
      $("image-wrap").hidden = false;
      $("markdown-wrap").hidden = true;
      $("image-controls").style.display = "flex";
      $("markdown-controls").classList.remove("visible");
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
      $("hover-marker").hidden = true;
      $("comment-popover").hidden = true;
      updateDimensionReadout();
      image.onload = () => {
        updateDimensionReadout();
        if (app.zoomMode === "stage-fit") {
          applyZoom(stageFitZoom(), "stage-fit");
        } else if (app.zoomMode === "actual-size") {
          applyZoom(100, "actual-size");
        } else {
          applyZoom(app.zoomPercent, "manual");
        }
      };
      image.src = artifactUrl(item);
      image.alt = item.name;
      if (image.complete && image.naturalWidth) {
        image.onload();
      }
    }

    async function loadMarkdown(item) {
      if (Object.prototype.hasOwnProperty.call(app.markdownContent, item.id)) return app.markdownContent[item.id];
      const response = await fetch(artifactUrl(item), { cache: "no-store" });
      if (!response.ok) throw new Error(`Markdown fetch failed: ${response.status}`);
      const content = await response.text();
      app.markdownContent[item.id] = content;
      app.markdownSavedContent[item.id] = content;
      app.markdownDirty[item.id] = false;
      return content;
    }

    function syncMarkdownModeButtons() {
      for (const button of document.querySelectorAll("[data-markdown-mode]")) {
        const active = button.dataset.markdownMode === app.markdownMode;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      }
    }

    function renderMarkdownBody(item) {
      const content = app.markdownContent[item.id] || "";
      $("markdown-preview").innerHTML = renderMarkdown(content);
      $("markdown-source").value = content;
      $("markdown-preview").hidden = app.markdownMode !== "preview";
      $("markdown-source").hidden = app.markdownMode !== "source";
      $("markdown-save").disabled = !app.markdownDirty[item.id];
      syncMarkdownModeButtons();
      updateDimensionReadout();
      renderMarkdownHighlights();
    }

    function renderMarkdownHighlights() {
      $("markdown-preview").querySelectorAll(".line-hit").forEach((node) => node.classList.remove("line-hit"));
      if (app.markdownMode !== "preview" || !isMarkdownArtifact()) return;
      for (const note of artifactAnnotations(artifact().id)) {
        const anchor = textRangeAnchor(note);
        if (!anchor) continue;
        for (const node of markdownLineElementsForRange(anchor)) {
          node.classList.add("line-hit");
        }
      }
      if (app.pendingAnchor?.type === "text_range") {
        for (const node of markdownLineElementsForRange(app.pendingAnchor)) {
          node.classList.add("line-hit");
        }
      }
    }

    async function renderMarkdownArtifact() {
      const item = artifact();
      $("image-wrap").hidden = true;
      $("markdown-wrap").hidden = false;
      $("image-controls").style.display = "none";
      $("markdown-controls").classList.add("visible");
      $("selection").hidden = true;
      $("hover-marker").hidden = true;
      $("comment-popover").hidden = true;
      try {
        await loadMarkdown(item);
        renderMarkdownBody(item);
      } catch (error) {
        $("markdown-preview").hidden = false;
        $("markdown-source").hidden = true;
        $("markdown-preview").innerHTML = `<p>Failed to load markdown: ${escapeHtml(error.message)}</p>`;
      }
    }

    async function saveMarkdownArtifact() {
      const item = artifact();
      if (!isMarkdownArtifact(item)) return;
      const content = app.markdownContent[item.id] || "";
      const response = await fetch(`/api/artifact-content/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        headers: { "content-type": "text/markdown; charset=utf-8" },
        body: content,
      });
      if (!response.ok) {
        showToast("Markdown save failed");
        return;
      }
      app.markdownSavedContent[item.id] = content;
      app.markdownDirty[item.id] = false;
      renderMarkdownBody(item);
      showToast("Markdown saved");
    }

    function revertMarkdownArtifact() {
      const item = artifact();
      if (!isMarkdownArtifact(item)) return;
      app.markdownContent[item.id] = app.markdownSavedContent[item.id] || "";
      app.markdownDirty[item.id] = false;
      renderMarkdownBody(item);
      showToast("Markdown reverted");
    }

    function setMarkdownMode(mode) {
      app.markdownMode = mode === "source" ? "source" : "preview";
      renderMarkdownBody(artifact());
      if (app.markdownMode === "source") $("markdown-source").focus();
    }

    function renderArtifact() {
      if (isMarkdownArtifact()) {
        void renderMarkdownArtifact();
        return;
      }
      renderImage();
    }

    function renderOverview() {
      $("overview-popover").innerHTML = app.collection.artifacts.map((item, index) => `
        <button class="artifact-option ${index === app.index ? "active" : ""}" type="button" data-index="${index}">
          <span>${escapeHtml(item.name)}</span>
          <span class="small">${escapeHtml(item.type || "file")} · ${escapeHtml(item.path)}</span>
        </button>
      `).join("");
      $("overview-popover").querySelectorAll("[data-index]").forEach((button) => {
        button.addEventListener("click", () => {
          $("overview-popover").hidden = true;
          setArtifact(Number(button.dataset.index));
        });
      });
    }

    function renderSidebar() {
      $("sidebar").innerHTML = app.collection.artifacts.map((item, index) => {
        const notes = artifactAnnotations(item.id);
        const annotationHtml = notes.length
          ? notes.map((note) => `
            <div class="annotation" draggable="true" data-artifact-id="${escapeHtml(item.id)}" data-annotation-id="${escapeHtml(note.id)}">
              <div class="annotation-text" title="${escapeHtml(note.comment)}">${escapeHtml(note.comment)}</div>
              <div class="small">${escapeHtml(anchorSummary(note.anchor))}</div>
            </div>
          `).join("")
          : "";
        return `
          <div class="artifact-row ${index === app.index ? "active" : ""}" data-index="${index}">
            <div class="row-title">
              <div class="name">${escapeHtml(item.name)}</div>
              <div class="small">${escapeHtml(item.type || "file")}</div>
            </div>
            ${annotationHtml}
          </div>
        `;
      }).join("");
      $("sidebar").querySelectorAll(".artifact-row[data-index]").forEach((row) => {
        row.addEventListener("click", (event) => {
          if (event.target.closest(".annotation")) return;
          setArtifact(Number(row.dataset.index));
        });
      });
      $("sidebar").querySelectorAll(".annotation").forEach((row) => {
        row.addEventListener("mouseenter", () => showAnnotationMarker(row.dataset.artifactId, row.dataset.annotationId));
        row.addEventListener("mouseleave", hideAnnotationMarker);
        row.addEventListener("click", (event) => {
          event.stopPropagation();
          selectAnnotation(row.dataset.artifactId, row.dataset.annotationId);
        });
        row.addEventListener("dragstart", (event) => {
          row.classList.add("dragging");
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", JSON.stringify({
            artifactId: row.dataset.artifactId,
            annotationId: row.dataset.annotationId,
          }));
        });
        row.addEventListener("dragend", () => row.classList.remove("dragging"));
        row.addEventListener("dragover", (event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
        });
        row.addEventListener("drop", async (event) => {
          event.preventDefault();
          const targetArtifactId = row.dataset.artifactId;
          const targetAnnotationId = row.dataset.annotationId;
          const payload = JSON.parse(event.dataTransfer.getData("text/plain") || "{}");
          if (payload.artifactId !== targetArtifactId || payload.annotationId === targetAnnotationId) return;
          const notes = [...artifactAnnotations(targetArtifactId)];
          const from = notes.findIndex((note) => note.id === payload.annotationId);
          const to = notes.findIndex((note) => note.id === targetAnnotationId);
          if (from < 0 || to < 0) return;
          const [moved] = notes.splice(from, 1);
          notes.splice(to, 0, moved);
          app.annotations[targetArtifactId] = notes;
          await syncAnnotations();
          renderSidebar();
        });
      });
    }

    function renderShell() {
      $("shell").classList.toggle("sidebar-hidden", !app.sidebarVisible);
    }

    function render() {
      renderTitle();
      renderArtifact();
      renderOverview();
      renderSidebar();
      renderShell();
    }

    function imagePoint(event) {
      const image = $("artifact-image");
      const rect = image.getBoundingClientRect();
      const x = Math.min(Math.max(event.clientX - rect.left, 0), rect.width);
      const y = Math.min(Math.max(event.clientY - rect.top, 0), rect.height);
      return { x, y };
    }

    function placeSelection(displayRect) {
      const selection = $("selection");
      const imageRect = $("artifact-image").getBoundingClientRect();
      const wrapRect = $("image-wrap").getBoundingClientRect();
      selection.style.left = `${displayRect.x + imageRect.left - wrapRect.left}px`;
      selection.style.top = `${displayRect.y + imageRect.top - wrapRect.top}px`;
      selection.style.width = `${displayRect.width}px`;
      selection.style.height = `${displayRect.height}px`;
      selection.hidden = false;
    }

    function displayRectFromNatural(rect) {
      const image = $("artifact-image");
      const imageRect = image.getBoundingClientRect();
      const sx = imageRect.width / image.naturalWidth;
      const sy = imageRect.height / image.naturalHeight;
      return {
        x: rect.x * sx,
        y: rect.y * sy,
        width: rect.width * sx,
        height: rect.height * sy,
      };
    }

    function markdownLineElementsForRange(anchor) {
      if (!anchor?.start?.line || !anchor?.end?.line) return [];
      const start = Math.min(anchor.start.line, anchor.end.line);
      const end = Math.max(anchor.start.line, anchor.end.line);
      return [...$("markdown-preview").querySelectorAll("[data-source-line]")]
        .filter((node) => {
          const line = Number(node.dataset.sourceLine);
          return line >= start && line <= end;
        });
    }

    function markdownDisplayRectFromAnchor(anchor) {
      const elements = markdownLineElementsForRange(anchor);
      if (!elements.length) return null;
      const wrapRect = $("markdown-wrap").getBoundingClientRect();
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

    function placeSelectionForRect(rect) {
      placeSelection(displayRectFromNatural(rect));
    }

    function placePopoverForRect(rect) {
      openComment(displayRectFromNatural(rect));
    }

    function placeSelectionForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        $("markdown-marker").hidden = true;
        placeSelectionForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        $("selection").hidden = true;
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (!displayRect) return;
        const marker = $("markdown-marker");
        marker.style.left = `${displayRect.x}px`;
        marker.style.top = `${displayRect.y}px`;
        marker.style.width = `${displayRect.width}px`;
        marker.style.height = `${displayRect.height}px`;
        marker.hidden = false;
      }
    }

    function placePopoverForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        placePopoverForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (displayRect) openComment(displayRect, $("markdown-wrap"));
      }
    }

    function placeMarkerForRect(rect) {
      const marker = $("hover-marker");
      const displayRect = displayRectFromNatural(rect);
      const imageRect = $("artifact-image").getBoundingClientRect();
      const wrapRect = $("image-wrap").getBoundingClientRect();
      marker.style.left = `${displayRect.x + displayRect.width / 2 + imageRect.left - wrapRect.left}px`;
      marker.style.top = `${displayRect.y + displayRect.height / 2 + imageRect.top - wrapRect.top}px`;
      marker.hidden = false;
    }

    function placeMarkerForAnchor(anchor) {
      if (anchor?.type === "image_region" && anchor.rect) {
        $("markdown-marker").hidden = true;
        placeMarkerForRect(anchor.rect);
        return;
      }
      if (anchor?.type === "text_range") {
        $("hover-marker").hidden = true;
        const displayRect = markdownDisplayRectFromAnchor(anchor);
        if (!displayRect) return;
        const marker = $("markdown-marker");
        marker.style.left = `${displayRect.x}px`;
        marker.style.top = `${displayRect.y}px`;
        marker.style.width = `${displayRect.width}px`;
        marker.style.height = `${displayRect.height}px`;
        marker.hidden = false;
      }
    }

    function hideAnnotationMarker() {
      app.activeMarker = null;
      $("hover-marker").hidden = true;
      $("markdown-marker").hidden = true;
    }

    function showAnnotationMarker(artifactId, annotationId) {
      const note = annotationById(artifactId, annotationId);
      if (!note) return;
      app.activeMarker = { artifactId, annotationId };
      const index = artifactIndexById(artifactId);
      if (index !== app.index) {
        setArtifact(index);
        app.activeMarker = { artifactId, annotationId };
        window.requestAnimationFrame(() => {
          if (isImageArtifact()) afterImageReady(() => placeMarkerForAnchor(note.anchor));
          else placeMarkerForAnchor(note.anchor);
        });
        return;
      }
      placeMarkerForAnchor(note.anchor);
    }

    function naturalRect(displayRect) {
      const image = $("artifact-image");
      const imageRect = image.getBoundingClientRect();
      const sx = image.naturalWidth / imageRect.width;
      const sy = image.naturalHeight / imageRect.height;
      return {
        x: Math.round(displayRect.x * sx),
        y: Math.round(displayRect.y * sy),
        width: Math.round(displayRect.width * sx),
        height: Math.round(displayRect.height * sy),
      };
    }

    function markdownPoint(event) {
      const rect = $("markdown-wrap").getBoundingClientRect();
      return {
        x: Math.min(Math.max(event.clientX - rect.left, 0), rect.width),
        y: Math.min(Math.max(event.clientY - rect.top, 0), rect.height),
      };
    }

    function placeMarkdownSelection(displayRect) {
      const marker = $("markdown-marker");
      marker.style.left = `${displayRect.x}px`;
      marker.style.top = `${displayRect.y}px`;
      marker.style.width = `${displayRect.width}px`;
      marker.style.height = `${displayRect.height}px`;
      marker.hidden = false;
    }

    function markdownAnchorFromDisplayRect(displayRect) {
      const wrapRect = $("markdown-wrap").getBoundingClientRect();
      const selectionRect = {
        left: wrapRect.left + displayRect.x,
        top: wrapRect.top + displayRect.y,
        right: wrapRect.left + displayRect.x + displayRect.width,
        bottom: wrapRect.top + displayRect.y + displayRect.height,
      };
      const hits = [...$("markdown-preview").querySelectorAll("[data-source-line]")]
        .map((node) => ({ node, rect: node.getBoundingClientRect(), line: Number(node.dataset.sourceLine) }))
        .filter(({ rect }) => rect.right >= selectionRect.left
          && rect.left <= selectionRect.right
          && rect.bottom >= selectionRect.top
          && rect.top <= selectionRect.bottom)
        .filter(({ line }) => Number.isFinite(line));
      if (!hits.length) return null;
      const startLine = Math.min(...hits.map((hit) => hit.line));
      const endLine = Math.max(...hits.map((hit) => hit.line));
      const content = app.markdownContent[artifact().id] || "";
      const lines = content.split("\n");
      const excerpt = lines.slice(startLine - 1, endLine).join("\n").slice(0, 600);
      return {
        type: "text_range",
        coordinate_space: "markdown_source",
        start: { line: startLine, column: 1 },
        end: { line: endLine, column: (lines[endLine - 1] || "").length + 1 },
        excerpt,
      };
    }

    function openComment(displayRect, relativeTo = $("artifact-image")) {
      const popover = $("comment-popover");
      const baseRect = relativeTo.getBoundingClientRect();
      const left = Math.min(baseRect.left + displayRect.x + displayRect.width + 10, window.innerWidth - 434);
      const top = Math.min(baseRect.top + displayRect.y, window.innerHeight - 190);
      popover.style.left = `${Math.max(14, left)}px`;
      popover.style.top = `${Math.max(14, top)}px`;
      popover.hidden = false;
      $("comment-text").focus();
    }

    function openCreateEditor(displayRect, relativeTo = $("artifact-image")) {
      app.editorMode = "create";
      app.editing = null;
      $("comment-text").value = "";
      $("secondary-comment-action").textContent = "Cancel";
      $("primary-comment-action").textContent = "Add Comment";
      openComment(displayRect, relativeTo);
    }

    function scrollRectIntoView(rect) {
      const image = $("artifact-image");
      const wrap = $("image-wrap");
      const stage = $("stage");
      if (!image.naturalWidth) return;
      const displayRect = displayRectFromNatural(rect);
      const targetLeft = wrap.offsetLeft + displayRect.x + displayRect.width / 2;
      const targetTop = wrap.offsetTop + displayRect.y + displayRect.height / 2;
      stage.scrollTo({
        left: Math.max(0, targetLeft - stage.clientWidth / 2),
        top: Math.max(0, targetTop - stage.clientHeight / 2),
        behavior: "auto",
      });
    }

    function scrollTextRangeIntoView(anchor) {
      if (!anchor?.start?.line) return;
      const target = $("markdown-preview").querySelector(`[data-source-line="${anchor.start.line}"]`);
      if (target) {
        target.scrollIntoView({ block: "center", inline: "nearest" });
        return;
      }
      const source = $("markdown-source");
      const lines = String(source.value || "").split("\n");
      const lineHeight = Number.parseFloat(window.getComputedStyle(source).lineHeight) || 21;
      source.scrollTop = Math.max(0, (Math.max(1, anchor.start.line) - 3) * lineHeight);
    }

    function openExistingEditor(note) {
      app.editorMode = "edit";
      app.editing = note;
      $("comment-text").value = note.comment;
      $("secondary-comment-action").textContent = "Delete";
      $("primary-comment-action").textContent = "Update";
      const anchor = note.anchor;
      if (anchor?.type === "image_region" && anchor.rect) {
        afterImageReady(() => {
          scrollRectIntoView(anchor.rect);
          window.requestAnimationFrame(() => {
            placeSelectionForAnchor(anchor);
            placePopoverForAnchor(anchor);
          });
        });
        return;
      }
      if (anchor?.type === "text_range") {
        if (app.markdownMode !== "preview") {
          app.markdownMode = "preview";
          renderMarkdownBody(artifact());
        }
        scrollTextRangeIntoView(anchor);
        window.requestAnimationFrame(() => {
          renderMarkdownHighlights();
          placeSelectionForAnchor(anchor);
          placePopoverForAnchor(anchor);
        });
      }
    }

    function closeEditor() {
      app.pendingAnchor = null;
      app.editing = null;
      app.editorMode = "create";
      $("comment-popover").hidden = true;
      $("selection").hidden = true;
      $("markdown-marker").hidden = true;
    }

    function selectAnnotation(artifactId, annotationId) {
      const index = artifactIndexById(artifactId);
      const note = annotationById(artifactId, annotationId);
      if (index < 0 || !note) return;
      if (index !== app.index) {
        app.index = index;
        render();
        window.requestAnimationFrame(() => openExistingEditor(note));
        return;
      }
      openExistingEditor(note);
    }

    function startDrag(event) {
      if (event.button !== 0) return;
      if (event.target.closest("#image-wrap")) {
        const point = imagePoint(event);
        app.drag = { type: "image", startX: point.x, startY: point.y };
        app.pendingAnchor = null;
        $("comment-popover").hidden = true;
        placeSelection({ x: point.x, y: point.y, width: 0, height: 0 });
        return;
      }
      if (app.markdownMode === "preview" && event.target.closest("#markdown-preview")) {
        const point = markdownPoint(event);
        app.drag = { type: "markdown", startX: point.x, startY: point.y };
        app.pendingAnchor = null;
        $("comment-popover").hidden = true;
        placeMarkdownSelection({ x: point.x, y: point.y, width: 0, height: 0 });
      }
    }

    function dragDisplayRect(point) {
      return {
        x: Math.min(app.drag.startX, point.x),
        y: Math.min(app.drag.startY, point.y),
        width: Math.abs(point.x - app.drag.startX),
        height: Math.abs(point.y - app.drag.startY),
      };
    }

    function moveDrag(event) {
      if (!app.drag) return;
      if (app.drag.type === "image") {
        placeSelection(dragDisplayRect(imagePoint(event)));
        return;
      }
      if (app.drag.type === "markdown") {
        placeMarkdownSelection(dragDisplayRect(markdownPoint(event)));
      }
    }

    function endDrag(event) {
      if (!app.drag) return;
      const type = app.drag.type;
      const displayRect = type === "markdown"
        ? dragDisplayRect(markdownPoint(event))
        : dragDisplayRect(imagePoint(event));
      app.drag = null;
      if (displayRect.width < 8 || displayRect.height < 8) {
        $("selection").hidden = true;
        $("markdown-marker").hidden = true;
        return;
      }
      if (type === "markdown") {
        const anchor = markdownAnchorFromDisplayRect(displayRect);
        if (!anchor) {
          $("markdown-marker").hidden = true;
          return;
        }
        app.pendingAnchor = anchor;
        renderMarkdownHighlights();
        openCreateEditor(displayRect, $("markdown-wrap"));
        return;
      }
      app.pendingAnchor = {
        type: "image_region",
        coordinate_space: "natural_image",
        rect: naturalRect(displayRect),
      };
      $("comment-popover").hidden = true;
      openCreateEditor(displayRect);
    }

    async function commitEditor() {
      const comment = $("comment-text").value.trim();
      if (!comment) return;
      if (app.editorMode === "edit" && app.editing) {
        app.editing.comment = comment;
        app.editing.updated_at_epoch = Math.floor(Date.now() / 1000);
        closeEditor();
        await syncAnnotations();
        renderSidebar();
        showToast("Comment updated");
        return;
      }
      if (!app.pendingAnchor) return;
      const item = artifact();
      const note = {
        id: `${item.id}-${Date.now().toString(36)}`,
        artifact_id: item.id,
        kind: "comment",
        anchor: app.pendingAnchor,
        comment,
        created_at_epoch: Math.floor(Date.now() / 1000),
        updated_at_epoch: null,
      };
      app.annotations[item.id] = [...artifactAnnotations(item.id), note];
      closeEditor();
      await syncAnnotations();
      renderSidebar();
      showToast("Comment added");
    }

    async function secondaryEditorAction() {
      if (app.editorMode === "edit" && app.editing) {
        const artifactId = app.editing.artifact_id;
        const noteId = app.editing.id;
        app.annotations[artifactId] = artifactAnnotations(artifactId).filter((note) => note.id !== noteId);
        closeEditor();
        await syncAnnotations();
        renderSidebar();
        showToast("Comment deleted");
        return;
      }
      closeEditor();
    }

    function insertTextAtCursor(input, value) {
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? input.value.length;
      const before = input.value.slice(0, start);
      const after = input.value.slice(end);
      const spacer = before && !before.endsWith(" ") ? " " : "";
      const text = `${spacer}${value}`.trimStart();
      input.value = `${before}${text}${after}`;
      const caret = before.length + text.length;
      input.focus();
      input.setSelectionRange(caret, caret);
    }

    function setupDictationControl({ buttonId, inputId }) {
      const button = $(buttonId);
      const input = $(inputId);
      let recognition = null;
      let state = "idle";

      const setState = (nextState) => {
        state = nextState;
        button.classList.toggle("recording", state === "recording");
        button.classList.toggle("transcribing", state === "transcribing");
        button.classList.toggle("error", state === "error");
        if (state === "recording") {
          button.title = "Stop dictation";
          button.setAttribute("aria-label", "Stop dictation");
        } else if (state === "transcribing") {
          button.title = "Transcribing";
          button.setAttribute("aria-label", "Transcribing");
        } else if (state === "error") {
          button.title = "Dictation unavailable";
          button.setAttribute("aria-label", "Dictation unavailable");
        } else {
          button.title = "Start dictation";
          button.setAttribute("aria-label", "Start dictation");
        }
      };

      button.addEventListener("click", () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          setState("error");
          showToast("Dictation unavailable");
          return;
        }
        if (state === "recording" && recognition) {
          setState("transcribing");
          recognition.stop();
          return;
        }
        recognition = new SpeechRecognition();
        recognition.interimResults = false;
        recognition.continuous = false;
        recognition.onstart = () => setState("recording");
        recognition.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map((result) => result[0]?.transcript || "")
            .join(" ")
            .trim();
          if (transcript) insertTextAtCursor(input, transcript);
        };
        recognition.onerror = () => {
          setState("error");
          showToast("Dictation unavailable");
        };
        recognition.onend = () => {
          recognition = null;
          if (state !== "error") setState("idle");
        };
        try {
          recognition.start();
        } catch (_error) {
          recognition = null;
          setState("error");
          showToast("Dictation unavailable");
        }
      });
    }

    function setupDictation() {
      setupDictationControl({ buttonId: "comment-dictation", inputId: "comment-text" });
    }

    function wireEvents() {
      $("prev").addEventListener("click", () => move(-1));
      $("next").addEventListener("click", () => move(1));
      $("overview").addEventListener("click", () => {
        $("overview-popover").hidden = !$("overview-popover").hidden;
        $("artifact-menu").hidden = true;
      });
      $("menu-button").addEventListener("click", () => {
        $("artifact-menu").hidden = !$("artifact-menu").hidden;
        $("overview-popover").hidden = true;
      });
      $("toggle-sidebar").addEventListener("click", () => {
        app.sidebarVisible = !app.sidebarVisible;
        renderShell();
      });
      $("copy-artifact").addEventListener("click", () => copyText(JSON.stringify(artifact(), null, 2)));
      $("copy-path").addEventListener("click", () => copyText(artifact().path));
      $("secondary-comment-action").addEventListener("click", secondaryEditorAction);
      $("primary-comment-action").addEventListener("click", commitEditor);
      $("zoom-in").addEventListener("click", () => applyZoom(app.zoomPercent + 10));
      $("zoom-out").addEventListener("click", () => applyZoom(app.zoomPercent - 10));
      $("zoom-input").addEventListener("change", () => applyZoom($("zoom-input").value.replace("%", "")));
      $("zoom-fit").addEventListener("click", smartFit);
      $("zoom-control").addEventListener("wheel", (event) => {
        event.preventDefault();
        applyZoom(app.zoomPercent + (event.deltaY < 0 ? 5 : -5));
      });
      $("markdown-preview-mode").addEventListener("click", () => setMarkdownMode("preview"));
      $("markdown-source-mode").addEventListener("click", () => setMarkdownMode("source"));
      $("markdown-save").addEventListener("click", saveMarkdownArtifact);
      $("markdown-revert").addEventListener("click", revertMarkdownArtifact);
      $("markdown-source").addEventListener("input", () => {
        const item = artifact();
        app.markdownContent[item.id] = $("markdown-source").value;
        app.markdownDirty[item.id] = app.markdownContent[item.id] !== app.markdownSavedContent[item.id];
        $("markdown-save").disabled = !app.markdownDirty[item.id];
        updateDimensionReadout();
      });
      $("markdown-source").addEventListener("keydown", (event) => {
        const key = String(event.key || "").toLowerCase();
        if ((event.metaKey || event.ctrlKey) && key === "s") {
          event.preventDefault();
          void saveMarkdownArtifact();
        }
        if (event.key !== "Tab") return;
        event.preventDefault();
        const input = $("markdown-source");
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const prefix = input.value.slice(0, start);
        const suffix = input.value.slice(end);
        input.value = `${prefix}  ${suffix}`;
        input.setSelectionRange(start + 2, start + 2);
        input.dispatchEvent(new Event("input"));
      });
      $("image-wrap").addEventListener("mousedown", startDrag);
      $("markdown-preview").addEventListener("mousedown", startDrag);
      $("artifact-image").addEventListener("dragstart", (event) => event.preventDefault());
      window.addEventListener("resize", () => {
        if (!isImageArtifact()) {
          updateMooringOverlays();
        } else if (app.zoomMode === "stage-fit") {
          applyZoom(stageFitZoom(), "stage-fit");
        } else {
          updateImageAlignment();
          updateMooringOverlays();
        }
      });
      $("stage").addEventListener("scroll", updateMooringOverlays);
      $("markdown-preview").addEventListener("scroll", updateMooringOverlays);
      $("markdown-source").addEventListener("scroll", updateMooringOverlays);
      $("stage").addEventListener("wheel", (event) => {
        if (!event.ctrlKey || !isImageArtifact()) return;
        event.preventDefault();
        applyZoom(app.zoomPercent + (event.deltaY < 0 ? 5 : -5));
      }, { passive: false });
      window.addEventListener("mousemove", moveDrag);
      window.addEventListener("mouseup", endDrag);
      document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") move(-1);
        if (event.key === "ArrowRight") move(1);
        if (event.key === "Escape") {
          $("overview-popover").hidden = true;
          $("artifact-menu").hidden = true;
          closeEditor();
          hideAnnotationMarker();
        }
      });
      document.addEventListener("click", (event) => {
        if (!event.target.closest(".popover") && !event.target.closest("#overview")) {
          $("overview-popover").hidden = true;
        }
        if (!event.target.closest(".menu") && !event.target.closest("#menu-button")) {
          $("artifact-menu").hidden = true;
        }
      });
      setupDictation();
    }

    async function boot() {
      const response = await fetch("/api/annotation-state");
      const payload = await response.json();
      app.collection = payload.collection;
      app.annotations = payload.annotations || {};
      if (!app.collection.artifacts.length) {
        $("stage").innerHTML = "<div class='small'>No artifacts found.</div>";
        return;
      }
      wireEvents();
      render();
    }

    boot().catch((error) => {
      $("stage").innerHTML = `<div class="small">Failed to load artifacts: ${escapeHtml(error.message)}</div>`;
    });
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a local artifact viewer for Playwright CLI public-page matrix outputs."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Aggregate matrix manifest to view",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the local artifact viewer in the system browser after the server starts",
    )
    return parser.parse_args()


def safe_manifest_path(path: Path) -> Path:
    manifest_path = path.resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if manifest_path.name != "manifest.json":
        raise SystemExit(f"Expected an aggregate manifest.json path: {manifest_path}")
    if REPO_ROOT not in manifest_path.parents:
        raise SystemExit(f"Manifest must be inside the repository: {manifest_path}")
    return manifest_path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_id(slug: str, key: str) -> str:
    return f"{slug}:{key}"


def artifact_created_at(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(path.stat().st_mtime)


def markdown_artifact_label(key: str) -> str:
    if key in MARKDOWN_ARTIFACT_KEYS:
        return MARKDOWN_ARTIFACT_KEYS[key]
    return key.replace("_", " ").replace("-", " ").title()


def is_markdown_artifact(key: str, path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return True
    mime = mimetypes.guess_type(str(path))[0]
    if mime == "text/markdown":
        return True
    normalized_key = key.lower().replace("-", "_")
    return normalized_key in MARKDOWN_ARTIFACT_KEYS and suffix in {".md", ".markdown", ".txt"}


def safe_artifact_path(relative_path: str, artifact_root: Path) -> Path | None:
    candidate = (REPO_ROOT / relative_path).resolve()
    root = artifact_root.resolve()
    if not candidate.exists() or REPO_ROOT not in candidate.parents:
        return None
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def build_collection(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("pages"), list):
        raise SystemExit(f"Invalid matrix manifest: {manifest_path}")

    artifact_root = manifest_path.parent
    artifacts: list[dict[str, Any]] = []
    for page in manifest["pages"]:
        slug = str(page.get("slug", "artifact"))
        page_artifacts = page.get("artifacts", {})
        dimensions = page.get("screenshot_dimensions", {})
        for key, label in IMAGE_ARTIFACT_KEYS.items():
            relative_path = page_artifacts.get(key)
            if not relative_path or safe_artifact_path(relative_path, artifact_root) is None:
                continue
            path = safe_artifact_path(relative_path, artifact_root)
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            artifacts.append(
                {
                    "id": artifact_id(slug, key),
                    "name": f"{slug} {label}",
                    "type": "image",
                    "kind": key,
                    "path": relative_path,
                    "mime_type": mime,
                    "capabilities": ["view", "annotate"],
                    "source_page": {
                        "slug": slug,
                        "url": page.get("url"),
                        "target_used": page.get("target_used"),
                    },
                    "dimensions": dimensions.get(key),
                    "created_at_epoch": artifact_created_at(path),
                }
            )
        for key, relative_path in page_artifacts.items():
            if key in IMAGE_ARTIFACT_KEYS or not relative_path:
                continue
            path = safe_artifact_path(relative_path, artifact_root)
            if path is None or not is_markdown_artifact(str(key), path):
                continue
            mime = mimetypes.guess_type(str(path))[0] or "text/markdown"
            artifacts.append(
                {
                    "id": artifact_id(slug, key),
                    "name": f"{slug} {markdown_artifact_label(str(key))}",
                    "type": "markdown",
                    "kind": str(key),
                    "path": relative_path,
                    "mime_type": mime,
                    "capabilities": ["view", "edit", "annotate"],
                    "source_page": {
                        "slug": slug,
                        "url": page.get("url"),
                        "target_used": page.get("target_used"),
                    },
                    "created_at_epoch": artifact_created_at(path),
                }
            )

    return {
        "id": f"artifact-collection:{manifest_path.relative_to(REPO_ROOT)}",
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "artifact_count": len(artifacts),
        "created_at_epoch": int(time.time()),
        "artifacts": artifacts,
    }


def clean_annotations(payload: Any, artifact_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return {}
    clean: dict[str, list[dict[str, Any]]] = {artifact_id_value: [] for artifact_id_value in artifact_ids}
    for item_id, annotations in payload.items():
        if item_id not in artifact_ids or not isinstance(annotations, list):
            continue
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            anchor = annotation.get("anchor")
            comment = str(annotation.get("comment", "")).strip()
            if not isinstance(anchor, dict) or not comment:
                continue
            clean_anchor = clean_annotation_anchor(anchor)
            if clean_anchor is None:
                continue
            try:
                clean[item_id].append(
                    {
                        "id": str(annotation.get("id") or f"{item_id}-{len(clean[item_id]) + 1}"),
                        "artifact_id": item_id,
                        "kind": str(annotation.get("kind") or "comment"),
                        "anchor": clean_anchor,
                        "comment": comment,
                        "created_at_epoch": int(annotation.get("created_at_epoch") or time.time()),
                        "updated_at_epoch": int(annotation["updated_at_epoch"])
                        if annotation.get("updated_at_epoch") is not None
                        else None,
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return clean


def clean_annotation_anchor(anchor: dict[str, Any]) -> dict[str, Any] | None:
    anchor_type = str(anchor.get("type") or "")
    if anchor_type == "image_region":
        rect = anchor.get("rect")
        if not isinstance(rect, dict):
            return None
        try:
            return {
                "type": "image_region",
                "coordinate_space": "natural_image",
                "rect": {
                    "x": int(rect["x"]),
                    "y": int(rect["y"]),
                    "width": int(rect["width"]),
                    "height": int(rect["height"]),
                },
            }
        except (KeyError, TypeError, ValueError):
            return None
    if anchor_type == "text_range":
        start = anchor.get("start")
        end = anchor.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None
        try:
            start_line = max(1, int(start["line"]))
            end_line = max(start_line, int(end["line"]))
            start_column = max(1, int(start.get("column", 1)))
            end_column = max(start_column if start_line == end_line else 1, int(end.get("column", 1)))
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "type": "text_range",
            "coordinate_space": "markdown_source",
            "start": {"line": start_line, "column": start_column},
            "end": {"line": end_line, "column": end_column},
            "excerpt": str(anchor.get("excerpt", ""))[:1000],
        }
    return None


class ReviewServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], manifest_path: Path):
        self.manifest_path = manifest_path
        self.artifact_root = manifest_path.parent
        self.collection = build_collection(manifest_path)
        self.artifacts_by_id = {item["id"]: item for item in self.collection["artifacts"]}
        self.annotations: dict[str, list[dict[str, Any]]] = {
            item["id"]: [] for item in self.collection["artifacts"]
        }
        self.updated_at_epoch = int(time.time())
        super().__init__(server_address, ReviewHandler)

    def annotation_state(self) -> dict[str, Any]:
        return {
            "status": "annotation_state",
            "collection": self.collection,
            "annotations": self.annotations,
            "updated_at_epoch": self.updated_at_epoch,
        }

    def replace_annotations(self, annotations: Any) -> None:
        artifact_ids = {item["id"] for item in self.collection["artifacts"]}
        self.annotations = clean_annotations(annotations, artifact_ids)
        self.updated_at_epoch = int(time.time())

    def artifact_path_by_id(self, artifact_id_value: str) -> Path | None:
        artifact = self.artifacts_by_id.get(artifact_id_value)
        if not artifact:
            return None
        return safe_artifact_path(str(artifact.get("path", "")), self.artifact_root)

    def write_markdown_artifact(self, artifact_id_value: str, content: str) -> dict[str, Any] | None:
        artifact = self.artifacts_by_id.get(artifact_id_value)
        if not artifact or artifact.get("type") != "markdown":
            return None
        path = self.artifact_path_by_id(artifact_id_value)
        if path is None:
            return None
        path.write_text(content, encoding="utf-8")
        artifact["created_at_epoch"] = artifact_created_at(path)
        artifact["size_bytes"] = path.stat().st_size
        return artifact


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format: str, *args: object) -> None:
        print("[artifact-viewer] " + format % args, file=sys.stderr)

    def send_text(self, status: HTTPStatus, content: str, content_type: str = "text/plain") -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", f"{content_type}; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status: HTTPStatus, value: Any) -> None:
        data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.send_text(HTTPStatus.OK, HTML, "text/html")
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path in {"/api/annotation-state", "/api/collection"}:
            self.send_json(HTTPStatus.OK, self.server.annotation_state())
            return
        if parsed.path.startswith("/artifact/"):
            self.serve_artifact(parsed.path.removeprefix("/artifact/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/annotation-state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("content-length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return
        self.server.replace_annotations(payload.get("annotations"))
        self.send_json(HTTPStatus.OK, self.server.annotation_state())

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/artifact-content/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        artifact_id_value = unquote(parsed.path.removeprefix("/api/artifact-content/"))
        length = int(self.headers.get("content-length", "0"))
        content = self.rfile.read(length).decode("utf-8")
        artifact = self.server.write_markdown_artifact(artifact_id_value, content)
        if artifact is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Markdown artifact not found"})
            return
        self.send_json(HTTPStatus.OK, {"status": "saved", "artifact": artifact})

    def serve_artifact(self, encoded_path: str) -> None:
        relative = Path(posixpath.normpath(unquote(encoded_path)))
        if relative.is_absolute() or ".." in relative.parts:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        artifact_path = safe_artifact_path(str(relative), self.server.artifact_root)
        if artifact_path is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(artifact_path.stat().st_size))
        self.end_headers()
        with artifact_path.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile)


def main() -> int:
    args = parse_args()
    manifest_path = safe_manifest_path(args.manifest)
    server = ReviewServer((args.host, args.port), manifest_path)
    host, port = server.server_address
    print(f"[artifact-viewer] serving {manifest_path}")
    print(f"[artifact-viewer] open http://{host}:{port}/")
    print(f"[artifact-viewer] annotation state http://{host}:{port}/api/annotation-state")
    if args.open:
        webbrowser.open(f"http://{host}:{port}/", new=2)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[artifact-viewer] stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
