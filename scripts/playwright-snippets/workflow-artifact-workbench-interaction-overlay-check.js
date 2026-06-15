async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const artifacts = state.collection?.artifacts || [];
    const imageIndex = artifacts.findIndex((artifact) => artifact.type === "image");
    if (imageIndex < 0) throw new Error("No image artifact available for interaction overlay smoke");
    const artifactId = artifacts[imageIndex].id;
    const annotations = { ...(state.annotations || {}) };
    annotations[artifactId] = [];
    const response = await fetch("/api/annotation-state", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ annotations }),
    });
    if (!response.ok) throw new Error(`Annotation reset failed: ${response.status}`);
    return { artifactId, imageIndex };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((imageIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${imageIndex}"]`);
    if (!row) throw new Error(`Image artifact row not found: ${imageIndex}`);
    row.click();
  }, model.imageIndex);

  await page.waitForFunction(() => {
    const image = document.querySelector("#artifact-image");
    return image?.complete && image.naturalWidth > 0 && !document.querySelector("#image-wrap")?.hidden;
  }, null, { timeout: 5000 });

  const imageBox = await page.locator("#artifact-image").boundingBox();
  if (!imageBox) throw new Error("Image bounding box unavailable");
  await page.mouse.move(imageBox.x + 24, imageBox.y + 24);
  await page.mouse.down();
  await page.mouse.move(imageBox.x + 112, imageBox.y + 112);
  await page.mouse.up();

  await page.waitForFunction(() => {
    const popover = document.querySelector("#comment-popover");
    return popover
      && !popover.hidden
      && document.querySelector("#primary-comment-action")?.textContent === "Add Comment"
      && document.querySelector("#secondary-comment-action")?.textContent === "Cancel";
  }, null, { timeout: 3000 });
  await page.fill("#comment-text", "Interaction overlay smoke");
  await page.click("#primary-comment-action");

  await page.waitForFunction(() => {
    return [...document.querySelectorAll(".annotation-text")]
      .some((node) => node.textContent === "Interaction overlay smoke");
  }, null, { timeout: 3000 });

  await page.click(".annotation");
  await page.waitForFunction(() => {
    const popover = document.querySelector("#comment-popover");
    return popover
      && !popover.hidden
      && document.querySelector("#comment-text")?.value === "Interaction overlay smoke"
      && document.querySelector("#primary-comment-action")?.textContent === "Update"
      && document.querySelector("#secondary-comment-action")?.textContent === "Delete";
  }, null, { timeout: 3000 });
  await page.fill("#comment-text", "Interaction overlay smoke updated");
  await page.click("#primary-comment-action");

  await page.waitForFunction(() => {
    const texts = [...document.querySelectorAll(".annotation-text")].map((node) => node.textContent || "");
    return texts.includes("Interaction overlay smoke updated")
      && !texts.includes("Interaction overlay smoke");
  }, null, { timeout: 3000 });

  await page.click(".annotation");
  await page.waitForFunction(() => {
    const popover = document.querySelector("#comment-popover");
    return popover
      && !popover.hidden
      && document.querySelector("#secondary-comment-action")?.textContent === "Delete";
  }, null, { timeout: 3000 });
  await page.click("#secondary-comment-action");

  await page.waitForFunction(() => {
    return ![...document.querySelectorAll(".annotation-text")]
      .some((node) => /Interaction overlay smoke/.test(node.textContent || ""));
  }, null, { timeout: 3000 });

  return await page.evaluate(async ({ artifactId }) => {
    const state = await fetch("/api/annotation-state", { cache: "no-store" }).then((response) => response.json());
    const remaining = (state.annotations?.[artifactId] || [])
      .filter((note) => /Interaction overlay smoke/.test(note.comment || ""));
    return {
      artifactId,
      overlaySubtype: "annotation",
      createLabel: "Add Comment",
      editPrimaryLabel: "Update",
      editSecondaryLabel: "Delete",
      smokeAnnotationCount: remaining.length,
    };
  }, model);
}
