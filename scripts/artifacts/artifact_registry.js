(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  const PRIMITIVES = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function components() {
    return [
      ROOT.types?.markdown,
      ROOT.types?.html,
      ROOT.types?.document,
      ROOT.types?.image,
    ].filter(Boolean);
  }

  function fallbackComponent() {
    return ROOT.types?.image;
  }

  function resolveArtifactComponent(artifact = {}, options = {}) {
    return components().find((component) => component.matches(artifact, options)) || fallbackComponent();
  }

  function artifactRenderKind(artifact = {}, options = {}) {
    return resolveArtifactComponent(artifact, options).kind;
  }

  function artifactStagePlan(artifact = {}, options = {}) {
    return resolveArtifactComponent(artifact, options).stagePlan(artifact, options);
  }

  function artifactReadout(options = {}) {
    const context = ROOT.common.readoutContext(options);
    return resolveArtifactComponent(context.artifact, context).readout(context);
  }

  function artifactToolbarPlan(options = {}) {
    const context = ROOT.common.readoutContext(options);
    return resolveArtifactComponent(context.artifact, context).toolbarPlan(context);
  }

  ROOT.registry = {
    artifactReadout,
    artifactRenderKind,
    artifactStagePlan,
    artifactToolbarPlan,
    resolveArtifactComponent,
  };
  PRIMITIVES.artifactRegistry = ROOT.registry;
}());
