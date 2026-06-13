async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const [state, projection] = await Promise.all([
      fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const collectionIds = new Set((state.collection?.artifacts || []).map((artifact) => artifact.id));
    const group = (projection.artifact_groups || []).find((item) => (
      Array.isArray(item.artifact_ids)
        && item.artifact_ids.length > 1
        && item.artifact_ids.every((artifactId) => collectionIds.has(artifactId))
    ));
    if (!group) throw new Error("No projection-only composite group found");
    const durableCompositeArtifact = (projection.artifacts || []).find((artifact) => artifact.id === group.id);
    if (durableCompositeArtifact) throw new Error(`Composite group is also a durable artifact: ${group.id}`);
    return {
      groupId: group.id,
      label: group.label,
      artifactIds: group.artifact_ids,
    };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((groupId) => {
    const button = document.querySelector(`[data-filter-kind="composite"][data-filter-value="${CSS.escape(groupId)}"]`);
    if (!button) throw new Error(`Composite filter button not found: ${groupId}`);
    button.click();
  }, model.groupId);

  await page.waitForFunction((label) => {
    const breadcrumb = document.querySelector("#artifact-title .artifact-breadcrumb");
    return breadcrumb && breadcrumb.textContent.includes(label);
  }, model.label, { timeout: 3000 });

  return await page.evaluate(async (model) => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const collection = state.collection?.artifacts || [];
    const visibleRows = [...document.querySelectorAll(".artifact-row[data-index]")];
    const visibleIds = visibleRows.map((row) => {
      const index = Number(row.dataset.index);
      const id = collection[index]?.id;
      if (!id) throw new Error(`Visible row has no stable collection id at index ${row.dataset.index}`);
      return id;
    });
    const expected = [...model.artifactIds].sort();
    const actual = [...visibleIds].sort();
    if (JSON.stringify(expected) !== JSON.stringify(actual)) {
      throw new Error(`Composite row ids mismatch: expected ${expected.join(",")} got ${actual.join(",")}`);
    }
    if (visibleRows.some((row) => row.textContent.includes(model.groupId))) {
      throw new Error("Composite group appeared as a durable artifact row");
    }
    return {
      breadcrumb: document.querySelector("#artifact-title .artifact-breadcrumb")?.textContent?.trim(),
      activeCompositeButton: document.querySelector("[data-filter-kind='composite'].active")?.textContent?.trim(),
      expectedArtifactIds: model.artifactIds,
      visibleRowCount: visibleRows.length,
      visibleIds,
    };
  }, model);
}
