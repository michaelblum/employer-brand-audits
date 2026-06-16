async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const imageIndex = artifacts.findIndex((artifact) => artifact.type === "image");
    if (imageIndex < 0) throw new Error("No image artifact available for annotation reorder smoke");
    const artifactId = artifacts[imageIndex].id;
    return {
      artifactId,
      imageIndex,
      originalInteractionOverlays: state.interaction_overlays || [],
    };
  });

  const smokeNotes = ["first", "second", "third"].map((label, index) => ({
    id: `reorder-smoke-${label}`,
    subtype: "annotation",
    subject: { kind: "artifact", id: model.artifactId },
    anchor: {
      type: "image_region",
      coordinate_space: "natural_image",
      rect: { x: 10 + index, y: 12 + index, width: 24, height: 24 },
    },
    body: { kind: "comment", text: `Reorder smoke ${label}` },
    created_at_epoch: 1781500000 + index,
    updated_at_epoch: null,
  }));

  async function restoreAnnotations() {
    await page.evaluate(async ({ originalInteractionOverlays }) => {
      const response = await fetch("/api/workbench-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ interaction_overlays: originalInteractionOverlays }),
      });
      if (!response.ok) throw new Error(`Interaction overlay restore failed: ${response.status}`);
    }, model);
  }

  try {
    await page.evaluate(async ({ artifactId, originalInteractionOverlays, smokeNotes }) => {
      const interactionOverlays = originalInteractionOverlays
        .filter((overlay) => !(
          overlay?.subtype === "annotation"
          && overlay?.subject?.kind === "artifact"
          && overlay?.subject?.id === artifactId
        ))
        .concat(smokeNotes);
      const response = await fetch("/api/workbench-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ interaction_overlays: interactionOverlays }),
      });
      if (!response.ok) throw new Error(`Interaction overlay seed failed: ${response.status}`);
    }, { ...model, smokeNotes });

    await page.reload();
    await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
    await page.evaluate((imageIndex) => {
      const row = document.querySelector(`.artifact-row[data-index="${imageIndex}"]`);
      if (!row) throw new Error(`Image artifact row not found: ${imageIndex}`);
      row.click();
    }, model.imageIndex);

    await page.waitForFunction(() => {
      const texts = [...document.querySelectorAll(".annotation-text")].map((node) => node.textContent || "");
      return texts.includes("Reorder smoke first")
        && texts.includes("Reorder smoke second")
        && texts.includes("Reorder smoke third");
    }, null, { timeout: 5000 });

    await page.evaluate(() => {
      const annotations = [...document.querySelectorAll(".annotation")];
      const source = annotations.find((row) => row.dataset.annotationId === "reorder-smoke-third");
      const target = annotations.find((row) => row.dataset.annotationId === "reorder-smoke-first");
      if (!source || !target) throw new Error("Reorder smoke annotations not found in sidebar");
      const dataTransfer = new DataTransfer();
      source.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer }));
      target.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer }));
      target.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer }));
      source.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer }));
    });

    await page.waitForFunction((artifactId) => {
      return fetch("/api/workbench-state", { cache: "no-store" })
        .then((response) => response.json())
        .then((state) => {
          const ids = (state.interaction_overlays || [])
            .filter((overlay) => (
              overlay?.subtype === "annotation"
              && overlay?.subject?.kind === "artifact"
              && overlay?.subject?.id === artifactId
            ))
            .map((note) => note.id);
          return ids.join(",") === "reorder-smoke-third,reorder-smoke-first,reorder-smoke-second";
        });
    }, model.artifactId, { timeout: 5000 });

    const order = await page.evaluate(async ({ artifactId }) => {
      const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
      return (state.interaction_overlays || [])
        .filter((overlay) => (
          overlay?.subtype === "annotation"
          && overlay?.subject?.kind === "artifact"
          && overlay?.subject?.id === artifactId
        ))
        .map((note) => note.id);
    }, model);

    return {
      artifactId: model.artifactId,
      reorderedAnnotationIds: order,
    };
  } finally {
    await restoreAnnotations();
  }
}
