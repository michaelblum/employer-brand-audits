async (page) => {
  await page.reload();
  const model = await page.evaluate(async () => {
    const [state, projection] = await Promise.all([
      fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json()),
      fetch("/api/workbench-projection", { cache: "no-store" }).then((response) => response.json()),
    ]);
    const inputOverlays = projection.workflow?.input_overlays || [];
    if (inputOverlays.length < 4) throw new Error("No projected bounded intake input overlays");
    const intakeArtifactId = inputOverlays[0]?.anchor?.artifact_id;
    const artifactIndex = (state.collection?.artifacts || []).findIndex((artifact) => artifact.id === intakeArtifactId);
    if (artifactIndex < 0) throw new Error(`Intake artifact not present in collection: ${intakeArtifactId}`);
    return { artifactIndex, intakeArtifactId };
  });

  await page.waitForSelector(".artifact-row[data-index]", { timeout: 5000 });
  await page.evaluate((artifactIndex) => {
    const row = document.querySelector(`.artifact-row[data-index="${artifactIndex}"]`);
    if (!row) throw new Error(`Intake artifact row not rendered: ${artifactIndex}`);
    row.click();
  }, model.artifactIndex);

  await page.waitForSelector('[data-artifact-renderer="mermaid"].render-state-complete svg', { timeout: 5000 });
  const diagramVisual = await page.evaluate(() => {
    function rgbFromCss(value) {
      const match = String(value || "").match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if (!match) return null;
      return match.slice(1, 4).map((part) => Number(part) / 255);
    }

    function luminance(rgb) {
      if (!rgb) return 0;
      const [r, g, b] = rgb.map((channel) => (
        channel <= 0.03928
          ? channel / 12.92
          : Math.pow((channel + 0.055) / 1.055, 2.4)
      ));
      return (0.2126 * r) + (0.7152 * g) + (0.0722 * b);
    }

    const figure = document.querySelector('[data-artifact-renderer="mermaid"].render-state-complete');
    const target = figure?.querySelector("[data-mermaid-target]");
    const svg = target?.querySelector("svg");
    if (!figure || !target || !svg) throw new Error("Rendered Mermaid figure not available");

    const edgePaths = [...new Set([
      ...svg.querySelectorAll(".edgePath path"),
      ...svg.querySelectorAll("path.flowchart-link"),
    ])];
    const edgeSamples = edgePaths.map((path) => {
      const style = getComputedStyle(path);
      return {
        stroke: style.stroke,
        strokeWidth: Number.parseFloat(style.strokeWidth) || 0,
        luminance: luminance(rgbFromCss(style.stroke)),
      };
    });
    const targetRect = target.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    const targetStyle = getComputedStyle(target);
    const svgStyle = getComputedStyle(svg);
    const nodeSamples = [...svg.querySelectorAll("g.node")].map((node) => {
      const rect = node.querySelector("rect.label-container");
      const foreignObject = node.querySelector("foreignObject");
      const label = node.querySelector(".nodeLabel");
      const rectBox = rect?.getBoundingClientRect();
      const foreignObjectBox = foreignObject?.getBoundingClientRect();
      const labelBox = label?.getBoundingClientRect();
      const rectStyle = rect ? getComputedStyle(rect) : null;
      const foreignObjectStyle = foreignObject ? getComputedStyle(foreignObject) : null;
      return {
        text: label?.innerText || node.textContent.trim(),
        cornerRadius: Number.parseFloat(rectStyle?.rx || rect?.getAttribute("rx") || "0") || 0,
        foreignObjectOverflow: foreignObjectStyle?.overflow || "",
        labelToForeignObjectBottomGap: foreignObjectBox && labelBox
          ? foreignObjectBox.bottom - labelBox.bottom
          : null,
        labelToRectBottomGap: rectBox && labelBox ? rectBox.bottom - labelBox.bottom : null,
      };
    });
    return {
      edgeCount: edgeSamples.length,
      minEdgeLuminance: Math.min(...edgeSamples.map((sample) => sample.luminance)),
      edgeSamples: edgeSamples.slice(0, 3),
      nodeSamples,
      bottomGap: targetRect.bottom - svgRect.bottom,
      paddingBottom: Number.parseFloat(targetStyle.paddingBottom) || 0,
      svgOverflow: svgStyle.overflow,
    };
  });
  if (diagramVisual.edgeCount < 1) {
    throw new Error("Rendered intake Mermaid diagram has no edge paths");
  }
  if (diagramVisual.minEdgeLuminance <= 0.12) {
    throw new Error(`Mermaid arrows are too dark against the workbench background: ${JSON.stringify(diagramVisual.edgeSamples)}`);
  }
  if (diagramVisual.bottomGap < 24 || diagramVisual.paddingBottom < 24 || diagramVisual.svgOverflow !== "visible") {
    throw new Error(`Mermaid bottom text is at risk of clipping: ${JSON.stringify(diagramVisual)}`);
  }
  const clippedNodeLabels = diagramVisual.nodeSamples.filter((sample) => (
    sample.foreignObjectOverflow !== "visible"
    && typeof sample.labelToForeignObjectBottomGap === "number"
    && sample.labelToForeignObjectBottomGap < 0
    && typeof sample.labelToRectBottomGap === "number"
    && sample.labelToRectBottomGap > 2
  ));
  if (clippedNodeLabels.length > 0) {
    throw new Error(`Mermaid node labels clip descenders inside foreignObject labels: ${JSON.stringify(clippedNodeLabels.slice(0, 3))}`);
  }
  const squareNodeBoxes = diagramVisual.nodeSamples.filter((sample) => sample.cornerRadius < 3);
  if (squareNodeBoxes.length > 0) {
    throw new Error(`Mermaid node boxes are too square for the intake flow visual: ${JSON.stringify(squareNodeBoxes.slice(0, 3))}`);
  }

  await page.waitForSelector("[data-bounded-input-panel]", { timeout: 5000 });
  const pairingVisual = await page.evaluate(() => {
    const node = document.querySelector('[data-artifact-renderer="mermaid"] svg g.node[data-id="intake"]');
    const panel = document.querySelector("[data-bounded-input-panel]");
    const highlight = document.querySelector("[data-workflow-pairing-highlight]");
    const connector = document.querySelector("[data-workflow-pairing-connector]");
    const connectorPath = connector?.querySelector("[data-workflow-pairing-connector-path]");
    const stageRect = document.querySelector("#stage")?.getBoundingClientRect();
    const nodeRect = node?.getBoundingClientRect();
    const panelRect = panel?.getBoundingClientRect();
    const highlightRect = highlight?.getBoundingClientRect();
    const panelStyle = panel ? getComputedStyle(panel) : null;
    const highlightStyle = highlight ? getComputedStyle(highlight) : null;
    const pathStyle = connectorPath ? getComputedStyle(connectorPath) : null;
    return {
      hasNode: Boolean(node),
      hasPanel: Boolean(panel),
      hasHighlight: Boolean(highlight),
      hasConnector: Boolean(connector),
      hasConnectorPath: Boolean(connectorPath),
      connectorPathD: connectorPath?.getAttribute("d") || "",
      highlightStepId: highlight?.dataset.workflowStepId || "",
      targetLinkEffect: highlight?.dataset.targetLinkEffect || "",
      panelPairing: panel?.dataset.pairing || "",
      panelTargetLinkEffect: panel?.dataset.targetLinkEffect || "",
      highlightAnimationName: highlightStyle?.animationName || "",
      highlightAnimationDuration: highlightStyle?.animationDuration || "",
      panelAnimationName: panelStyle?.animationName || "",
      panelAnimationDuration: panelStyle?.animationDuration || "",
      pathAnimationName: pathStyle?.animationName || "",
      pathAnimationDuration: pathStyle?.animationDuration || "",
      targetLinkColorA: highlightStyle?.getPropertyValue("--target-link-color-a").trim() || "",
      targetLinkLineDuration: highlightStyle?.getPropertyValue("--target-link-line-duration").trim() || "",
      targetLinkPulseDuration: highlightStyle?.getPropertyValue("--target-link-pulse-duration").trim() || "",
      nodeRect: nodeRect ? { left: nodeRect.left, top: nodeRect.top, right: nodeRect.right, bottom: nodeRect.bottom } : null,
      panelRect: panelRect ? { left: panelRect.left, top: panelRect.top, right: panelRect.right, bottom: panelRect.bottom } : null,
      highlightRect: highlightRect ? { left: highlightRect.left, top: highlightRect.top, right: highlightRect.right, bottom: highlightRect.bottom } : null,
      stageRect: stageRect ? { left: stageRect.left, top: stageRect.top, right: stageRect.right, bottom: stageRect.bottom } : null,
    };
  });
  if (!pairingVisual.hasNode || !pairingVisual.hasPanel) {
    throw new Error(`Pairing smoke could not find source node or bounded input panel: ${JSON.stringify(pairingVisual)}`);
  }
  if (!pairingVisual.hasHighlight || !pairingVisual.hasConnector || !pairingVisual.hasConnectorPath) {
    throw new Error(`Workflow pairing overlay is not mounted: ${JSON.stringify(pairingVisual)}`);
  }
  if (pairingVisual.highlightStepId !== "l0-seed-intake" || pairingVisual.panelPairing !== "workflow-step") {
    throw new Error(`Workflow pairing overlay is not bound to the seed intake step: ${JSON.stringify(pairingVisual)}`);
  }
  if (pairingVisual.targetLinkEffect !== "chase" || pairingVisual.panelTargetLinkEffect !== "chase") {
    throw new Error(`Workflow pairing is not rendered through the generic target-link effect: ${JSON.stringify(pairingVisual)}`);
  }
  if (!pairingVisual.connectorPathD.includes("C")) {
    throw new Error(`Workflow pairing connector does not use a curved connector path: ${JSON.stringify(pairingVisual)}`);
  }
  if (!String(pairingVisual.highlightAnimationName).includes("chase")
    || !String(pairingVisual.panelAnimationName).includes("chase")
    || !String(pairingVisual.pathAnimationName).includes("chase")) {
    throw new Error(`Workflow pairing lacks matching chase animation: ${JSON.stringify(pairingVisual)}`);
  }
  const durationSeconds = (value) => Number(String(value || "").replace("s", ""));
  if (durationSeconds(pairingVisual.pathAnimationDuration) < 1.8
    || durationSeconds(pairingVisual.highlightAnimationDuration) < 3.3
    || durationSeconds(pairingVisual.panelAnimationDuration) < 3.3) {
    throw new Error(`Workflow pairing chase animation is too fast: ${JSON.stringify(pairingVisual)}`);
  }
  if (pairingVisual.targetLinkColorA !== "#38bdf8"
    || pairingVisual.targetLinkLineDuration !== "1.8s"
    || pairingVisual.targetLinkPulseDuration !== "3.3s") {
    throw new Error(`Workflow pairing target-link defaults drifted: ${JSON.stringify(pairingVisual)}`);
  }
  const insetTolerance = 8;
  if (
    pairingVisual.highlightRect.left > pairingVisual.nodeRect.left + insetTolerance
    || pairingVisual.highlightRect.top > pairingVisual.nodeRect.top + insetTolerance
    || pairingVisual.highlightRect.right < pairingVisual.nodeRect.right - insetTolerance
    || pairingVisual.highlightRect.bottom < pairingVisual.nodeRect.bottom - insetTolerance
  ) {
    throw new Error(`Workflow pairing highlight does not enclose the intake node: ${JSON.stringify(pairingVisual)}`);
  }

  await page.fill('[data-bounded-input-control][data-input-id="company"]', "Northstar Robotics");
  await page.fill('[data-bounded-input-control][data-input-id="domain_hint"]', "northstar.example");
  await page.selectOption('[data-bounded-input-control][data-input-id="workflow_template"]', "standard-audit");
  await page.fill('[data-bounded-input-control][data-input-id="talent_segment"]', "Field robotics engineers");

  await page.waitForFunction(() => {
    return fetch("/api/workbench-state", { cache: "no-store" })
      .then((response) => response.json())
      .then((state) => {
        const values = state.bounded_inputs?.values || {};
        return values["l0-seed-intake.company"] === "Northstar Robotics"
          && values["l0-seed-intake.domain_hint"] === "northstar.example"
          && values["l0-seed-intake.workflow_template"] === "standard-audit"
          && values["l0-seed-intake.talent_segment"] === "Field robotics engineers";
      });
  }, null, { timeout: 5000 });

  const persistedInputs = await page.evaluate(async ({ intakeArtifactId }) => {
    const state = await fetch("/api/workbench-state", { cache: "no-store" }).then((response) => response.json());
    return {
      status: "passed",
      intakeArtifactId,
      boundedInputCount: state.bounded_inputs?.items?.length || 0,
      values: state.bounded_inputs?.values || {},
    };
  }, model);
  return {
    ...persistedInputs,
    diagramVisual,
    pairingVisual,
  };
}
