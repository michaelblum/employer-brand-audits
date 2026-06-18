async (page) => {
  const runtimeErrors = [];
  const onConsole = (message) => {
    if (message.type() === "error") {
      runtimeErrors.push(`console:${message.text()}`);
    }
  };
  const onPageError = (error) => {
    runtimeErrors.push(`pageerror:${error.message}`);
  };
  page.on("console", onConsole);
  page.on("pageerror", onPageError);

  try {
    await page.reload({ waitUntil: "load", timeout: 8000 });
    await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
    await page.waitForFunction(() => Boolean(window.WorkbenchArtifactBinding), null, { timeout: 3000 });

    const bootState = await page.evaluate(async () => {
      const [assetHealth, state] = await Promise.all([
        fetch("/api/workbench-assets", { cache: "no-store" }).then((response) => response.json()),
        fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
      ]);
      const artifacts = state.collection?.artifacts || [];
      return {
        assetCount: assetHealth.asset_count,
        assetHealthy: assetHealth.status === "workbench_assets" && assetHealth.assets?.every((asset) => asset.exists),
        artifactCount: artifacts.length,
        imageIndex: artifacts.findIndex((artifact) => artifact.type === "image"),
        markdownIndex: artifacts.findIndex((artifact) => artifact.type === "markdown"),
        htmlIndex: artifacts.findIndex((artifact) => artifact.id === "l4-final-report" && artifact.type === "html"),
        documentIndex: artifacts.findIndex((artifact) => ["json", "text", "log", "file"].includes(artifact.type)),
      };
    });

    if (!bootState.assetHealthy) throw new Error("Workbench asset health is not healthy");
    if (bootState.artifactCount <= 0) throw new Error("Workbench booted without artifacts");
    if (bootState.imageIndex < 0) throw new Error("No image artifact found for live smoke");
    if (bootState.markdownIndex < 0) throw new Error("No markdown artifact found for live smoke");
    if (bootState.htmlIndex < 0) throw new Error("No HTML L4 report artifact found for live smoke");
    if (bootState.documentIndex < 0) throw new Error("No document artifact found for live smoke");

    async function selectArtifact(index) {
      await page.evaluate((artifactIndex) => {
        const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
        if (!row) throw new Error(`Artifact row not rendered: ${artifactIndex}`);
        row.click();
      }, index);
    }

    await selectArtifact(bootState.imageIndex);
    await page.waitForFunction(() => {
      const image = document.querySelector("#artifact-image");
      const readout = document.querySelector("#artifact-readout")?.textContent || "";
      return image
        && image.complete
        && image.naturalWidth > 0
        && !document.querySelector("#image-wrap")?.hidden
        && document.querySelector("#markdown-wrap")?.hidden
        && document.querySelector("#artifact-zoom-controls") !== null
        && document.querySelector("#markdown-controls") === null
        && /\d+ x \d+ px/.test(readout);
    }, null, { timeout: 5000 });

    await selectArtifact(bootState.markdownIndex);
    await page.waitForFunction(() => {
      const readout = document.querySelector("#artifact-readout")?.textContent || "";
      return document.querySelector("#image-wrap")?.hidden
        && !document.querySelector("#markdown-wrap")?.hidden
        && document.querySelector("#artifact-zoom-controls") === null
        && document.querySelector("#markdown-controls") === null
        && /lines/.test(readout);
    }, null, { timeout: 5000 });

    await selectArtifact(bootState.htmlIndex);
    await page.waitForFunction(() => {
      const readout = document.querySelector("#artifact-readout")?.textContent || "";
      const frame = document.querySelector("[data-html-frame]");
      return document.querySelector("#image-wrap")?.hidden
        && !document.querySelector("#markdown-wrap")?.hidden
        && document.querySelector("[data-artifact-renderer='html']") !== null
        && document.querySelector("#artifact-zoom-controls") === null
        && document.querySelector("#markdown-controls") === null
        && frame?.contentDocument?.querySelector('[data-report-surface="signal-brief"]')
        && /elements|bytes/.test(readout);
    }, null, { timeout: 5000 });

    await selectArtifact(bootState.documentIndex);
    await page.waitForFunction(() => {
      const readout = document.querySelector("#artifact-readout")?.textContent || "";
      return document.querySelector("#image-wrap")?.hidden
        && !document.querySelector("#markdown-wrap")?.hidden
        && document.querySelector("[data-artifact-renderer='document']") !== null
        && document.querySelector("#artifact-zoom-controls") === null
        && document.querySelector("#markdown-controls") === null
        && /lines|bytes/.test(readout);
    }, null, { timeout: 5000 });

    if (runtimeErrors.length) {
      throw new Error(`Workbench runtime errors: ${runtimeErrors.join(" | ")}`);
    }

    return await page.evaluate((boot) => ({
      activeReadout: document.querySelector("#artifact-readout")?.textContent?.trim(),
      activeTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      assetCount: boot.assetCount,
      artifactCount: boot.artifactCount,
      hasBinding: Boolean(window.WorkbenchArtifactBinding),
      zoomControlsMounted: Boolean(document.querySelector("#artifact-zoom-controls")),
      markdownControlsMounted: Boolean(document.querySelector("#markdown-controls")),
      rendererType: document.querySelector("[data-artifact-renderer]")?.getAttribute("data-artifact-renderer"),
      status: "passed",
    }), bootState);
  } finally {
    page.off("console", onConsole);
    page.off("pageerror", onPageError);
  }
}
