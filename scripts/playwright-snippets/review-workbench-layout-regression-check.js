async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const imageIndex = artifacts.findIndex((artifact) => artifact.type === "image");
    const markdownIndex = artifacts.findIndex((artifact) => artifact.type === "markdown" && artifact.kind === "report");
    if (imageIndex < 0) throw new Error("No image artifact in collection");
    if (markdownIndex < 0) throw new Error("No report markdown artifact in collection");
    return { imageIndex, markdownIndex };
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
  }, { timeout: 5000 });
  await page.click("#zoom-fit");
  await page.waitForFunction(() => document.querySelector("#image-wrap")?.classList.contains("centered"), { timeout: 3000 });
  const imageLayout = await page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    const wrap = document.querySelector("#image-wrap");
    const stageStyle = getComputedStyle(stage);
    const stageWidth = stage.clientWidth - parseFloat(stageStyle.paddingLeft) - parseFloat(stageStyle.paddingRight);
    const stageHeight = stage.clientHeight - parseFloat(stageStyle.paddingTop) - parseFloat(stageStyle.paddingBottom);
    const imageRect = image.getBoundingClientRect();
    return {
      stageHasMarkdownClass: stage.classList.contains("markdown-stage"),
      centered: wrap.classList.contains("centered"),
      stageWidth,
      stageHeight,
      imageWidth: imageRect.width,
      imageHeight: imageRect.height,
      zoomValue: document.querySelector("#zoom-input")?.value,
    };
  });
  if (imageLayout.stageHasMarkdownClass) throw new Error("Image stage should not keep markdown-stage class");
  if (!imageLayout.centered) throw new Error("Stage-fit image should stay centered");
  if (imageLayout.imageWidth > imageLayout.stageWidth + 1 || imageLayout.imageHeight > imageLayout.stageHeight + 1) {
    throw new Error(`Stage-fit image exceeds stage: ${JSON.stringify(imageLayout)}`);
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
  }, { timeout: 5000 });
  const markdownLayout = await page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const wrap = document.querySelector("#markdown-wrap");
    const preview = document.querySelector("#markdown-preview");
    preview.scrollTop = preview.scrollHeight;
    const renderedBlocks = [...preview.querySelectorAll("h1, h2, h3, p, li, pre, figure")];
    const lastBlock = renderedBlocks[renderedBlocks.length - 1];
    const previewRect = preview.getBoundingClientRect();
    const lastRect = lastBlock.getBoundingClientRect();
    return {
      stageOverflow: getComputedStyle(stage).overflow,
      wrapHeight: wrap.getBoundingClientRect().height,
      previewClientHeight: preview.clientHeight,
      previewScrollHeight: preview.scrollHeight,
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

  return { imageLayout, markdownLayout };
}
