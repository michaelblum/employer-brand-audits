async (page) => {
  await page.evaluate(() => window.localStorage.removeItem("eba.workflowArtifactWorkbench.artifactDocumentTheme"));
  await page.evaluate(() => window.localStorage.removeItem("eba.workflowArtifactWorkbench.markdownTheme"));
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const imageIndex = artifacts.findIndex((artifact) => (
      artifact.type === "image" && /full.page|full page/i.test(`${artifact.name || ""} ${artifact.path || ""}`)
    ));
    const fitImageIndex = artifacts.findIndex((artifact, index) => (
      artifact.type === "image" && index !== imageIndex && /viewport/i.test(`${artifact.name || ""} ${artifact.path || ""}`)
    ));
    const tableMarkdownIndex = artifacts.findIndex((artifact) => (
      artifact.type === "markdown" && /kilos|analysis/i.test(`${artifact.kind || ""} ${artifact.path || ""}`)
    ));
    const finalReportMarkdownIndex = artifacts.findIndex((artifact) => (
      artifact.type === "markdown"
        && /final employer brand audit/i.test(`${artifact.name || ""} ${artifact.summary || ""} ${artifact.path || ""}`)
    ));
    const markdownIndex = tableMarkdownIndex >= 0
      ? tableMarkdownIndex
      : artifacts.findIndex((artifact) => artifact.type === "markdown");
    if (imageIndex < 0) throw new Error("No image artifact in collection");
    if (fitImageIndex < 0) throw new Error("No viewport fit image artifact in collection");
    if (markdownIndex < 0) throw new Error("No markdown artifact in collection");
    return {
      imageIndex,
      fitImageIndex,
      markdownIndex,
      finalReportMarkdownIndex,
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
    const stageRect = stage.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();
    return !wrap?.classList.contains("centered")
      && Math.abs(imageRect.width - stageRect.width) <= 2
      && imageRect.height > stageRect.height + 1;
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
  if (imageLayout.centered) throw new Error(`Scrollable full-page screenshot should not use no-scroll centered alignment: ${JSON.stringify(imageLayout)}`);
  if (Math.abs(imageLayout.imageWidth - imageLayout.stageWidth) > 2) {
    throw new Error(`Full-page screenshot should fit the stage width: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.imageHeight <= imageLayout.stageHeight + 1 || imageLayout.stageScrollHeight <= imageLayout.stageClientHeight + 1) {
    throw new Error(`Full-page screenshot should scroll vertically after width fit: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.visibleCenterDelta.x > 2) {
    throw new Error(`Full-page screenshot should stay horizontally centered: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.stagePadding.top || imageLayout.stagePadding.right || imageLayout.stagePadding.bottom || imageLayout.stagePadding.left) {
    throw new Error(`Stage should not own projection padding: ${JSON.stringify(imageLayout)}`);
  }
  if (imageLayout.imageTopDelta > 1) {
    throw new Error(`Full-page screenshot should start at the top of the scrollable stage: ${JSON.stringify(imageLayout)}`);
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

  await page.evaluate((index) => {
    const row = document.querySelector(`.artifact-row[data-index="${index}"]`);
    if (!row) throw new Error(`Viewport fit image artifact row not found: ${index}`);
    row.click();
  }, model.fitImageIndex);
  await page.waitForFunction(() => {
    const image = document.querySelector("#artifact-image");
    return image?.complete && image.naturalWidth > 0 && !document.querySelector("#image-wrap")?.hidden;
  }, null, { timeout: 5000 });
  await page.click("#zoom-fit", { timeout: 3000 });
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
    const renderedBlocks = [...body.querySelectorAll("h1, h2, h3, p, li, pre, figure")];
    const lastBlock = renderedBlocks[renderedBlocks.length - 1];
    const previewRect = preview.getBoundingClientRect();
    const lastRect = lastBlock.getBoundingClientRect();
    const documentStyle = getComputedStyle(wrap);
    const previewStyle = getComputedStyle(preview);
    const previewAfterStyle = getComputedStyle(preview, "::after");
    const bodyStyle = getComputedStyle(body);
    return {
      stageOverflow: getComputedStyle(stage).overflow,
      wrapHeight: wrap.getBoundingClientRect().height,
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
      scrollTop: preview.scrollTop,
      lastBlockText: lastBlock.textContent.trim().slice(0, 80),
      lastBlockBottom: lastRect.bottom,
      previewBottom: previewRect.bottom,
    };
  });
  if (markdownLayout.stageOverflow !== "hidden") {
    throw new Error(`Markdown stage should hide outer scroll: ${JSON.stringify(markdownLayout)}`);
  }
  if (markdownLayout.lastBlockBottom > markdownLayout.previewBottom + 1) {
    throw new Error(`Markdown preview bottom is clipped: ${JSON.stringify(markdownLayout)}`);
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

  let finalReportLayout = null;
  if (model.finalReportMarkdownIndex >= 0) {
    await page.evaluate((index) => {
      const row = document.querySelector(`.artifact-row[data-index="${index}"]`);
      if (!row) throw new Error(`Final report markdown artifact row not found: ${index}`);
      row.click();
    }, model.finalReportMarkdownIndex);
    await page.waitForFunction(() => {
      const preview = document.querySelector("#markdown-preview");
      const title = document.querySelector("#artifact-title")?.textContent || "";
      return preview
        && !preview.hidden
        && /Final employer brand audit/i.test(title)
        && preview.querySelector("h1, h2, h3, p, li, pre, figure, table");
    }, null, { timeout: 5000 });
    finalReportLayout = await page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const wrap = document.querySelector("#markdown-wrap");
    const preview = document.querySelector("#markdown-preview");
    const body = document.querySelector("#markdown-preview-body");
    preview.scrollTop = preview.scrollHeight;
    const renderedBlocks = [...body.querySelectorAll("h1, h2, h3, p, li, pre, figure, table")];
    const lastBlock = renderedBlocks[renderedBlocks.length - 1];
    const recommendedHeading = [...body.querySelectorAll("h2")]
      .find((heading) => /Recommended Edits/i.test(heading.textContent || ""));
    const recommendedList = recommendedHeading?.nextElementSibling?.tagName === "OL"
      ? recommendedHeading.nextElementSibling
      : null;
    const stageRect = stage.getBoundingClientRect();
    const wrapRect = wrap.getBoundingClientRect();
    const previewRect = preview.getBoundingClientRect();
    const lastRect = lastBlock.getBoundingClientRect();
    const listRect = recommendedList?.getBoundingClientRect();
    const listStyle = recommendedList ? getComputedStyle(recommendedList) : null;
    const itemRects = [...(recommendedList?.querySelectorAll("li") || [])].map((item) => {
      const rect = item.getBoundingClientRect();
      const range = document.createRange();
      range.selectNodeContents(item);
      const textRect = range.getBoundingClientRect();
      range.detach();
      return {
        text: item.textContent.trim(),
        rect: rect.toJSON(),
        textRect: textRect.toJSON(),
      };
    });
    return {
      stageBottom: stageRect.bottom,
      wrapBottom: wrapRect.bottom,
      previewBottom: previewRect.bottom,
      previewRight: previewRect.right,
      lastBlockBottom: lastRect.bottom,
      lastBlockText: lastBlock.textContent.trim().slice(0, 80),
      lastBlockGapToPreviewBottom: previewRect.bottom - lastRect.bottom,
      recommendedListBottom: listRect?.bottom ?? null,
      recommendedListMarginBottom: listStyle?.marginBottom ?? null,
      recommendedListPaddingLeft: listStyle?.paddingLeft ?? null,
      recommendedItemRects: itemRects,
      scrollTop: preview.scrollTop,
      previewClientHeight: preview.clientHeight,
      previewScrollHeight: preview.scrollHeight,
    };
    });
    if (finalReportLayout.wrapBottom > finalReportLayout.stageBottom + 1) {
      throw new Error(`Final report markdown card extends below visible stage: ${JSON.stringify(finalReportLayout)}`);
    }
    if (finalReportLayout.lastBlockBottom > finalReportLayout.stageBottom + 1) {
      throw new Error(`Final report bottom remains clipped by the stage: ${JSON.stringify(finalReportLayout)}`);
    }
    if (finalReportLayout.lastBlockGapToPreviewBottom < 220) {
      throw new Error(`Final report markdown needs more end-of-document breathing room: ${JSON.stringify(finalReportLayout)}`);
    }
    if (!Number.isFinite(finalReportLayout.recommendedListBottom)) {
      throw new Error(`Final report recommended edits list was not rendered as an ordered list: ${JSON.stringify(finalReportLayout)}`);
    }
    if (finalReportLayout.recommendedListBottom > finalReportLayout.previewBottom - 48) {
      throw new Error(`Final report recommended edits list lacks bottom breathing room: ${JSON.stringify(finalReportLayout)}`);
    }
    for (const item of finalReportLayout.recommendedItemRects) {
      if (item.textRect.right > finalReportLayout.previewRight - 24) {
        throw new Error(`Final report recommended edits item text is horizontally clipped: ${JSON.stringify(finalReportLayout)}`);
      }
    }
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

  return { imageLayout, fitImageLayout, markdownLayout, finalReportLayout, artifactDocumentTheme, lightArtifactDocumentTheme, restoredArtifactDocumentTheme };
}
