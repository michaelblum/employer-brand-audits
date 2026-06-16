async (page) => {
  await page.reload();
  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });

  await page.evaluate(() => {
    const rows = [...document.querySelectorAll(".artifact-row[data-index]")];
    const markdownRow = rows.find((row) => {
      const icon = row.querySelector(".artifact-type-icon");
      const title = row.querySelector(".name")?.textContent || "";
      return icon?.getAttribute("title") === "markdown" && /Final employer brand audit/.test(title);
    });
    if (!markdownRow) {
      throw new Error("No final report markdown artifact row found");
    }
    markdownRow.click();
  });

  await page.waitForFunction(() => {
    const markdownWrap = document.querySelector("#markdown-wrap");
    const imageWrap = document.querySelector("#image-wrap");
    const preview = document.querySelector("#markdown-preview");
    const readout = document.querySelector("#artifact-readout")?.textContent || "";
    return markdownWrap
      && imageWrap
      && !markdownWrap.hidden
      && imageWrap.hidden
      && document.querySelector("#image-controls") === null
      && document.querySelector("#markdown-controls") !== null
      && /lines/.test(readout)
      && /Acme Robotics Employer Brand Audit/.test(preview?.textContent || "")
      && document.querySelector(".artifact-row.active .artifact-type-icon use")?.getAttribute("href")?.includes("artifact-workbench-icons.svg");
  }, null, { timeout: 3000 });

  return await page.evaluate(() => {
    const markdownIcon = document.querySelector(".artifact-row.active .artifact-type-icon");
    const markdownIconUse = markdownIcon?.querySelector("use");
    const previewButton = document.querySelector("#markdown-preview-mode");
    const editButton = document.querySelector("#markdown-source-mode");
    const revertButton = document.querySelector("#markdown-revert");
    const saveButton = document.querySelector("#markdown-save");
    const imageControls = document.querySelector("#image-controls");
    return {
      activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      activeType: markdownIcon?.getAttribute("title"),
      activeIconHref: markdownIconUse?.getAttribute("href"),
      imageHidden: document.querySelector("#image-wrap")?.hidden,
      markdownVisible: !document.querySelector("#markdown-wrap")?.hidden,
      previewTooltip: previewButton?.getAttribute("title"),
      editTooltip: editButton?.getAttribute("title"),
      revertTooltip: revertButton?.getAttribute("title"),
      saveTooltip: saveButton?.getAttribute("title"),
      previewIconHref: previewButton?.querySelector("use")?.getAttribute("href"),
      revertIconHref: revertButton?.querySelector("use")?.getAttribute("href"),
      saveIconHref: saveButton?.querySelector("use")?.getAttribute("href"),
      previewButtonText: previewButton?.textContent?.trim(),
      editButtonText: editButton?.textContent?.trim(),
      revertButtonText: revertButton?.textContent?.trim(),
      saveButtonText: saveButton?.textContent?.trim(),
      imageControlsMounted: Boolean(imageControls),
      readout: document.querySelector("#artifact-readout")?.textContent?.trim(),
      markdownHeading: document.querySelector("#markdown-preview h1")?.textContent?.trim(),
    };
  });
}
