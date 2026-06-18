async (page) => {
  await page.reload();
  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });

  const model = await page.evaluate(async () => {
    const [state, projection] = await Promise.all([
      fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const report = (projection.artifacts || []).find((artifact) => artifact.id === "l4-final-report");
    if (!report) throw new Error("Missing projected l4-final-report artifact");
    if (report.type !== "html") throw new Error(`l4-final-report should project as html: ${JSON.stringify(report)}`);
    if (report.kind !== "report") throw new Error(`l4-final-report should preserve report kind: ${JSON.stringify(report)}`);
    if ((report.capabilities || []).includes("edit") || (report.capabilities || []).includes("render")) {
      throw new Error(`HTML report should not expose edit/render controls: ${JSON.stringify(report)}`);
    }
    const duplicate = (projection.artifacts || []).find((artifact) => artifact.id === "l4-final-report-html");
    if (duplicate) throw new Error(`L4 report HTML should not be duplicated: ${JSON.stringify(duplicate)}`);
    const artifactIndex = (state.collection?.artifacts || []).findIndex((artifact) => artifact.id === report.id);
    if (artifactIndex < 0) throw new Error("l4-final-report is not present in the workbench collection");
    return { artifactIndex, report };
  });

  await page.evaluate((artifactIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
    if (!row) throw new Error(`Report artifact row not rendered: ${artifactIndex}`);
    row.click();
  }, model.artifactIndex);

  await page.waitForFunction(() => {
    const frame = document.querySelector("[data-html-frame]");
    const doc = frame?.contentDocument;
    return frame
      && doc?.querySelector('[data-report-surface="signal-brief"]')
      && doc.querySelector("#candidate-signal-ledger")
      && /Acme Robotics/.test(doc.body?.textContent || "")
      && document.querySelector("#artifact-zoom-controls") === null
      && document.querySelector("#markdown-controls") === null;
  }, null, { timeout: 5000 });

  return await page.evaluate(() => {
    const frame = document.querySelector("[data-html-frame]");
    const doc = frame?.contentDocument;
    const reportSurface = doc?.querySelector('[data-report-surface="signal-brief"]');
    const scoreTiles = [...(doc?.querySelectorAll("[data-kilos-score]") || [])];
    const ledgerRows = [...(doc?.querySelectorAll("#candidate-signal-ledger tbody tr") || [])];
    const activeIcon = document.querySelector(".artifact-row.active .artifact-type-icon");
    return {
      activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      activeType: activeIcon?.getAttribute("title"),
      activeIconHref: activeIcon?.querySelector("use")?.getAttribute("href"),
      rendererType: document.querySelector("[data-artifact-renderer]")?.getAttribute("data-artifact-renderer"),
      reportSurface: reportSurface?.getAttribute("data-report-surface"),
      headline: doc?.querySelector("h1")?.textContent?.trim(),
      kilosScoreCount: scoreTiles.length,
      ledgerRowCount: ledgerRows.length,
      readout: document.querySelector("#artifact-readout")?.textContent?.trim(),
      zoomControlsMounted: Boolean(document.querySelector("#artifact-zoom-controls")),
      markdownControlsMounted: Boolean(document.querySelector("#markdown-controls")),
    };
  });
}
