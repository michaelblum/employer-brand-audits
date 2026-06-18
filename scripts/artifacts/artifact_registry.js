(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  const PRIMITIVES = window.ArtifactPrimitives = window.ArtifactPrimitives || {};
  const registeredTypes = ROOT.registeredTypes || [];
  ROOT.registeredTypes = registeredTypes;
  let fallbackKind = ROOT.fallbackArtifactKind || null;

  function typeOrder(component = {}) {
    return Number.isFinite(component.order) ? component.order : 1000;
  }

  function components() {
    return registeredTypes.slice().sort((left, right) => {
      const orderDelta = typeOrder(left) - typeOrder(right);
      if (orderDelta !== 0) return orderDelta;
      return String(left.kind || "").localeCompare(String(right.kind || ""));
    });
  }

  function registerType(component = {}) {
    if (!component.kind) throw new Error("Artifact type registration requires kind");
    if (typeof component.matches !== "function") throw new Error(`Artifact type ${component.kind} requires matches`);
    if (typeof component.stagePlan !== "function") throw new Error(`Artifact type ${component.kind} requires stagePlan`);
    if (typeof component.readout !== "function") throw new Error(`Artifact type ${component.kind} requires readout`);
    if (typeof component.toolbarPlan !== "function") throw new Error(`Artifact type ${component.kind} requires toolbarPlan`);
    const index = registeredTypes.findIndex((registered) => registered.kind === component.kind);
    if (index >= 0) registeredTypes.splice(index, 1, component);
    else registeredTypes.push(component);
    if (component.fallback) fallbackKind = ROOT.fallbackArtifactKind = component.kind;
    return component;
  }

  function fallbackComponent() {
    return components().find((component) => component.kind === fallbackKind) || components()[0];
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

  ROOT.registerType = registerType;
  ROOT.registry = {
    artifactReadout,
    artifactRenderKind,
    artifactStagePlan,
    artifactToolbarPlan,
    registeredArtifactTypes: components,
    registerType,
    resolveArtifactComponent,
  };
  PRIMITIVES.artifactRegistry = ROOT.registry;
}());
