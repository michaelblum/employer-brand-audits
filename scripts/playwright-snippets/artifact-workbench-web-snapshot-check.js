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

    const model = await page.evaluate(async () => {
      const [state, projection] = await Promise.all([
        fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
        fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
      ]);
      if (projection.source?.format !== "url_stage_capture") {
        throw new Error(`Expected URL stage projection, got ${projection.source?.format}`);
      }
      const webSnapshot = (projection.artifacts || []).find((artifact) => artifact.type === "html" && artifact.kind === "web_snapshot");
      if (!webSnapshot) throw new Error("Missing projected html/web_snapshot artifact");
      const targetMap = (projection.artifacts || []).find((artifact) => artifact.id === webSnapshot.facets?.target_map_artifact_id);
      if (!targetMap) throw new Error(`Missing target map artifact for ${webSnapshot.id}`);
      if (targetMap.facets?.coordinate_space !== "screenshot") {
        throw new Error(`Target map must use screenshot coordinate space: ${JSON.stringify(targetMap)}`);
      }
      const artifactIndex = (state.collection?.artifacts || []).findIndex((artifact) => artifact.id === webSnapshot.id);
      if (artifactIndex < 0) throw new Error(`${webSnapshot.id} is not present in the workbench collection`);
      return { artifactIndex, targetMap, webSnapshot };
    });

    await page.evaluate((artifactIndex) => {
      const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
      if (!row) throw new Error(`Web snapshot artifact row not rendered: ${artifactIndex}`);
      row.click();
    }, model.artifactIndex);

    await page.waitForFunction(() => {
      const frame = document.querySelector("[data-html-frame]");
      const doc = frame?.contentDocument;
      const stage = doc?.querySelector("[data-web-snapshot-stage='true']");
      const targets = [...(doc?.querySelectorAll(".web-target[data-web-target-id]") || [])];
      const target = targets.find((candidate) => {
        try {
          const metadata = JSON.parse(candidate.getAttribute("data-web-target") || "{}");
          return ["button", "input", "link"].includes(metadata.target_kind);
        } catch (_error) {
          return false;
        }
      }) || targets[0];
      const image = doc?.querySelector(".web-snapshot-stage img");
      const readout = document.querySelector("#artifact-readout")?.textContent || "";
      return document.querySelector("[data-artifact-renderer='html']")
        && document.querySelector("#image-controls") === null
        && document.querySelector("#markdown-controls") === null
        && stage
        && target
        && image
        && /html/.test(readout);
    }, null, { timeout: 5000 });

    await page.evaluate(() => {
      const frame = document.querySelector("[data-html-frame]");
      const doc = frame.contentDocument;
      const targets = [...doc.querySelectorAll(".web-target[data-web-target-id]")];
      const target = targets.find((candidate) => {
        try {
          const metadata = JSON.parse(candidate.getAttribute("data-web-target") || "{}");
          return ["button", "input", "link"].includes(metadata.target_kind);
        } catch (_error) {
          return false;
        }
      }) || targets[0];
      const rect = target.getBoundingClientRect();
      target.dispatchEvent(new frame.contentWindow.MouseEvent("mousemove", {
        bubbles: true,
        cancelable: true,
        clientX: rect.left + Math.min(8, rect.width / 2),
        clientY: rect.top + Math.min(8, rect.height / 2),
      }));
    });

    await page.waitForFunction(() => {
      const marker = document.querySelector("#markdown-marker");
      const rect = marker?.getBoundingClientRect();
      return marker && marker.hidden === false && rect?.width > 0 && rect?.height > 0;
    }, null, { timeout: 3000 });

    await page.evaluate(() => {
      const frame = document.querySelector("[data-html-frame]");
      const doc = frame.contentDocument;
      const targets = [...doc.querySelectorAll(".web-target[data-web-target-id]")];
      const target = targets.find((candidate) => {
        try {
          const metadata = JSON.parse(candidate.getAttribute("data-web-target") || "{}");
          return ["button", "input", "link"].includes(metadata.target_kind);
        } catch (_error) {
          return false;
        }
      }) || targets[0];
      const rect = target.getBoundingClientRect();
      target.dispatchEvent(new frame.contentWindow.MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        clientX: rect.left + Math.min(8, rect.width / 2),
        clientY: rect.top + Math.min(8, rect.height / 2),
      }));
    });

    await page.waitForFunction(() => {
      return document.querySelector("#comment-popover")?.hidden === false
        && document.querySelector("#comment-text") !== null
        && document.querySelector("#primary-comment-action")?.textContent?.trim();
    }, null, { timeout: 3000 });

    const result = await page.evaluate((modelValue) => {
      const frame = document.querySelector("[data-html-frame]");
      const doc = frame?.contentDocument;
      const targets = [...(doc?.querySelectorAll(".web-target[data-web-target-id]") || [])];
      const target = targets.find((candidate) => {
        try {
          const metadata = JSON.parse(candidate.getAttribute("data-web-target") || "{}");
          return ["button", "input", "link"].includes(metadata.target_kind);
        } catch (_error) {
          return false;
        }
      }) || targets[0];
      const markerRect = document.querySelector("#markdown-marker")?.getBoundingClientRect();
      const popoverOpen = document.querySelector("#comment-popover")?.hidden === false;
      document.querySelector("#secondary-comment-action")?.click();
      return {
        activeArtifactTitle: document.querySelector("#artifact-title")?.textContent?.trim(),
        rendererType: document.querySelector("[data-artifact-renderer]")?.getAttribute("data-artifact-renderer"),
        targetId: target?.getAttribute("data-web-target-id"),
        targetCount: modelValue.targetMap.facets?.target_count,
        markerRect: markerRect ? {
          x: Math.round(markerRect.x),
          y: Math.round(markerRect.y),
          width: Math.round(markerRect.width),
          height: Math.round(markerRect.height),
        } : null,
        popoverOpened: popoverOpen,
        readout: document.querySelector("#artifact-readout")?.textContent?.trim(),
        status: "passed",
      };
    }, model);

    if (runtimeErrors.length) {
      throw new Error(`Workbench runtime errors: ${runtimeErrors.join(" | ")}`);
    }
    return result;
  } finally {
    page.off("console", onConsole);
    page.off("pageerror", onPageError);
  }
}
