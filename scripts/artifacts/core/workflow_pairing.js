(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};

  function selectorCandidatesForDefinition(definition = {}) {
    const selectors = definition?.anchor?.selector_candidates;
    return Array.isArray(selectors)
      ? selectors.map((item) => String(item || "").trim()).filter(Boolean)
      : [];
  }

  function definitionForArtifact(definitions = [], artifact = {}) {
    return definitions.find((definition) => (
      definition?.anchor?.artifact_id === artifact?.id
      && definition?.step_id
      && selectorCandidatesForDefinition(definition).length > 0
    )) || null;
  }

  function domAnchorForDefinition(definition, { artifactId = "" } = {}) {
    const selectorCandidates = selectorCandidatesForDefinition(definition);
    if (!selectorCandidates.length) return null;
    return {
      type: "dom_element",
      coordinate_space: "artifact_dom",
      artifact_id: definition?.anchor?.artifact_id || artifactId,
      selector_candidates: selectorCandidates,
    };
  }

  function targetLinkOptionsForDefinition(definition = {}) {
    if (definition.target_link && typeof definition.target_link === "object") {
      return definition.target_link;
    }
    if (definition.anchor?.target_link && typeof definition.anchor.target_link === "object") {
      return definition.anchor.target_link;
    }
    return {};
  }

  ROOT.workflowPairing = {
    definitionForArtifact,
    domAnchorForDefinition,
    selectorCandidatesForDefinition,
    targetLinkOptionsForDefinition,
  };
}());
