async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const imageIndex = artifacts.findIndex((artifact) => artifact.type === "image");
    if (imageIndex < 0) throw new Error("No image artifact in collection");
    return { imageIndex };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((imageIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${imageIndex}"]`);
    if (!row) throw new Error(`Image artifact row not rendered: ${imageIndex}`);
    row.click();
  }, model.imageIndex);

  await page.waitForFunction(() => {
    const image = document.querySelector("#artifact-image");
    const stage = document.querySelector("#stage");
    const imageWrap = document.querySelector("#image-wrap");
    const markdownWrap = document.querySelector("#markdown-wrap");
    const imageControls = document.querySelector("#image-controls");
    const markdownControls = document.querySelector("#markdown-controls");
    const readout = document.querySelector("#dimension-readout")?.textContent || "";
    return image
      && image.complete
      && image.naturalWidth > 0
      && imageWrap
      && !imageWrap.hidden
      && markdownWrap
      && markdownWrap.hidden
      && !stage?.classList.contains("markdown-stage")
      && getComputedStyle(imageControls).display === "flex"
      && !markdownControls?.classList.contains("visible")
      && /\d+ x \d+ px/.test(readout);
  }, null, { timeout: 5000 });

  return await page.evaluate(() => {
    const image = document.querySelector("#artifact-image");
    const stage = document.querySelector("#stage");
    const imageControls = document.querySelector("#image-controls");
    const markdownControls = document.querySelector("#markdown-controls");
    const activeIcon = document.querySelector(".artifact-row.active .artifact-type-icon");
    return {
      activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      activeType: activeIcon?.getAttribute("title"),
      imageVisible: !document.querySelector("#image-wrap")?.hidden,
      documentHidden: document.querySelector("#markdown-wrap")?.hidden,
      stageHasMarkdownClass: stage?.classList.contains("markdown-stage"),
      imageControlsDisplay: getComputedStyle(imageControls).display,
      markdownControlsVisible: markdownControls?.classList.contains("visible"),
      imageNaturalWidth: image?.naturalWidth,
      imageNaturalHeight: image?.naturalHeight,
      readout: document.querySelector("#dimension-readout")?.textContent?.trim(),
    };
  });
}
