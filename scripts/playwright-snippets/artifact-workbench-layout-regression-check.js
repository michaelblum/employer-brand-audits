async (page) => {
  await page.evaluate(() => window.localStorage.removeItem("eba.artifactWorkbench.artifactDocumentTheme"));
  await page.evaluate(() => window.localStorage.removeItem("eba.workflowArtifactWorkbench.artifactDocumentTheme"));
  await page.evaluate(() => window.localStorage.removeItem("eba.workflowArtifactWorkbench.markdownTheme"));
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const fullPageImageIndex = artifacts.findIndex((artifact) => (
      artifact.type === "image" && /full.page|full page/i.test(`${artifact.name || ""} ${artifact.path || ""}`)
    ));
    const imageIndex = fullPageImageIndex >= 0
      ? fullPageImageIndex
      : artifacts.findIndex((artifact) => artifact.type === "image");
    const htmlIndex = artifacts.findIndex((artifact) => artifact.type === "html");
    const documentIndex = artifacts.findIndex((artifact) => (
      ["json", "text", "log", "file"].includes(String(artifact.type || "").toLowerCase())
    ));
    const tableMarkdownIndex = artifacts.findIndex((artifact) => (
      artifact.type === "markdown" && /kilos|analysis/i.test(`${artifact.kind || ""} ${artifact.path || ""}`)
    ));
    const finalReportHtmlIndex = artifacts.findIndex((artifact) => (
      artifact.id === "l4-final-report" && artifact.type === "html"
    ));
    const markdownIndex = tableMarkdownIndex >= 0
      ? tableMarkdownIndex
      : artifacts.findIndex((artifact) => artifact.type === "markdown");
    if (imageIndex < 0) throw new Error("No image artifact in collection");
    if (markdownIndex < 0) throw new Error("No markdown artifact in collection");
    if (htmlIndex < 0) throw new Error("No html artifact in collection");
    if (documentIndex < 0) throw new Error("No document artifact in collection");
    return {
      imageIndex,
      markdownIndex,
      finalReportHtmlIndex,
      htmlIndex,
      documentIndex,
      expectsMarkdownTable: tableMarkdownIndex >= 0,
    };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((index) => {
    const row = document.querySelector(`.artifact-row[data-index="${index}"]`);
    if (!row) throw new Error(`Image artifact row not found: ${index}`);
    row.click();
  }, model.imageIndex);
  await page.waitForFunction(() => {
    const image = document.querySelector("#artifact-image");
    return image?.complete && image.naturalWidth > 0 && !document.querySelector("#image-wrap")?.hidden;
  }, null, { timeout: 5000 });
  await page.click("#zoom-fit", { timeout: 3000 });
  await page.waitForFunction(() => {
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    const wrap = document.querySelector("#image-wrap");
    if (!stage || !image || !image.complete || !image.naturalWidth) return false;
    return Boolean(wrap);
  }, null, { timeout: 3000 });
  const imageLayout = await page.evaluate(() => {
    const shell = document.querySelector("#shell");
    const sidebar = document.querySelector("#sidebar");
    const primaryToolbar = document.querySelector(".toolbar.primary");
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    const wrap = document.querySelector("#image-wrap");
    const shellRect = shell.getBoundingClientRect();
    const sidebarRect = sidebar.getBoundingClientRect();
    const toolbarRect = primaryToolbar.getBoundingClientRect();
    const shellStyle = getComputedStyle(shell);
    const toolbarStyle = getComputedStyle(primaryToolbar);
    const stageStyle = getComputedStyle(stage);
    const stagePadding = {
      top: parseFloat(stageStyle.paddingTop),
      right: parseFloat(stageStyle.paddingRight),
      bottom: parseFloat(stageStyle.paddingBottom),
      left: parseFloat(stageStyle.paddingLeft),
    };
    const stageWidth = stage.clientWidth - stagePadding.left - stagePadding.right;
    const stageHeight = stage.clientHeight - stagePadding.top - stagePadding.bottom;
    const stageRect = stage.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();
    const visibleCenterDelta = {
      x: Math.abs((imageRect.left + imageRect.width / 2) - (stageRect.left + stageRect.width / 2)),
      y: Math.abs((imageRect.top + imageRect.height / 2) - (stageRect.top + stageRect.height / 2)),
    };
    return {
      stageHasMarkdownClass: stage.classList.contains("markdown-stage"),
      centered: wrap.classList.contains("centered"),
      stageWidth,
      stageHeight,
      stageClientWidth: stage.clientWidth,
      stageClientHeight: stage.clientHeight,
      stageScrollWidth: stage.scrollWidth,
      stageScrollHeight: stage.scrollHeight,
      stageScrollLeft: stage.scrollLeft,
      stageScrollTop: stage.scrollTop,
      imageWidth: imageRect.width,
      imageHeight: imageRect.height,
      visibleCenterDelta,
      zoomValue: document.querySelector("#zoom-input")?.value,
      stagePadding,
      imageTopDelta: Math.abs(imageRect.top - stageRect.top),
      imageBottomDelta: Math.abs(imageRect.bottom - stageRect.bottom),
      imageFitsStage: imageRect.width <= stageRect.width + 1 && imageRect.height <= stageRect.height + 1,
      shellRight: shellRect.right,
      shellPosition: shellStyle.position,
      shellTop: shellRect.top,
      shellBottom: shellRect.bottom,
      sidebarRight: sidebarRect.right,
      toolbarRight: toolbarRect.right,
      toolbarPosition: toolbarStyle.position,
      viewportWidth: window.innerWidth,
      browserOuterWidth: window.outerWidth,
      browserWindowWidthDelta: Math.abs(window.outerWidth - window.innerWidth),
      viewportHeight: window.innerHeight,
      bodyScrollWidth: document.documentElement.scrollWidth,
    };
  });
  if (imageLayout.stageHasMarkdownClass) throw new Error("Image stage should not keep markdown-stage class");
  if (imageLayout.imageFitsStage) {
    if (!imageLayout.centered) throw new Error(`Fit image should use no-scroll centered alignment: ${JSON.stringify(imageLayout)}`);
    if (imageLayout.stageScrollWidth > imageLayout.stageClientWidth + 1 || imageLayout.stageScrollHeight > imageLayout.stageClientHeight + 1) {
      throw new Error(`Fit image should not require stage scrollbars: ${JSON.stringify(imageLayout)}`);
    }
    if (imageLayout.visibleCenterDelta.x > 2 || imageLayout.visibleCenterDelta.y > 2) {
      throw new Error(`Fit image should be centered in the stage: ${JSON.stringify(imageLayout)}`);
    }
  } else {
    if (imageLayout.centered) throw new Error(`Scrollable screenshot should not use no-scroll centered alignment: ${JSON.stringify(imageLayout)}`);
    if (Math.abs(imageLayout.imageWidth - imageLayout.stageWidth) > 2) {
      throw new Error(`Scrollable screenshot should fit the stage width: ${JSON.stringify(imageLayout)}`);
    }
    if (imageLayout.imageHeight <= imageLayout.stageHeight + 1 || imageLayout.stageScrollHeight <= imageLayout.stageClientHeight + 1) {
      throw new Error(`Scrollable screenshot should scroll vertically after width fit: ${JSON.stringify(imageLayout)}`);
    }
    if (imageLayout.visibleCenterDelta.x > 2) {
      throw new Error(`Scrollable screenshot should stay horizontally centered: ${JSON.stringify(imageLayout)}`);
    }
    if (imageLayout.imageTopDelta > 1) {
      throw new Error(`Scrollable screenshot should start at the top of the scrollable stage: ${JSON.stringify(imageLayout)}`);
    }
  }
  if (imageLayout.stagePadding.top || imageLayout.stagePadding.right || imageLayout.stagePadding.bottom || imageLayout.stagePadding.left) {
    throw new Error(`Stage should not own projection padding: ${JSON.stringify(imageLayout)}`);
  }
  if (Math.abs(imageLayout.shellRight - imageLayout.viewportWidth) > 1 || Math.abs(imageLayout.sidebarRight - imageLayout.viewportWidth) > 1) {
    throw new Error(`Shell/sidebar should fill to the viewport right edge: ${JSON.stringify(imageLayout)}`);
  }
  if (Math.abs(imageLayout.toolbarRight - imageLayout.viewportWidth) > 1) {
    throw new Error(`Primary toolbar should fill to the viewport right edge: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.browserWindowWidthDelta > 1) {
    throw new Error(`Workbench page viewport should match the visible browser window width: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.shellPosition !== "fixed" || imageLayout.toolbarPosition !== "fixed") {
    throw new Error(`Workbench chrome should be viewport-anchored, not document-flow sized: ${JSON.stringify(imageLayout)}`);
  }
  if (Math.abs(imageLayout.shellBottom - imageLayout.viewportHeight) > 1) {
    throw new Error(`Workbench shell should fill to the viewport bottom edge: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.bodyScrollWidth > imageLayout.viewportWidth + 1) {
    throw new Error(`Workbench shell should not create horizontal overflow: ${JSON.stringify(imageLayout)}`);
  }

  await page.fill("#zoom-input", "10%");
  await page.dispatchEvent("#zoom-input", "change");
  await page.waitForFunction(
    () => document.querySelector("#image-wrap")?.classList.contains("centered"),
    null,
    { timeout: 3000 },
  );
  const fitImageLayout = await page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    const wrap = document.querySelector("#image-wrap");
    const stageRect = stage.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();
    const emptySpace = {
      top: imageRect.top - stageRect.top,
      right: stageRect.right - imageRect.right,
      bottom: stageRect.bottom - imageRect.bottom,
      left: imageRect.left - stageRect.left,
    };
    return {
      centered: wrap.classList.contains("centered"),
      stageScrollWidth: stage.scrollWidth,
      stageScrollHeight: stage.scrollHeight,
      stageClientWidth: stage.clientWidth,
      stageClientHeight: stage.clientHeight,
      stageScrollLeft: stage.scrollLeft,
      stageScrollTop: stage.scrollTop,
      imageWidth: imageRect.width,
      imageHeight: imageRect.height,
      emptySpace,
      verticalEmptySpaceDelta: Math.abs(emptySpace.top - emptySpace.bottom),
      horizontalEmptySpaceDelta: Math.abs(emptySpace.left - emptySpace.right),
    };
  });
  if (!fitImageLayout.centered) {
    throw new Error(`Viewport fit image should use centered alignment: ${JSON.stringify(fitImageLayout)}`);
  }
  if (fitImageLayout.stageScrollWidth > fitImageLayout.stageClientWidth + 1 || fitImageLayout.stageScrollHeight > fitImageLayout.stageClientHeight + 1) {
    throw new Error(`Viewport fit image should not require stage scrollbars: ${JSON.stringify(fitImageLayout)}`);
  }
  if (fitImageLayout.verticalEmptySpaceDelta > 2 || fitImageLayout.horizontalEmptySpaceDelta > 2) {
    throw new Error(`Viewport fit image should have balanced stage empty space: ${JSON.stringify(fitImageLayout)}`);
  }

  await page.evaluate(() => {
    window.__ebaNestedDocumentScrollers = () => {
      const stage = document.querySelector("#stage");
      if (!stage) return [];
      return [...stage.querySelectorAll(".artifact-document, .artifact-document-scroll, .html-artifact-frame-wrap, .html-artifact-frame")]
        .filter((element) => {
          if (element.hidden || element.offsetParent === null) return false;
          const style = getComputedStyle(element);
          const verticalScrollable = /(auto|scroll)/.test(style.overflowY)
            && element.scrollHeight > element.clientHeight + 1;
          return verticalScrollable;
        })
        .map((element) => ({
          id: element.id,
          className: element.className,
          overflowY: getComputedStyle(element).overflowY,
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
        }));
    };
  });

  await page.evaluate((index) => {
    const row = document.querySelector(`.artifact-row[data-index="${index}"]`);
    if (!row) throw new Error(`Markdown artifact row not found: ${index}`);
    row.click();
  }, model.markdownIndex);
  await page.waitForFunction(() => {
    const stage = document.querySelector("#stage");
    const wrap = document.querySelector("#markdown-wrap");
    const preview = document.querySelector("#markdown-preview");
    return stage?.classList.contains("markdown-stage")
      && wrap
      && !wrap.hidden
      && preview
      && !preview.hidden
      && preview.querySelector("h1, h2, h3, p, li, pre, figure");
  }, null, { timeout: 5000 });
  const markdownLayout = await page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const wrap = document.querySelector("#markdown-wrap");
    const preview = document.querySelector("#markdown-preview");
    const body = document.querySelector("#markdown-preview-body");
    preview.scrollTop = preview.scrollHeight;
    const previewScrollTopAfterSet = preview.scrollTop;
    stage.scrollTop = stage.scrollHeight;
    const renderedBlocks = [...body.querySelectorAll("h1, h2, h3, p, li, pre, figure")];
    const lastBlock = renderedBlocks[renderedBlocks.length - 1];
    const stageRect = stage.getBoundingClientRect();
    const wrapRect = wrap.getBoundingClientRect();
    const lastRect = lastBlock.getBoundingClientRect();
    const stageStyle = getComputedStyle(stage);
    const documentStyle = getComputedStyle(wrap);
    const previewStyle = getComputedStyle(preview);
    const previewAfterStyle = getComputedStyle(preview, "::after");
    const bodyStyle = getComputedStyle(body);
    return {
      stageOverflow: stageStyle.overflow,
      stageOverflowY: stageStyle.overflowY,
      stageClientHeight: stage.clientHeight,
      stageScrollHeight: stage.scrollHeight,
      stageScrollTop: stage.scrollTop,
      wrapHeight: wrap.getBoundingClientRect().height,
      wrapTop: wrapRect.top,
      wrapBottom: wrapRect.bottom,
      stageTop: stageRect.top,
      stageBottom: stageRect.bottom,
      wrapOverflowY: documentStyle.overflowY,
      previewOverflowY: previewStyle.overflowY,
      documentMarginTop: documentStyle.marginTop,
      documentMarginRight: documentStyle.marginRight,
      documentMarginBottom: documentStyle.marginBottom,
      documentMarginLeft: documentStyle.marginLeft,
      previewPaddingTop: previewStyle.paddingTop,
      previewPaddingRight: previewStyle.paddingRight,
      previewPaddingBottom: previewStyle.paddingBottom,
      previewPaddingLeft: previewStyle.paddingLeft,
      previewAfterContent: previewAfterStyle.content,
      previewAfterHeight: previewAfterStyle.height,
      bodyPaddingTop: bodyStyle.paddingTop,
      bodyPaddingRight: bodyStyle.paddingRight,
      bodyPaddingBottom: bodyStyle.paddingBottom,
      bodyPaddingLeft: bodyStyle.paddingLeft,
      previewClientHeight: preview.clientHeight,
      previewScrollHeight: preview.scrollHeight,
      previewFontFamily: getComputedStyle(preview).fontFamily,
      tableCount: body.querySelectorAll("table").length,
      artifactDocumentClass: wrap.classList.contains("artifact-document"),
      artifactDocumentScrollClass: preview.classList.contains("artifact-document-scroll"),
      artifactDocumentBodyClass: body.classList.contains("artifact-document-body"),
      artifactProjectionClass: body.classList.contains("artifact-projection-markdown"),
      tableScrollBaseClass: Boolean(body.querySelector(".artifact-document-table-scroll")),
      previewScrollTopAfterSet,
      lastBlockText: lastBlock.textContent.trim().slice(0, 80),
      lastBlockBottom: lastRect.bottom,
      stageRelativeLastBottom: lastRect.bottom - stageRect.top,
      nestedDocumentScrollers: window.__ebaNestedDocumentScrollers(),
    };
  });
  if (!/(auto|scroll)/.test(markdownLayout.stageOverflowY)) {
    throw new Error(`Markdown stage should own document scrolling: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.previewOverflowY !== "visible" || markdownLayout.wrapOverflowY !== "visible") {
    throw new Error(`Markdown artifact should not create a nested vertical scroller: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.nestedDocumentScrollers.length) {
    throw new Error(`Markdown artifact has nested vertical scroll containers: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.previewScrollTopAfterSet !== 0) {
    throw new Error(`Markdown preview should not accept nested scrollTop changes: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.wrapHeight < markdownLayout.stageClientHeight - 1) {
    throw new Error(`Markdown artifact should fill at least the stage height: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.lastBlockBottom > markdownLayout.stageBottom + 1) {
    throw new Error(`Markdown stage bottom is clipped after stage scroll: ${JSON.stringify(markdownLayout)}`);
  }
  if (/Georgia|Times New Roman/i.test(markdownLayout.previewFontFamily)) {
    throw new Error(`Markdown preview should not use document-serif body text: ${JSON.stringify(markdownLayout)}`);
  }
  if (model.expectsMarkdownTable && markdownLayout.tableCount < 1) {
    throw new Error(`Markdown table was not rendered as a table: ${JSON.stringify(markdownLayout)}`);
  }
  if (!markdownLayout.artifactDocumentClass || !markdownLayout.artifactDocumentScrollClass || !markdownLayout.artifactDocumentBodyClass || !markdownLayout.artifactProjectionClass) {
    throw new Error(`Markdown projection should compose shared artifact-document base classes: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.documentMarginTop !== "0px" || markdownLayout.documentMarginRight !== "0px" || markdownLayout.documentMarginBottom !== "0px" || markdownLayout.documentMarginLeft !== "0px") {
    throw new Error(`Document wrapper should not own projection margin: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.previewPaddingTop !== "0px" || markdownLayout.previewPaddingRight !== "0px" || markdownLayout.previewPaddingBottom !== "0px" || markdownLayout.previewPaddingLeft !== "0px") {
    throw new Error(`Artifact scroll container should not own document padding: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.previewAfterContent !== "none" && markdownLayout.previewAfterHeight !== "0px") {
    throw new Error(`Artifact scroll container should not own generated document spacing: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.bodyPaddingTop === "0px" || markdownLayout.bodyPaddingLeft === "0px") {
    throw new Error(`Markdown body should own document content padding: ${JSON.stringify(markdownLayout)}`);
  }
  if (model.expectsMarkdownTable && !markdownLayout.tableScrollBaseClass) {
    throw new Error(`Markdown table scroll should use shared artifact-document table structure: ${JSON.stringify(markdownLayout)}`);
  }

  const artifactDocumentTheme = await page.evaluate(() => {
    const toggle = document.querySelector("#markdown-theme-toggle");
    const preview = document.querySelector("#markdown-preview");
    return {
      hasToggle: Boolean(toggle),
      ariaPressed: toggle?.getAttribute("aria-pressed"),
      title: toggle?.getAttribute("title"),
      background: preview ? getComputedStyle(preview).backgroundColor : null,
      color: preview ? getComputedStyle(preview).color : null,
      theme: document.body.dataset.artifactDocumentTheme || null,
      legacyTheme: document.body.dataset.markdownTheme || null,
    };
  });
  if (!artifactDocumentTheme.hasToggle) {
    throw new Error(`Markdown theme toggle is missing: ${JSON.stringify(artifactDocumentTheme)}`);
  }
  if (artifactDocumentTheme.theme !== "dark" || artifactDocumentTheme.ariaPressed !== "true") {
    throw new Error(`Artifact document should default to dark mode: ${JSON.stringify(artifactDocumentTheme)}`);
  }
  if (artifactDocumentTheme.legacyTheme) {
    throw new Error(`Artifact document theming should not use legacy markdown dataset hooks: ${JSON.stringify(artifactDocumentTheme)}`);
  }
  if (/rgb\(2(?:4[0-9]|5[0-5])[, ]+2(?:4[0-9]|5[0-5])[, ]+2(?:4[0-9]|5[0-5])\)/.test(artifactDocumentTheme.background || "")) {
    throw new Error(`Artifact document dark mode background should not be white: ${JSON.stringify(artifactDocumentTheme)}`);
  }
  await page.click("#markdown-theme-toggle", { timeout: 3000 });
  const lightArtifactDocumentTheme = await page.evaluate(() => {
    const preview = document.querySelector("#markdown-preview");
    return {
      ariaPressed: document.querySelector("#markdown-theme-toggle")?.getAttribute("aria-pressed"),
      background: preview ? getComputedStyle(preview).backgroundColor : null,
      theme: document.body.dataset.artifactDocumentTheme || null,
      legacyTheme: document.body.dataset.markdownTheme || null,
    };
  });
  if (lightArtifactDocumentTheme.theme !== "light" || lightArtifactDocumentTheme.ariaPressed !== "false") {
    throw new Error(`Artifact document theme toggle did not switch to light mode: ${JSON.stringify(lightArtifactDocumentTheme)}`);
  }
  if (lightArtifactDocumentTheme.legacyTheme) {
    throw new Error(`Artifact document light mode should not use legacy markdown dataset hooks: ${JSON.stringify(lightArtifactDocumentTheme)}`);
  }
  await page.click("#markdown-theme-toggle", { timeout: 3000 });
  const restoredArtifactDocumentTheme = await page.evaluate(() => ({
    ariaPressed: document.querySelector("#markdown-theme-toggle")?.getAttribute("aria-pressed"),
    theme: document.body.dataset.artifactDocumentTheme || null,
    legacyTheme: document.body.dataset.markdownTheme || null,
  }));
  if (restoredArtifactDocumentTheme.theme !== "dark" || restoredArtifactDocumentTheme.ariaPressed !== "true") {
    throw new Error(`Artifact document theme toggle did not restore dark mode: ${JSON.stringify(restoredArtifactDocumentTheme)}`);
  }
  if (restoredArtifactDocumentTheme.legacyTheme) {
    throw new Error(`Artifact document restored dark mode should not use legacy markdown dataset hooks: ${JSON.stringify(restoredArtifactDocumentTheme)}`);
  }

  const documentSurfaceLayout = async (index, label) => {
    await page.evaluate((targetIndex) => {
      const row = document.querySelector(`.artifact-row[data-index="${targetIndex}"]`);
      if (!row) throw new Error(`Artifact row not found: ${targetIndex}`);
      row.click();
    }, index);
    await page.waitForFunction(() => {
      const stage = document.querySelector("#stage");
      const wrap = document.querySelector("#markdown-wrap");
      const preview = document.querySelector("#markdown-preview");
      const body = document.querySelector("#markdown-preview-body");
      return stage?.classList.contains("markdown-stage")
        && wrap
        && !wrap.hidden
        && preview
        && !preview.hidden
        && body?.querySelector("[data-artifact-renderer]");
    }, null, { timeout: 5000 });
    const layout = await page.evaluate((surfaceLabel) => {
      const stage = document.querySelector("#stage");
      const wrap = document.querySelector("#markdown-wrap");
      const preview = document.querySelector("#markdown-preview");
      const frame = document.querySelector("[data-html-frame]");
      stage.scrollTop = 0;
      preview.scrollTop = preview.scrollHeight;
      const previewScrollTopAfterSet = preview.scrollTop;
      const stageRect = stage.getBoundingClientRect();
      const wrapRect = wrap.getBoundingClientRect();
      const frameDoc = frame?.contentDocument || null;
      const frameDocHeight = frameDoc
        ? Math.max(
          frameDoc.body?.scrollHeight || 0,
          frameDoc.documentElement?.scrollHeight || 0,
          frameDoc.body?.offsetHeight || 0,
          frameDoc.documentElement?.offsetHeight || 0,
        )
        : null;
      return {
        label: surfaceLabel,
        stageClientHeight: stage.clientHeight,
        stageScrollHeight: stage.scrollHeight,
        stageOverflowY: getComputedStyle(stage).overflowY,
        wrapHeight: wrapRect.height,
        wrapTopDelta: Math.abs(wrapRect.top - stageRect.top),
        wrapOverflowY: getComputedStyle(wrap).overflowY,
        previewOverflowY: getComputedStyle(preview).overflowY,
        previewScrollTopAfterSet,
        nestedDocumentScrollers: window.__ebaNestedDocumentScrollers(),
        frameHeight: frame?.clientHeight ?? null,
        frameDocHeight,
        frameScrolling: frame?.getAttribute("scrolling") || null,
      };
    }, label);
    if (!/(auto|scroll)/.test(layout.stageOverflowY)) {
      throw new Error(`${label} stage should own document scrolling: ${JSON.stringify(layout)}`);
    }
    if (layout.wrapHeight < layout.stageClientHeight - 1 || layout.wrapTopDelta > 1) {
      throw new Error(`${label} artifact should fill the visible stage height from the top: ${JSON.stringify(layout)}`);
    }
    if (layout.previewOverflowY !== "visible" || layout.wrapOverflowY !== "visible") {
      throw new Error(`${label} artifact should not create a nested vertical scroller: ${JSON.stringify(layout)}`);
    }
    if (layout.previewScrollTopAfterSet !== 0 || layout.nestedDocumentScrollers.length) {
      throw new Error(`${label} artifact has nested vertical scrolling: ${JSON.stringify(layout)}`);
    }
    if (layout.frameDocHeight !== null && layout.frameHeight + 2 < layout.frameDocHeight) {
      throw new Error(`${label} iframe should expand to content height: ${JSON.stringify(layout)}`);
    }
    return layout;
  };

  const finalReportLayout = await documentSurfaceLayout(
    model.finalReportHtmlIndex >= 0 ? model.finalReportHtmlIndex : model.htmlIndex,
    "Final report HTML",
  );
  const reportSurface = await page.evaluate(() => {
    const frame = document.querySelector("[data-html-frame]");
    const doc = frame?.contentDocument;
    return {
      surface: doc?.querySelector("[data-report-surface]")?.getAttribute("data-report-surface") || "",
      ledgerRows: doc?.querySelectorAll("#candidate-signal-ledger tbody tr").length || 0,
      scoreTiles: doc?.querySelectorAll("[data-kilos-score]").length || 0,
    };
  });
  if (
    reportSurface.surface !== "signal-brief"
    || reportSurface.ledgerRows < 3
    || reportSurface.scoreTiles < 5
  ) {
    throw new Error(`Final report HTML surface drifted: ${JSON.stringify(reportSurface)}`);
  }
  const htmlLayout = model.htmlIndex === model.finalReportHtmlIndex
    ? finalReportLayout
    : await documentSurfaceLayout(model.htmlIndex, "HTML");
  const documentLayout = await documentSurfaceLayout(model.documentIndex, "Document");

  return { imageLayout, fitImageLayout, markdownLayout, finalReportLayout, htmlLayout, documentLayout, reportSurface, artifactDocumentTheme, lightArtifactDocumentTheme, restoredArtifactDocumentTheme };
}
