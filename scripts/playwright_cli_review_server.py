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
    .fit-group {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .fit-button {
      height: 32px;
      padding: 0 10px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--muted);
      font-size: 12px;
    }
    .zoom-control {
      display: grid;
      grid-template-columns: 74px 24px;
      align-items: center;
      height: 38px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 9px;
      background: var(--panel);
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
    .image-wrap img {
      display: block;
      width: auto;
      max-width: none;
      height: auto;
      background: #000;
      box-shadow: 0 0 0 1px #27364d, 0 16px 40px rgba(0, 0, 0, 0.42);
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
    .comment-actions {
      display: flex;
      justify-content: space-between;
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
        <div class="image-controls">
          <div class="fit-group">
            <button class="fit-button" id="fit-width" type="button">Fit W</button>
            <button class="fit-button" id="fit-height" type="button">Fit H</button>
          </div>
          <div class="zoom-control" id="zoom-control">
            <input id="zoom-input" type="text" inputmode="numeric" aria-label="Zoom percentage">
            <div class="zoom-steps">
              <button id="zoom-in" type="button" aria-label="Zoom in">+</button>
              <button id="zoom-out" type="button" aria-label="Zoom out">-</button>
            </div>
          </div>
        </div>
      </div>
      <section class="stage" id="stage">
        <div class="image-wrap" id="image-wrap">
          <img id="artifact-image" alt="" draggable="false">
          <div class="selection" id="selection" hidden></div>
          <div class="hover-marker" id="hover-marker" hidden>💡</div>
        </div>
        <div class="comment-popover" id="comment-popover" hidden>
          <textarea id="comment-text" placeholder="Leave a comment"></textarea>
          <div class="comment-actions">
            <button class="icon-button" id="dictate" type="button" title="Dictate">🎙</button>
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
      pendingRect: null,
      editorMode: "create",
      editing: null,
      sidebarVisible: true,
      zoomPercent: 100,
      zoomMode: "fit-width",
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

    function clampZoom(value) {
      return Math.min(400, Math.max(10, Math.round(Number(value) || 100)));
    }

    function applyZoom(value, mode = "manual") {
      const image = $("artifact-image");
      app.zoomPercent = clampZoom(value);
      app.zoomMode = mode;
      $("zoom-input").value = `${app.zoomPercent}%`;
      if (image.naturalWidth) {
        image.style.width = `${Math.max(1, Math.round(image.naturalWidth * app.zoomPercent / 100))}px`;
      }
      if (app.editing) {
        placeSelectionForRect(app.editing.rect);
        placePopoverForRect(app.editing.rect);
      }
    }

    function fitWidth() {
      const image = $("artifact-image");
      const stage = $("stage");
      if (!image.naturalWidth) return;
      applyZoom(((stage.clientWidth - 64) / image.naturalWidth) * 100, "fit-width");
    }

    function fitHeight() {
      const image = $("artifact-image");
      const stage = $("stage");
      if (!image.naturalHeight) return;
      applyZoom(((stage.clientHeight - 64) / image.naturalHeight) * 100, "fit-height");
    }

    function updateDimensionReadout() {
      const item = artifact();
      const dimensions = item.dimensions || {};
      const width = dimensions.width || $("artifact-image").naturalWidth || "unknown";
      const height = dimensions.height || $("artifact-image").naturalHeight || "unknown";
      $("dimension-readout").textContent = `${width} x ${height} px`;
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
      $("selection").hidden = true;
      $("hover-marker").hidden = true;
      $("comment-popover").hidden = true;
      updateDimensionReadout();
      image.onload = () => {
        updateDimensionReadout();
        if (app.zoomMode === "fit-height") {
          fitHeight();
        } else if (app.zoomMode === "fit-width") {
          fitWidth();
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

    function renderOverview() {
      $("overview-popover").innerHTML = app.collection.artifacts.map((item, index) => `
        <button class="artifact-option ${index === app.index ? "active" : ""}" type="button" data-index="${index}">
          <span>${escapeHtml(item.name)}</span>
          <span class="small">${escapeHtml(item.path)}</span>
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
            </div>
          `).join("")
          : "";
        return `
          <div class="artifact-row ${index === app.index ? "active" : ""}" data-index="${index}">
            <div class="row-title">
              <div class="name">${escapeHtml(item.name)}</div>
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
      renderImage();
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

    function placeSelectionForRect(rect) {
      placeSelection(displayRectFromNatural(rect));
    }

    function placePopoverForRect(rect) {
      openComment(displayRectFromNatural(rect));
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

    function hideAnnotationMarker() {
      $("hover-marker").hidden = true;
    }

    function showAnnotationMarker(artifactId, annotationId) {
      const note = annotationById(artifactId, annotationId);
      if (!note) return;
      const index = artifactIndexById(artifactId);
      if (index !== app.index) {
        setArtifact(index);
        window.requestAnimationFrame(() => placeMarkerForRect(note.rect));
        return;
      }
      placeMarkerForRect(note.rect);
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

    function openComment(displayRect) {
      const popover = $("comment-popover");
      const imageRect = $("artifact-image").getBoundingClientRect();
      const left = Math.min(imageRect.left + displayRect.x + displayRect.width + 10, window.innerWidth - 434);
      const top = Math.min(imageRect.top + displayRect.y, window.innerHeight - 190);
      popover.style.left = `${Math.max(14, left)}px`;
      popover.style.top = `${Math.max(14, top)}px`;
      popover.hidden = false;
      $("comment-text").focus();
    }

    function openCreateEditor(displayRect) {
      app.editorMode = "create";
      app.editing = null;
      $("comment-text").value = "";
      $("secondary-comment-action").textContent = "Cancel";
      $("primary-comment-action").textContent = "Add Comment";
      openComment(displayRect);
    }

    function openExistingEditor(note) {
      app.editorMode = "edit";
      app.editing = note;
      $("comment-text").value = note.comment;
      $("secondary-comment-action").textContent = "Delete";
      $("primary-comment-action").textContent = "Update";
      placeSelectionForRect(note.rect);
      placePopoverForRect(note.rect);
    }

    function closeEditor() {
      app.pendingRect = null;
      app.editing = null;
      app.editorMode = "create";
      $("comment-popover").hidden = true;
      $("selection").hidden = true;
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
      if (event.button !== 0 || !event.target.closest("#image-wrap")) return;
      const point = imagePoint(event);
      app.drag = { startX: point.x, startY: point.y };
      app.pendingRect = null;
      $("comment-popover").hidden = true;
      placeSelection({ x: point.x, y: point.y, width: 0, height: 0 });
    }

    function moveDrag(event) {
      if (!app.drag) return;
      const point = imagePoint(event);
      const displayRect = {
        x: Math.min(app.drag.startX, point.x),
        y: Math.min(app.drag.startY, point.y),
        width: Math.abs(point.x - app.drag.startX),
        height: Math.abs(point.y - app.drag.startY),
      };
      placeSelection(displayRect);
    }

    function endDrag(event) {
      if (!app.drag) return;
      const point = imagePoint(event);
      const displayRect = {
        x: Math.min(app.drag.startX, point.x),
        y: Math.min(app.drag.startY, point.y),
        width: Math.abs(point.x - app.drag.startX),
        height: Math.abs(point.y - app.drag.startY),
      };
      app.drag = null;
      if (displayRect.width < 8 || displayRect.height < 8) {
        $("selection").hidden = true;
        return;
      }
      app.pendingRect = naturalRect(displayRect);
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
      if (!app.pendingRect) return;
      const item = artifact();
      const note = {
        id: `${item.id}-${Date.now().toString(36)}`,
        artifact_id: item.id,
        rect: app.pendingRect,
        comment,
        created_at_epoch: Math.floor(Date.now() / 1000),
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

    function setupDictation() {
      $("dictate").addEventListener("click", () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          showToast("Dictation unavailable");
          return;
        }
        const recognition = new SpeechRecognition();
        recognition.onresult = (event) => {
          $("comment-text").value = `${$("comment-text").value} ${event.results[0][0].transcript}`.trim();
        };
        recognition.start();
      });
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
      $("zoom-control").addEventListener("wheel", (event) => {
        event.preventDefault();
        applyZoom(app.zoomPercent + (event.deltaY < 0 ? 5 : -5));
      });
      $("fit-width").addEventListener("click", fitWidth);
      $("fit-height").addEventListener("click", fitHeight);
      $("image-wrap").addEventListener("mousedown", startDrag);
      $("artifact-image").addEventListener("dragstart", (event) => event.preventDefault());
      window.addEventListener("resize", () => {
        if (app.zoomMode === "fit-width") fitWidth();
        if (app.zoomMode === "fit-height") fitHeight();
      });
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
        $("stage").innerHTML = "<div class='small'>No image artifacts found.</div>";
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
                    "kind": key,
                    "path": relative_path,
                    "mime_type": mime,
                    "source_page": {
                        "slug": slug,
                        "url": page.get("url"),
                        "target_used": page.get("target_used"),
                    },
                    "dimensions": dimensions.get(key),
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
            rect = annotation.get("rect")
            comment = str(annotation.get("comment", "")).strip()
            if not isinstance(rect, dict) or not comment:
                continue
            try:
                clean[item_id].append(
                    {
                        "id": str(annotation.get("id") or f"{item_id}-{len(clean[item_id]) + 1}"),
                        "artifact_id": item_id,
                        "rect": {
                            "x": int(rect["x"]),
                            "y": int(rect["y"]),
                            "width": int(rect["width"]),
                            "height": int(rect["height"]),
                        },
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


class ReviewServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], manifest_path: Path):
        self.manifest_path = manifest_path
        self.artifact_root = manifest_path.parent
        self.collection = build_collection(manifest_path)
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
