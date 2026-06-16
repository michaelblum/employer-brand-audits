async (page) => {
  await page.reload();

  const model = await page.evaluate(async () => {
    const [state, projection] = await Promise.all([
      fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const collection = state.collection?.artifacts || [];
    const projectedArtifactsById = Object.fromEntries(
      (projection.artifacts || []).map((artifact) => [artifact.id, artifact])
    );
    const projectedStepsById = Object.fromEntries(
      (projection.workflow?.steps || []).map((step) => [step.id, step])
    );
    const countsByStepId = {};
    for (const artifact of collection) {
      const stepId = projectedArtifactsById[artifact.id]?.produced_by_step_id;
      if (stepId) countsByStepId[stepId] = (countsByStepId[stepId] || 0) + 1;
    }
    const stepId = Object.entries(countsByStepId)
      .sort((left, right) => right[1] - left[1])
      .map(([id]) => id)
      .find((id) => projectedStepsById[id] && countsByStepId[id] > 1);
    if (!stepId) throw new Error("No projected step filter target found");
    return {
      artifactCount: collection.length,
      selectedStep: projectedStepsById[stepId],
      selectedStepCount: countsByStepId[stepId],
    };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((stepId) => {
    const button = document.querySelector(`[data-filter-kind="step"][data-filter-value="${CSS.escape(stepId)}"]`);
    if (!button) throw new Error(`Step filter button not found: ${stepId}`);
    button.click();
  }, model.selectedStep.id);

  await page.waitForFunction((stepId) => {
    const active = document.querySelector(`[data-filter-kind="step"][data-filter-value="${CSS.escape(stepId)}"]`);
    return active?.classList.contains("active") && document.querySelectorAll(".artifact-row[data-index]").length > 0;
  }, model.selectedStep.id, { timeout: 3000 });

  const filteredState = await page.evaluate(async (stepId) => {
    const [state, projection] = await Promise.all([
      fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const collection = state.collection?.artifacts || [];
    const projectedArtifactsById = Object.fromEntries(
      (projection.artifacts || []).map((artifact) => [artifact.id, artifact])
    );
    const visibleRows = [...document.querySelectorAll(".artifact-row[data-index]")];
    const visibleIds = visibleRows.map((row) => {
      const index = Number(row.dataset.index);
      const artifact = collection[index];
      if (!artifact) throw new Error(`Visible row has no collection artifact at index ${row.dataset.index}`);
      return artifact.id;
    });
    const mismatches = visibleIds.filter((id) => projectedArtifactsById[id]?.produced_by_step_id !== stepId);
    if (mismatches.length) {
      throw new Error(`Step filter included artifacts from another step: ${mismatches.join(",")}`);
    }
    const activeRow = document.querySelector(".artifact-row.active[data-index]");
    if (!activeRow) throw new Error("No active row after step filtering");
    return {
      activeIndex: activeRow.dataset.index,
      filteredRowCount: visibleRows.length,
      visibleIndexes: visibleRows.map((row) => row.dataset.index),
      title: document.querySelector("#artifact-title")?.textContent?.trim(),
      visibleIds,
    };
  }, model.selectedStep.id);

  if (filteredState.filteredRowCount !== model.selectedStepCount) {
    throw new Error(`Filtered row count mismatch: expected ${model.selectedStepCount} got ${filteredState.filteredRowCount}`);
  }
  if (filteredState.visibleIndexes.length < 2) {
    throw new Error(`Filtered Prev/Next smoke needs at least two visible artifacts: ${JSON.stringify(filteredState)}`);
  }

  const initialPosition = filteredState.visibleIndexes.indexOf(filteredState.activeIndex);
  const expectedNextIndex = filteredState.visibleIndexes[(initialPosition + 1) % filteredState.visibleIndexes.length];
  await page.click("#next", { timeout: 3000 });
  await page.waitForFunction((index) => {
    const activeRow = document.querySelector(".artifact-row.active[data-index]");
    return activeRow?.dataset.index === index;
  }, expectedNextIndex, { timeout: 3000 });

  const filteredNextState = await page.evaluate(() => ({
    activeIndex: document.querySelector(".artifact-row.active[data-index]")?.dataset.index,
    visibleIndexes: [...document.querySelectorAll(".artifact-row[data-index]")].map((row) => row.dataset.index),
    title: document.querySelector("#artifact-title")?.textContent?.trim(),
  }));
  if (JSON.stringify(filteredNextState.visibleIndexes) !== JSON.stringify(filteredState.visibleIndexes)) {
    throw new Error(`Next changed the filtered row set: ${JSON.stringify({ before: filteredState, after: filteredNextState })}`);
  }

  await page.click("#prev", { timeout: 3000 });
  await page.waitForFunction((index) => {
    const activeRow = document.querySelector(".artifact-row.active[data-index]");
    return activeRow?.dataset.index === index;
  }, filteredState.activeIndex, { timeout: 3000 });

  await page.click("#overview", { timeout: 3000 });
  await page.waitForSelector("#overview-popover [data-index]", { timeout: 3000 });

  const overviewState = await page.evaluate(() => {
    const buttons = [...document.querySelectorAll("#overview-popover [data-index]")];
    const activeOption = document.querySelector("#overview-popover .artifact-option.active[data-index]");
    const activeRow = document.querySelector(".artifact-row.active[data-index]");
    if (!activeOption) throw new Error("No active overview option");
    if (!activeRow) throw new Error("No active sidebar row while overview is open");
    if (activeOption.dataset.index !== activeRow.dataset.index) {
      throw new Error(`Active overview index ${activeOption.dataset.index} did not match row ${activeRow.dataset.index}`);
    }
    return {
      activeIndex: activeOption.dataset.index,
      optionCount: buttons.length,
      alternateIndex: buttons.find((button) => button.dataset.index !== activeOption.dataset.index)?.dataset.index || null,
    };
  });

  let overviewNavigation = null;
  if (overviewState.alternateIndex !== null) {
    await page.evaluate((index) => {
      const button = document.querySelector(`#overview-popover [data-index="${CSS.escape(index)}"]`);
      if (!button) throw new Error(`Overview option not found: ${index}`);
      button.click();
    }, overviewState.alternateIndex);
    await page.waitForFunction((index) => {
      const activeRow = document.querySelector(".artifact-row.active[data-index]");
      return activeRow?.dataset.index === index && document.querySelector("#overview-popover")?.hidden;
    }, overviewState.alternateIndex, { timeout: 3000 });
    overviewNavigation = await page.evaluate(() => ({
      activeIndex: document.querySelector(".artifact-row.active[data-index]")?.dataset.index,
      title: document.querySelector("#artifact-title")?.textContent?.trim(),
    }));
  }

  await page.evaluate(() => {
    const button = document.querySelector("[data-filter-kind='clear']");
    if (!button) throw new Error("Clear filter button not found");
    button.click();
  });

  await page.waitForFunction((artifactCount) => (
    !document.querySelector("[data-filter-kind='clear']")
      && !document.querySelector("[data-filter-kind='step'].active")
      && document.querySelectorAll(".artifact-row[data-index]").length === artifactCount
  ), model.artifactCount, { timeout: 3000 });

  const clearedState = await page.evaluate(() => ({
    rowCount: document.querySelectorAll(".artifact-row[data-index]").length,
    activeFilterCount: document.querySelectorAll("[data-filter-kind].active").length,
  }));

  return {
    selectedStep: model.selectedStep.id,
    filteredRowCount: filteredState.filteredRowCount,
    filteredNavigation: {
      initialIndex: filteredState.activeIndex,
      nextIndex: filteredNextState.activeIndex,
      visibleIndexes: filteredState.visibleIndexes,
    },
    overviewCount: overviewState.optionCount,
    overviewNavigation,
    clearedRowCount: clearedState.rowCount,
    activeFilterCount: clearedState.activeFilterCount,
  };
}
