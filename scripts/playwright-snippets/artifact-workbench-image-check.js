async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
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
    const imageControls = document.querySelector("#artifact-zoom-controls");
    const markdownControls = document.querySelector("#markdown-controls");
    const readout = document.querySelector("#artifact-readout")?.textContent || "";
    return image
      && image.complete
      && image.naturalWidth > 0
      && imageWrap
      && !imageWrap.hidden
      && markdownWrap
      && markdownWrap.hidden
      && !stage?.classList.contains("markdown-stage")
      && imageControls !== null
      && markdownControls === null
      && /\d+ x \d+ px/.test(readout);
  }, null, { timeout: 5000 });

  const measureImageLayout = () => page.evaluate(() => {
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    const wrap = document.querySelector("#image-wrap");
    const stageRect = stage?.getBoundingClientRect();
    const imageRect = image?.getBoundingClientRect();
    return {
      centered: wrap?.classList.contains("centered"),
      imageHeight: imageRect?.height,
      imageWidth: imageRect?.width,
      stageHeight: stageRect?.height,
      stageWidth: stageRect?.width,
      stageClientHeight: stage?.clientHeight,
      stageClientWidth: stage?.clientWidth,
      stageScrollHeight: stage?.scrollHeight,
      stageScrollLeft: stage?.scrollLeft,
      stageScrollTop: stage?.scrollTop,
      stageScrollWidth: stage?.scrollWidth,
      visibleCenterDelta: {
        x: Math.abs((imageRect.left + imageRect.width / 2) - (stageRect.left + stageRect.width / 2)),
        y: Math.abs((imageRect.top + imageRect.height / 2) - (stageRect.top + stageRect.height / 2)),
      },
      edgeSpace: {
        top: imageRect.top - stageRect.top,
        right: stageRect.right - imageRect.right,
        bottom: stageRect.bottom - imageRect.bottom,
        left: imageRect.left - stageRect.left,
      },
    };
  });

  const assertImageCentered = (layout, label) => {
    const imageFitsStage = layout.imageWidth <= layout.stageWidth + 1
      && layout.imageHeight <= layout.stageHeight + 1;
    const imageFitsStageWidth = layout.imageWidth <= layout.stageWidth + 1;
    if (imageFitsStage) {
      if (!layout.centered) throw new Error(`${label} should have centered alignment: ${JSON.stringify(layout)}`);
      if (layout.visibleCenterDelta.x > 2 || layout.visibleCenterDelta.y > 2) {
        throw new Error(`${label} should be visibly centered: ${JSON.stringify(layout)}`);
      }
      if (layout.stageScrollWidth > layout.stageClientWidth + 1 || layout.stageScrollHeight > layout.stageClientHeight + 1) {
        throw new Error(`${label} should not require stage scrollbars: ${JSON.stringify(layout)}`);
      }
    } else if (imageFitsStageWidth) {
      if (layout.visibleCenterDelta.x > 2) {
        throw new Error(`${label} should stay horizontally centered: ${JSON.stringify(layout)}`);
      }
      if (Math.abs(layout.edgeSpace.top) > 1) {
        throw new Error(`${label} should top-align in the scrollable stage: ${JSON.stringify(layout)}`);
      }
    } else if (layout.imageWidth > layout.stageWidth + 1) {
      const expectedScrollLeft = Math.max(0, (layout.stageScrollWidth - layout.stageClientWidth) / 2);
      if (Math.abs(layout.stageScrollLeft - expectedScrollLeft) > 2) {
        throw new Error(`${label} should center the horizontal overflow viewport: ${JSON.stringify({ ...layout, expectedScrollLeft })}`);
      }
      if (layout.visibleCenterDelta.x > 2) {
        throw new Error(`${label} should show the center of the overflowing image: ${JSON.stringify(layout)}`);
      }
    }
  };

  const imageLayout = await measureImageLayout();
  assertImageCentered(imageLayout, "Initial image");

  const beforeZoom = await page.evaluate(() => ({
    imageWidth: parseFloat(document.querySelector("#artifact-image")?.style.width || "0"),
    zoomInput: document.querySelector("#zoom-input")?.value || "",
  }));
  await page.click("#zoom-in");
  await page.waitForFunction((before) => {
    const imageWidth = parseFloat(document.querySelector("#artifact-image")?.style.width || "0");
    const zoomInput = document.querySelector("#zoom-input")?.value || "";
    return imageWidth > before.imageWidth && zoomInput !== before.zoomInput;
  }, beforeZoom, { timeout: 3000 });

  const zoomedLayout = await measureImageLayout();
  assertImageCentered(zoomedLayout, "Zoomed image");

  await page.fill("#zoom-input", "150%");
  await page.dispatchEvent("#zoom-input", "change");
  await page.waitForFunction(() => {
    const stage = document.querySelector("#stage");
    const image = document.querySelector("#artifact-image");
    if (!stage || !image) return false;
    return image.getBoundingClientRect().width > stage.getBoundingClientRect().width + 1;
  }, null, { timeout: 3000 });
  const overflowLayout = await measureImageLayout();
  assertImageCentered(overflowLayout, "Overflow zoom image");

  const finalState = await page.evaluate(() => {
    const image = document.querySelector("#artifact-image");
    const stage = document.querySelector("#stage");
    const imageControls = document.querySelector("#artifact-zoom-controls");
    const markdownControls = document.querySelector("#markdown-controls");
    const activeIcon = document.querySelector(".artifact-row.active .artifact-type-icon");
    return {
      activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      activeType: activeIcon?.getAttribute("title"),
      imageVisible: !document.querySelector("#image-wrap")?.hidden,
      documentHidden: document.querySelector("#markdown-wrap")?.hidden,
      stageHasMarkdownClass: stage?.classList.contains("markdown-stage"),
      imageControlsMounted: Boolean(imageControls),
      markdownControlsMounted: Boolean(markdownControls),
      imageNaturalWidth: image?.naturalWidth,
      imageNaturalHeight: image?.naturalHeight,
      imageRenderedWidth: image?.style.width,
      zoomInput: document.querySelector("#zoom-input")?.value,
      centered: document.querySelector("#image-wrap")?.classList.contains("centered"),
      readout: document.querySelector("#artifact-readout")?.textContent?.trim(),
    };
  });
  return {
    ...finalState,
    layout: {
      initial: imageLayout,
      zoomed: zoomedLayout,
      overflow: overflowLayout,
    },
  };
}
