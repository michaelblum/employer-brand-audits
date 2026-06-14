async (page) => {
  await page.evaluate(() => {
    const rows = [...document.querySelectorAll(".artifact-row[data-index]")];
    const jsonRow = rows.find((row) => row.querySelector(".artifact-type-icon")?.getAttribute("title") === "json");
    if (!jsonRow) {
      throw new Error("No JSON artifact row found");
    }
    jsonRow.click();
  });

  await page.waitForFunction(() => {
    const markdownWrap = document.querySelector("#markdown-wrap");
    const imageWrap = document.querySelector("#image-wrap");
    const source = document.querySelector("[data-document-source]");
    const renderer = document.querySelector("[data-artifact-renderer='document']");
    return markdownWrap
      && imageWrap
      && !markdownWrap.hidden
      && imageWrap.hidden
      && renderer
      && source
      && /acme\.example|knowledge|identity|logistics/.test(source.textContent || "");
  }, { timeout: 3000 });

  return await page.evaluate(() => {
    const activeIcon = document.querySelector(".artifact-row.active .artifact-type-icon");
    const documentNode = document.querySelector("[data-artifact-renderer='document']");
    const source = document.querySelector("[data-document-source]");
    return {
      activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      activeType: activeIcon?.getAttribute("title"),
      imageHidden: document.querySelector("#image-wrap")?.hidden,
      documentVisible: !document.querySelector("#markdown-wrap")?.hidden,
      rendererType: documentNode?.getAttribute("data-document-type"),
      hasSource: Boolean(source),
      readout: document.querySelector("#dimension-readout")?.textContent?.trim(),
    };
  });
}
