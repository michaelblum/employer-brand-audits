async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const [state, projection] = await Promise.all([
      fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const mermaidArtifact = (projection.artifacts || []).find((artifact) => (
      artifact.type === "markdown"
        && artifact.facets?.diagram_kind === "mermaid"
        && (artifact.capabilities || []).includes("render")
    ));
    if (!mermaidArtifact) throw new Error("No Mermaid-capable markdown artifact in projection");
    const artifactIndex = (state.collection?.artifacts || []).findIndex((artifact) => artifact.id === mermaidArtifact.id);
    if (artifactIndex < 0) throw new Error(`Mermaid artifact not present in collection: ${mermaidArtifact.id}`);
    return { artifactId: mermaidArtifact.id, artifactIndex };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((artifactIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
    if (!row) throw new Error(`Mermaid artifact row not rendered: ${artifactIndex}`);
    row.click();
  }, model.artifactIndex);

  await page.waitForFunction(() => {
    const figure = document.querySelector("[data-artifact-renderer='mermaid']");
    return figure?.dataset.renderState === "complete"
      && figure.querySelector("[data-mermaid-target] svg")
      && figure.querySelector(".mermaid-source-line[data-source-line]");
  }, null, { timeout: 5000 });
  const validRenderCompleted = true;

  const mermaidLine = await page.evaluate(() => {
    const first = document.querySelector(".mermaid-source-line[data-source-line]");
    return Number(first?.dataset.sourceLine || 0);
  });
  if (!mermaidLine) throw new Error("No Mermaid source line found");

  await page.evaluate(async ({ artifactId, line }) => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const annotations = state.annotations || {};
    annotations[artifactId] = [{
      id: `${artifactId}-mermaid-source-line-smoke`,
      artifact_id: artifactId,
      kind: "comment",
      anchor: {
        type: "text_range",
        coordinate_space: "markdown_source",
        start: { line, column: 1 },
        end: { line, column: 24 },
        excerpt: "Mermaid source line",
      },
      comment: "Mermaid source-line annotation smoke",
      created_at_epoch: Math.floor(Date.now() / 1000),
      updated_at_epoch: null,
    }];
    const response = await fetch("/api/annotation-state", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ annotations }),
    });
    if (!response.ok) throw new Error(`Annotation sync failed: ${response.status}`);
  }, { artifactId: model.artifactId, line: mermaidLine });

  await page.reload();
  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((artifactIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
    if (!row) throw new Error(`Mermaid artifact row not rendered after reload: ${artifactIndex}`);
    row.click();
  }, model.artifactIndex);
  await page.waitForFunction((line) => {
    const hit = document.querySelector(`.mermaid-source-line[data-source-line="${line}"]`);
    return hit?.classList.contains("line-hit");
  }, mermaidLine, { timeout: 5000 });

  await page.click("#markdown-source-mode");
  await page.waitForFunction(() => !document.querySelector("#markdown-source")?.hidden, null, { timeout: 3000 });
  await page.click("#markdown-preview-mode");
  await page.waitForFunction((line) => {
    const figure = document.querySelector("[data-artifact-renderer='mermaid']");
    const hit = document.querySelector(`.mermaid-source-line[data-source-line="${line}"]`);
    return figure?.dataset.renderState === "complete" && hit?.classList.contains("line-hit");
  }, mermaidLine, { timeout: 5000 });
  const sourceLineAnchorSurvivedModeSwitch = await page.evaluate((line) => {
    const hit = document.querySelector(`.mermaid-source-line[data-source-line="${line}"]`);
    return Boolean(hit?.classList.contains("line-hit"));
  }, mermaidLine);

  await page.click("#markdown-source-mode");
  await page.evaluate(() => {
    const source = document.querySelector("#markdown-source");
    source.value = "```mermaid\nflowchart TD\n  A -->\n```";
    source.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.click("#markdown-preview-mode");
  await page.waitForFunction(() => {
    const figure = document.querySelector("[data-artifact-renderer='mermaid']");
    return figure?.dataset.renderState === "error"
      && /Mermaid render error/.test(figure.querySelector("[data-mermaid-status]")?.textContent || "")
      && Boolean(figure.querySelector(".mermaid-source"));
  }, null, { timeout: 5000 });

  const result = await page.evaluate(({ sourceLineAnchorSurvivedModeSwitch, validRenderCompleted }) => {
    const figure = document.querySelector("[data-artifact-renderer='mermaid']");
    return {
      artifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
      validRenderCompleted,
      invalidRenderState: figure?.dataset.renderState,
      renderer: figure?.dataset.artifactRenderer,
      status: figure?.querySelector("[data-mermaid-status]")?.textContent?.trim(),
      sourceLineAnchorSurvivedModeSwitch,
      invalidSourceFallbackRendered: Boolean(figure?.querySelector(".mermaid-source")),
      activeIconHref: document.querySelector(".artifact-row.active .artifact-type-icon use")?.getAttribute("href"),
    };
  }, { sourceLineAnchorSurvivedModeSwitch, validRenderCompleted });

  await page.reload();
  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });

  return result;
}
